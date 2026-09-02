import argparse
from datetime import datetime

import json
from config import Config
from db import init_db, save_job, update_job_status, get_all_jobs_in_session, get_db_connection
from collector import collect_all_jobs
from ats_optimizer import process_job_ats
from sender import apply_to_job
from report import generate_html_report, generate_markdown_report
from filters import filter_jobs
from notify import notify_all
from logutil import log_print


def run_pipeline(keywords, location, min_score, dry_run=False, enable_linkedin_posts=None):
    """Executa um ciclo completo: coleta -> filtros -> ATS -> envio -> relatório.

    Extraído de main() para poder ser chamado tanto pela CLI (python main.py) quanto
    diretamente pela GUI quando ela roda como .exe congelado — nesse caso não existe um
    python.exe nem um main.py separado para chamar via subprocess (o .exe empacota só a GUI).
    """
    log_print("=" * 65)
    log_print("[+] INICIANDO AUTOMATIZADOR DE CURRICULOS & VAGAS (JobAutoFit)")
    log_print("=" * 65)
    log_print(f"[*] Palavras-chave: {keywords}")
    log_print(f"[*] Localização: {location}")
    log_print(f"[*] Nota de Match Mínima: {min_score}%")
    log_print(f"[*] Provedor de IA: {Config.LLM_PROVIDER.upper()}")
    log_print("=" * 65)

    # 1. Inicializar Banco de Dados
    init_db()
    session_start_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Coletar Vagas (Gupy, LinkedIn, Remotive, ...)
    filter_cfg = {}
    try:
        if Config.SEARCH_CONFIG_PATH.exists():
            filter_cfg = json.loads(Config.SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        filter_cfg = {}

    # LinkedIn posts de recrutadores: chamador sobrepõe config; default True se não definido
    enable_posts = filter_cfg.get("enable_linkedin_posts", True)
    if enable_linkedin_posts is not None:
        enable_posts = enable_linkedin_posts
    linkedin_posts_limit = int(filter_cfg.get("linkedin_posts_limit", filter_cfg.get("limit_per_source", 8)) or 8)
    if enable_posts:
        log_print(f"[*] Posts de recrutadores LinkedIn: ATIVADO (limite {linkedin_posts_limit}/keyword)")
    else:
        log_print("[*] Posts de recrutadores LinkedIn: DESATIVADO")

    # envio automático x fila de revisão manual (aba Histórico da GUI)
    auto_send = bool(filter_cfg.get("auto_send", True))
    if not auto_send:
        log_print("[*] Envio automático: DESATIVADO — vagas aprovadas ficam em 'ready_to_send' aguardando aprovação manual na aba Histórico.")

    raw_jobs = collect_all_jobs(keywords, location=location, limit_per_source=filter_cfg.get("limit_per_source", 8), enable_linkedin_posts=enable_posts, linkedin_posts_limit=linkedin_posts_limit)

    # aplicar filtros avançados antes de salvar
    if filter_cfg:
        before = len(raw_jobs)
        raw_jobs = filter_jobs(raw_jobs, filter_cfg)
        log_print(f"[Filtros] {before} -> {len(raw_jobs)} vagas após filtros avançados (salário/nível/PCD/inglês/excluir/bloqueadas)")

    # daily limit
    daily_limit = int(filter_cfg.get("daily_limit", Config.DAILY_LIMIT) or Config.DAILY_LIMIT)
    # contar já processados hoje (inclui ready_to_send: já consumiram cota de geração/IA hoje)
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs WHERE date(created_at)=date('now') AND status IN ('applied','prepared','ready_to_send')")
        today_count = cur.fetchone()[0]
        con.close()
    except Exception:
        today_count = 0
    remaining = max(0, daily_limit - today_count)
    if remaining == 0 and daily_limit > 0:
        log_print(f"[Limite] Limite diário de {daily_limit} atingido. Nenhuma vaga será processada hoje.")
        raw_jobs = []

    saved_jobs = []
    new_jobs_count = 0

    for j in raw_jobs:
        if len(saved_jobs) >= remaining and daily_limit > 0:
            log_print(f"[Limite] Interrompendo após {remaining} vagas (limite diário).")
            break
        job_id = save_job(j)
        if job_id != -1:  # Nova vaga (não duplicada)
            j['id'] = job_id
            saved_jobs.append(j)
            new_jobs_count += 1

    log_print(f"\n[Main] Novas vagas salvas para processamento nesta rodada: {new_jobs_count} (restante do limite: {remaining})")

    if not saved_jobs:
        log_print("[Main] Nenhuma nova vaga inédita encontrada nesta rodada.")

    # 3. Processar Cada Vaga (ATS + Envio)
    for idx, job in enumerate(saved_jobs, 1):
        log_print(f"\n--- [{idx}/{len(saved_jobs)}] Processando: {job['title']} @ {job['company']} ({job['platform']}) ---")

        try:
            ats_res = process_job_ats(job['id'], job['title'], job['company'], job['description'])
            score = ats_res['match_score']
            reason = ats_res['match_reason']
            pdf_path = ats_res['resume_path']
            cover_path = ats_res['cover_path']
            cover_text = ats_res['cover_letter']

            job['match_score'] = score
            job['match_reason'] = reason
            job['resume_pdf_path'] = pdf_path
            job['cover_letter_path'] = cover_path

            log_print(f"   -> Match ATS: {score}% ({reason})")

            if score >= min_score:
                if dry_run:
                    log_print("   -> [Dry-Run] Simulação ativa. PDF e carta gerados, candidatura não disparada.")
                    status = 'prepared'
                elif not auto_send:
                    log_print("   -> Match aceito! Envio automático desativado — aguardando aprovação manual (aba Histórico).")
                    status = 'ready_to_send'
                else:
                    log_print("   -> Match aceito! Disparando envio/automação...")
                    status = apply_to_job(job, pdf_path, cover_text)

                update_job_status(job['id'], status, resume_path=pdf_path, cover_path=cover_path)
                job['status'] = status
            else:
                log_print(f"   -> Score {score}% abaixo do limite mínimo ({min_score}%). Vaga ignorada.")
                update_job_status(job['id'], 'skipped', resume_path=pdf_path, cover_path=cover_path)
                job['status'] = 'skipped'

        except Exception as e:
            log_print(f"   -> Erro ao processar vaga {job['title']}: {e}")
            update_job_status(job['id'], 'failed')
            job['status'] = 'failed'

    # 4. Obter Histórico da Sessão para o Relatório
    session_jobs = get_all_jobs_in_session(session_start_iso)

    # 5. Gerar Relatórios
    timestamp_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
    html_report_path = Config.REPORTS_DIR / f"relatorio_{timestamp_slug}.html"
    md_report_path = Config.REPORTS_DIR / f"relatorio_{timestamp_slug}.md"

    generate_html_report(session_jobs, html_report_path)
    generate_markdown_report(session_jobs, md_report_path)

    log_print("\n" + "=" * 65)
    log_print("[+] CICLO DE AUTOMAÇÃO CONCLUÍDO COM SUCESSO!")
    log_print("=" * 65)
    log_print(f"[*] Relatório HTML gerado em: {html_report_path}")
    log_print(f"[*] Relatório Markdown gerado em: {md_report_path}")
    log_print("=" * 65)
    # notificação
    try:
        high = sum(1 for j in session_jobs if j.get("match_score", 0) >= 80)
        notify_all("JobAutoFit concluído", f"{len(session_jobs)} vagas analisadas, {high} com match >=80%. Relatório: {html_report_path.name}")
    except Exception:
        pass

    return {"session_jobs": session_jobs, "html_report_path": html_report_path, "md_report_path": md_report_path}


def main():
    parser = argparse.ArgumentParser(description="JobAutoFit - Automação Inteligente de Candidaturas e ATS")
    parser.add_argument("--keywords", nargs="+", default=Config.TARGET_KEYWORDS, help="Palavras-chave das vagas (ex: Python Developer)")
    parser.add_argument("--location", default=Config.TARGET_LOCATION, help="Localização desejada (ex: Brasil, Remoto)")
    parser.add_argument("--min-score", type=int, default=Config.MIN_MATCH_SCORE, help="Porcentagem mínima de match ATS para candidatar-se")
    parser.add_argument("--dry-run", action="store_true", help="Apenas analisa e gera relatórios/PDFs sem enviar candidaturas")
    parser.add_argument("--enable-linkedin-posts", dest="enable_linkedin_posts", action="store_true", help="Ativa coleta de posts de recrutadores no LinkedIn")
    parser.add_argument("--disable-linkedin-posts", dest="enable_linkedin_posts", action="store_false", help="Desativa coleta de posts de recrutadores")
    parser.set_defaults(enable_linkedin_posts=None)
    args = parser.parse_args()

    run_pipeline(args.keywords, args.location, args.min_score, dry_run=args.dry_run, enable_linkedin_posts=args.enable_linkedin_posts)


if __name__ == "__main__":
    main()
