import sys
import argparse
from datetime import datetime
from pathlib import Path

import json
from config import Config
from db import init_db, save_job, update_job_match, update_job_status, get_all_jobs_in_session, get_db_connection
from collector import collect_all_jobs
from ats_optimizer import process_job_ats
from sender import apply_to_job
from report import generate_html_report, generate_markdown_report
from filters import filter_jobs
from notify import notify_all

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

    print("=" * 65)
    print("[+] INICIANDO AUTOMATIZADOR DE CURRICULOS & VAGAS (JobAutoFit)")
    print("=" * 65)
    print(f"[*] Palavras-chave: {args.keywords}")
    print(f"[*] Localização: {args.location}")
    print(f"[*] Nota de Match Mínima: {args.min_score}%")
    print(f"[*] Provedor de IA: {Config.LLM_PROVIDER.upper()}")
    print("=" * 65)

    # 1. Inicializar Banco de Dados
    init_db()
    session_start_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 2. Coletar Vagas (Gupy, LinkedIn, Remotive)
    # carregar filtros avançados de search_config.json se existir
    filter_cfg = {}
    try:
        if Config.SEARCH_CONFIG_PATH.exists():
            filter_cfg = json.loads(Config.SEARCH_CONFIG_PATH.read_text(encoding="utf-8"))
    except: filter_cfg={}

    # LinkedIn posts de recrutadores: CLI sobrepoe config; default True se não definido
    enable_posts = filter_cfg.get("enable_linkedin_posts", True)
    if args.enable_linkedin_posts is not None:
        enable_posts = args.enable_linkedin_posts
    linkedin_posts_limit = int(filter_cfg.get("linkedin_posts_limit", filter_cfg.get("limit_per_source", 8)) or 8)
    if enable_posts:
        print(f"[*] Posts de recrutadores LinkedIn: ATIVADO (limite {linkedin_posts_limit}/keyword)")
    else:
        print(f"[*] Posts de recrutadores LinkedIn: DESATIVADO")

    raw_jobs = collect_all_jobs(args.keywords, location=args.location, limit_per_source=filter_cfg.get("limit_per_source", 8), enable_linkedin_posts=enable_posts, linkedin_posts_limit=linkedin_posts_limit)

    # aplicar filtros avançados antes de salvar
    if filter_cfg:
        before = len(raw_jobs)
        raw_jobs = filter_jobs(raw_jobs, filter_cfg)
        print(f"[Filtros] {before} -> {len(raw_jobs)} vagas após filtros avançados (salário/nível/PCD/inglês/excluir/bloqueadas)")

    # daily limit
    daily_limit = int(filter_cfg.get("daily_limit", Config.DAILY_LIMIT) or Config.DAILY_LIMIT)
    # contar já processados hoje
    try:
        con = get_db_connection()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM jobs WHERE date(created_at)=date('now') AND status IN ('applied','prepared')")
        today_count = cur.fetchone()[0]
        con.close()
    except: today_count=0
    remaining = max(0, daily_limit - today_count)
    if remaining==0 and daily_limit>0:
        print(f"[Limite] Limite diário de {daily_limit} atingido. Nenhuma vaga será processada hoje.")
        raw_jobs=[]

    saved_jobs = []
    new_jobs_count = 0

    for j in raw_jobs:
        if len(saved_jobs) >= remaining and daily_limit>0:
            print(f"[Limite] Interrompendo após {remaining} vagas (limite diário).")
            break
        job_id = save_job(j)
        if job_id != -1: # Nova vaga (não duplicada)
            j['id'] = job_id
            saved_jobs.append(j)
            new_jobs_count += 1

    print(f"\n[Main] Novas vagas salvas para processamento nesta rodada: {new_jobs_count} (restante do limite: {remaining})")

    if not saved_jobs:
        print("[Main] Nenhuma nova vaga inédita encontrada nesta rodada.")

    # 3. Processar Cada Vaga (ATS + Envio)
    for idx, job in enumerate(saved_jobs, 1):
        print(f"\n--- [{idx}/{len(saved_jobs)}] Processando: {job['title']} @ {job['company']} ({job['platform']}) ---")
        
        # Otimização ATS via IA
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
            
            print(f"   -> Match ATS: {score}% ({reason})")
            
            if score >= args.min_score:
                if args.dry_run:
                    print("   -> [Dry-Run] Simulação ativa. PDF e carta gerados, candidatura não disparada.")
                    status = 'prepared'
                else:
                    print("   -> Match aceito! Disparando envio/automação...")
                    status = apply_to_job(job, pdf_path, cover_text)
                    
                update_job_status(job['id'], status, resume_path=pdf_path, cover_path=cover_path)
                job['status'] = status
            else:
                print(f"   -> Score {score}% abaixo do limite mínimo ({args.min_score}%). Vaga ignorada.")
                update_job_status(job['id'], 'skipped', resume_path=pdf_path, cover_path=cover_path)
                job['status'] = 'skipped'
                
        except Exception as e:
            print(f"   -> Erro ao processar vaga {job['title']}: {e}")
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

    print("\n" + "=" * 65)
    print("[+] CICLO DE AUTOMAÇÃO CONCLUÍDO COM SUCESSO!")
    print("=" * 65)
    print(f"[*] Relatório HTML gerado em: {html_report_path}")
    print(f"[*] Relatório Markdown gerado em: {md_report_path}")
    print("=" * 65)
    # notificação
    try:
        high = sum(1 for j in session_jobs if j.get("match_score",0) >= 80)
        notify_all("JobAutoFit concluído", f"{len(session_jobs)} vagas analisadas, {high} com match >=80%. Relatório: {html_report_path.name}")
    except: pass

if __name__ == "__main__":
    main()