import os
import json
import hashlib
import requests
from pathlib import Path
from typing import Dict, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from config import Config

SKILLS_IA_DIR = Config.BASE_DIR / "skills_ia"

def load_skills_context() -> str:
    """Carrega todos os arquivos .md de skills_ia como contexto para a IA."""
    if not SKILLS_IA_DIR.exists():
        return ""
    parts = []
    for f in sorted(SKILLS_IA_DIR.glob("*.md")):
        content = f.read_text(encoding="utf-8", errors="ignore")
        # extrai nome e conteúdo, pulando frontmatter YAML se houver
        clean = content.split("---", 2)[-1] if content.startswith("---") else content
        parts.append(f"=== SKILL: {f.name} ===\n{clean.strip()[:3000]}\n")
    return "\n".join(parts)

def load_base_curriculum() -> dict:
    path = Config.CURRICULUM_PATH
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de curriculo base nao encontrado em {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _call_openai_compat(prompt: str, api_key: str, base_url: str, model: str) -> str:
    try:
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
        r = requests.post(base_url, headers=headers, json=payload, timeout=45)
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            print(f"[ATS AI] OpenAI-compat erro {r.status_code}: {r.text[:300]}")
    except Exception as e:
        print(f"[ATS AI] OpenAI-compat erro: {e}")
    return ""

def call_llm(prompt: str) -> str:
    """Chama a IA configurada (gemini|ollama|openai|claude|groq|custom) — todos opcionais."""
    provider = Config.LLM_PROVIDER
    
    if provider == "gemini" and Config.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=Config.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            # não existe fallback real para outro provedor aqui — quem chama (evaluate_and_optimize_resume)
            # recebe "" e usa o heurístico por palavras-chave
            print(f"[ATS AI] Erro Gemini: {e}. Usando heurístico como fallback.")
            return ""
    if provider == "openai" and Config.OPENAI_API_KEY:
        return _call_openai_compat(prompt, Config.OPENAI_API_KEY, "https://api.openai.com/v1/chat/completions", "gpt-4o-mini")
    if provider == "claude" and Config.CLAUDE_API_KEY:
        # Claude usa header x-api-key e formato messages
        try:
            headers = {"x-api-key": Config.CLAUDE_API_KEY, "Content-Type": "application/json", "anthropic-version": "2023-06-01"}
            payload = {"model": "claude-3-haiku-20240307", "max_tokens": 2048, "messages": [{"role": "user", "content": prompt}]}
            r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload, timeout=45)
            if r.status_code == 200:
                return "".join([c["text"] for c in r.json()["content"] if c["type"]=="text"])
            print(f"[ATS AI] Claude erro {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"[ATS AI] Claude erro: {e}")
        return ""
    if provider == "groq" and Config.GROQ_API_KEY:
        return _call_openai_compat(prompt, Config.GROQ_API_KEY, "https://api.groq.com/openai/v1/chat/completions", "llama3-8b-8192")
    if provider == "openrouter" and Config.OPENROUTER_API_KEY:
        # Modelos para tentar (ordem de preferência)
        models_to_try = []
        seen = set()
        for m in [Config.OPENROUTER_MODEL, 
                  "minimax/minimax-m3:free",
                  "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"]:
            if m and m not in seen:
                seen.add(m)
                models_to_try.append(m)

        for model in models_to_try:
            try:
                headers = {
                    "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}", 
                    "Content-Type": "application/json", 
                    "HTTP-Referer": "https://github.com/Lucas-Baumann/Job-Auto-Fit", 
                    "X-Title": "JobAutoFit"
                }
                payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000}
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                                 headers=headers,
                                  json=payload, 
                                  timeout=45)
                if r.status_code == 200:
                    return r.json()["choices"][0]["message"]["content"]
                else:
                    err = f"HTTP {r.status_code}: {r.text[:500]}"
                    print(f"[ATS AI] OpenRouter modelo '{model}' falhou: {r.status_code} - {r.text[:300]}")
                    continue
            except Exception as e:
                print(f"[ATS AI] OpenRouter erro com modelo '{model}': {e}")
                continue
        # Se chegou aqui, todos falharam
        print(f"[ATS AI] OpenRouter: todos os modelos falharam.")
        return ""
    if provider == "custom" and Config.CUSTOM_LLM_URL and Config.CUSTOM_LLM_KEY:
        return _call_openai_compat(prompt, Config.CUSTOM_LLM_KEY, Config.CUSTOM_LLM_URL, "default")

    if provider == "ollama" or not any([Config.GEMINI_API_KEY, Config.OPENAI_API_KEY, Config.CLAUDE_API_KEY, Config.GROQ_API_KEY, Config.OPENROUTER_API_KEY, Config.CUSTOM_LLM_KEY]):
        try:
            url = f"{Config.OLLAMA_HOST}/api/generate"
            payload = {"model": Config.OLLAMA_MODEL, "prompt": prompt, "stream": False}
            res = requests.post(url, json=payload, timeout=60)
            if res.status_code == 200:
                return res.json().get('response', '')
        except Exception as e:
            print(f"[ATS AI] Ollama erro: {e}.")
    return ""

def _ats_cache_key(job_title: str, company: str, job_description: str, base_cv: dict) -> str:
    raw = json.dumps({"t": job_title, "c": company, "d": job_description, "cv": base_cv}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def evaluate_and_optimize_resume(job_title: str, company: str, job_description: str, base_cv: dict) -> Tuple[int, str, dict, str]:
    """
    Analisa o grau de compatibilidade e otimiza o curriculo para passar pelos filtros ATS.
    Retorna: (score_0_100, motivo_match, cv_otimizado_dict, carta_de_apresentacao)
    """
    # cache por hash (vaga+currículo) evita gastar cota gratuita da IA reprocessando a mesma
    # combinação (ex: reruns/testes) — só cacheia resultado real de IA, não o heurístico (é instantâneo)
    from db import get_ats_cache, save_ats_cache
    cache_key = _ats_cache_key(job_title, company, job_description, base_cv)
    optimized_cv = json.loads(json.dumps(base_cv))  # copia profunda
    cached = get_ats_cache(cache_key)
    if cached:
        if cached.get("optimized_summary"):
            optimized_cv["summary"] = cached["optimized_summary"]
        if cached.get("optimized_skills"):
            try:
                optimized_cv["skills"] = json.loads(cached["optimized_skills"])
            except Exception:
                pass
        return cached["score"], cached["reason"], optimized_cv, cached.get("cover_letter") or ""

    # Carrega contexto das skills_ia (se existir no .exe ou no sistema de arquivos)
    skills_context = load_skills_context()
    prompt = f"""
Voce e um especialista em recrutamento e sistemas ATS (Applicant Tracking System).

--- CONTEXTO DAS SKILLS DISPONIVEIS ---
{skills_context}

--- VAGA ---
Titulo: {job_title}
Empresa: {company}
Descricao:
{job_description[:3000]}

--- CURRICULO BASE DO CANDIDATO ---
{json.dumps(base_cv, ensure_ascii=False, indent=2)}

--- INSTRUÇÕES ---
1. Calcule a porcentagem de compatibilidade (0 a 100) baseada nos requisitos da vaga vs habilidades do candidato.
2. Utilize o contexto das SKILLS DISPONIVEIS para guiar a reestruturacao (se aplicavel).
3. Reescreva o resumo profissional e selecione/reorganize as principais habilidades e destaques de experiencia para DESTACAR os termos exatos exigidos pela vaga (SEM INVENTAR dados falsos).
4. Escreva uma carta de apresentacao (Cover Letter) curta, profissional e persuasiva em portugues.

Responda EXATAMENTE no seguinte formato JSON (sem markdown de bloco de codigo):
{{
  "match_score": 85,
  "match_reason": "Breve justificativa dos pontos de aderencia.",
  "optimized_summary": "Resumo profissional focado nas palavras-chave da vaga...",
  "optimized_skills": ["Habilidade 1", "Habilidade 2", "Habilidade 3"],
  "cover_letter": "Texto da carta de apresentacao..."
}}
"""
    response_text = call_llm(prompt)

    score = 50
    reason = "Análise preliminar realizada."
    cover_letter = f"Prezada equipe da {company},\n\nTenho grande interesse na vaga de {job_title}. Anexo meu curriculo para apreciação.\n\nAtenciosamente,\n{base_cv.get('personal_info', {}).get('name')}"

    if response_text:
        try:
            # Limpar formatação markdown se houver
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(clean_json)

            score = parsed.get("match_score", 50)
            reason = parsed.get("match_reason", reason)
            optimized_summary = parsed.get("optimized_summary", "")
            optimized_skills = parsed.get("optimized_skills", [])
            if optimized_summary:
                optimized_cv["summary"] = optimized_summary
            if optimized_skills:
                optimized_cv["skills"] = optimized_skills
            if "cover_letter" in parsed:
                cover_letter = parsed["cover_letter"]
            try:
                save_ats_cache(cache_key, score, reason, optimized_summary, json.dumps(optimized_skills, ensure_ascii=False), cover_letter)
            except Exception as e:
                print(f"[ATS AI] Falha ao salvar cache: {e}")
        except Exception as e:
            print(f"[ATS AI] Falha ao ler resposta JSON da IA: {e}")
    else:
        # Fallback Heurístico simples caso IA não esteja configurada
        kw_count = sum(1 for kw in base_cv.get('skills', []) if kw.lower() in job_description.lower())
        score = min(90, 40 + (kw_count * 10))
        reason = f"Correspondência heurística de {kw_count} palavras-chave no texto da vaga."

    return score, reason, optimized_cv, cover_letter

def generate_ats_pdf(cv_data: dict, output_path: Path):
    """Gera um curriculo em formato PDF com layout ATS-friendly (limpo e legível por leitores automáticos)."""
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )
    
    styles = getSampleStyleSheet()
    
    # Estilos customizados
    name_style = ParagraphStyle('NameStyle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#1A2B4C'), alignment=1)
    contact_style = ParagraphStyle('ContactStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, alignment=1, textColor=colors.HexColor('#4A5568'))
    section_title = ParagraphStyle('SectionTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=12, leading=16, textColor=colors.HexColor('#1A2B4C'), spaceBefore=10, spaceAfter=4)
    body_style = ParagraphStyle('BodyStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=14, textColor=colors.HexColor('#2D3748'))
    bullet_style = ParagraphStyle('BulletStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=13, leftIndent=12, textColor=colors.HexColor('#2D3748'))
    
    story = []
    p_info = cv_data.get('personal_info', {})
    
    # Cabeçalho
    story.append(Paragraph(p_info.get('name', 'Candidato'), name_style))
    contact_parts = [p_info.get('email'), p_info.get('phone'), p_info.get('location'), p_info.get('linkedin')]
    contact_text = " | ".join([p for p in contact_parts if p])
    story.append(Paragraph(contact_text, contact_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CBD5E0'), spaceAfter=8))
    
    # Resumo
    if cv_data.get('summary'):
        story.append(Paragraph("RESUMO PROFISSIONAL", section_title))
        story.append(Paragraph(cv_data['summary'], body_style))
        story.append(Spacer(1, 8))
        
    # Habilidades / Competências (ATS Keywords)
    if cv_data.get('skills'):
        story.append(Paragraph("COMPETÊNCIAS TÉCNICAS E TECNOLOGIAS", section_title))
        skills_text = " • ".join(cv_data['skills'])
        story.append(Paragraph(skills_text, body_style))
        story.append(Spacer(1, 8))
        
    # Experiência Profissional
    if cv_data.get('experiences'):
        story.append(Paragraph("EXPERIÊNCIA PROFISSIONAL", section_title))
        for exp in cv_data['experiences']:
            title_line = f"<b>{exp.get('position')}</b> — {exp.get('company')} ({exp.get('period')})"
            story.append(Paragraph(title_line, body_style))
            for hl in exp.get('highlights', []):
                story.append(Paragraph(f"• {hl}", bullet_style))
            story.append(Spacer(1, 6))
            
    # Formação Acadêmica
    if cv_data.get('education'):
        story.append(Paragraph("FORMAÇÃO ACADÊMICA", section_title))
        for edu in cv_data['education']:
            edu_line = f"<b>{edu.get('degree')}</b> — {edu.get('institution')} ({edu.get('year')})"
            story.append(Paragraph(edu_line, body_style))
            
    doc.build(story)

def process_job_ats(job_id: int, job_title: str, company: str, job_description: str) -> dict:
    """Orquestra a análise ATS e a geração dos arquivos (PDF e Cover Letter)."""
    base_cv = load_base_curriculum()
    score, reason, optimized_cv, cover_letter = evaluate_and_optimize_resume(job_title, company, job_description, base_cv)
    
    pdf_filename = Config.OUTPUT_DIR / f"CV_{company.replace(' ', '_')}_{job_id}.pdf"
    cover_filename = Config.OUTPUT_DIR / f"CoverLetter_{company.replace(' ', '_')}_{job_id}.txt"
    
    # Gerar PDF
    generate_ats_pdf(optimized_cv, pdf_filename)
    
    # Salvar Carta de Apresentação
    with open(cover_filename, 'w', encoding='utf-8') as f:
        f.write(cover_letter)
        
    return {
        "match_score": score,
        "match_reason": reason,
        "resume_path": str(pdf_filename),
        "cover_path": str(cover_filename),
        "cover_letter": cover_letter
    }