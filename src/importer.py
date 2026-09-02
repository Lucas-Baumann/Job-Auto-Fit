import re
import json
from pathlib import Path

def extract_text_from_pdf(pdf_path: Path) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(pdf_path))
        txt = "\n".join([p.extract_text() or "" for p in reader.pages])
        return txt
    except Exception as e:
        raise RuntimeError(f"Falha ao ler PDF: {e} (pip install pypdf)")

def extract_text_from_docx(docx_path: Path) -> str:
    try:
        import docx
        d = docx.Document(str(docx_path))
        return "\n".join([p.text for p in d.paragraphs])
    except Exception as e:
        raise RuntimeError(f"Falha ao ler DOCX: {e} (pip install python-docx)")

def _extract_section(text: str, start_marker: str, end_markers: list) -> str:
    """Extrai bloco entre start_marker e o próximo end_marker (apenas cabeçalhos em linha própria)."""
    low = text.lower()
    start = low.find(start_marker.lower())
    if start == -1:
        return ""
    start += len(start_marker)
    end = len(text)
    # procura end_marker apenas como cabeçalho (início de linha, com ou sem espaços)
    for m in end_markers:
        # regex para cabeçalho: quebra de linha + opcionais espaços + marker
        pattern = re.compile(r"\n\s*" + re.escape(m.lower()))
        match = pattern.search(low, pos=start)
        if match:
            idx = match.start()
            if idx < end:
                end = idx
    return text[start:end].strip()

def heuristic_parse_curriculum(text: str) -> dict:
    """Parse robusto: nome, email, telefone, linkedin, github, skills, resumo, experiências e formação."""
    data = {"personal_info": {}, "summary": "", "skills": [], "experiences": [], "education": [], "languages": []}
    # email
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
    if m: data["personal_info"]["email"] = m.group(0).strip()
    # telefone BR
    m = re.search(r"\(?\d{2}\)?\s*9?\d{4,5}[-.\s]?\d{4}", text)
    if m: data["personal_info"]["phone"] = m.group(0).strip()
    # linkedin (com ou sem https)
    m = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com[^\s,;]+", text, re.I)
    if m:
        url = m.group(0).strip().rstrip(".,;")
        if not url.lower().startswith("http"): url = "https://" + url
        data["personal_info"]["linkedin"] = url
    # github (com ou sem https)
    m = re.search(r"(?:https?://)?(?:www\.)?github\.com[^\s,;]+", text, re.I)
    if m:
        url = m.group(0).strip().rstrip(".,;")
        if not url.lower().startswith("http"): url = "https://" + url
        data["personal_info"]["github"] = url
    # endereço / localização (linha com Endereço)
    m = re.search(r"Endereço:\s*([^\n]+)", text, re.I)
    if m: data["personal_info"]["location"] = m.group(1).strip()
    # nome: primeira linha não vazia com 2+ palavras e sem @
    for line in text.splitlines():
        line=line.strip()
        if line and len(line.split())>=2 and "@" not in line and len(line)<60:
            if not any(k in line.lower() for k in ["curriculum","currículo","resumo","objetivo","endereço","contato","e-mail","email"]):
                # evita linhas de cabeçalho como "HABILIDADES"
                if len(line) < 40 and line.isupper() and " " in line:
                    # nome geralmente em maiúsculas no topo
                    data["personal_info"]["name"]=line.title()
                    break
                elif not line.isupper() or " " in line:
                    # fallback: primeira linha válida
                    if "name" not in data["personal_info"]:
                        data["personal_info"]["name"]=line
                        break
    if "name" not in data["personal_info"]:
        # tenta primeira linha
        for line in text.splitlines():
            if line.strip() and len(line.strip().split())>=2:
                data["personal_info"]["name"]=line.strip().title()
                break
    # skills: extrai APENAS do bloco Skills para não inventar do texto geral
    skill_keywords = ["python","java","javascript","typescript","html","css","vue.js","vue","react","next.js","nextjs","node",".net","dotnet","c#","csharp","php","ruby","rails","mysql","sql server","sql","docker","git","linux","aws","azure","fastapi","django","kubernetes","bootstrap","react native","expo","node.js","postgresql","postgres"]
    found=[]
    # tenta extrair bloco Skills/Competências primeiro
    skills_block = _extract_section(text, "COMPETÊNCIAS TÉCNICAS", ["EXPERIÊNCIA","FORMAÇÃO","RESUMO","PROJETOS","CURSOS","IDIOMA","OBJETIVO"])
    if not skills_block:
        skills_block = _extract_section(text, "COMPETÊNCIAS", ["EXPERIÊNCIA","FORMAÇÃO","RESUMO"])
    if not skills_block:
        skills_block = _extract_section(text, "HABILIDADES", ["EXPERIÊNCIA","FORMAÇÃO","RESUMO"])
    if not skills_block:
        skills_block = _extract_section(text, "SKILLS", ["EXPERIENCE","EDUCATION","SUMMARY"])
    tl = (skills_block if skills_block else text).lower()
    # extrai de "Tecnologias:" ou linha com "•" do PDF gerado
    m = re.search(r"Tecnologias:\s*([^\n]+)", text, re.I)
    if m:
        tech_line = m.group(1)
        for part in re.split(r"[,;/•]", tech_line):
            p=part.strip()
            if p and len(p)<30 and p not in found:
                found.append(p)
    # fallback "•" do PDF ATS (ex: "React • Next.js • TypeScript")
    if not found and skills_block and "•" in skills_block:
        for part in skills_block.split("•"):
            p=part.strip().replace("\n"," ")
            if p and len(p)<30 and len(p.split())<=3 and p not in found:
                # filtrar cabeçalhos
                if p.lower() not in ["competências técnicas e tecnologias","habilidades","skills"]:
                    found.append(p)
    for kw in skill_keywords:
        # usa word boundary para evitar Java em JavaScript; para .net/c# usa simples contém
        if kw in [".net","c#"]:
            matched = kw in tl
        else:
            matched = bool(re.search(r"\b" + re.escape(kw) + r"\b", tl))
        if matched:
            # evita duplicatas case-insensitive
            norm = kw.replace("csharp","C#").replace("dotnet",".NET").replace("nextjs","Next.js")
            # mapeia para display bonito
            display = {"python":"Python","java":"Java","javascript":"JavaScript","typescript":"TypeScript","html":"HTML","css":"CSS","vue.js":"Vue.js","vue":"Vue.js","react":"React","next.js":"Next.js","node":"Node.js",".net":".NET","dotnet":".NET","c#":"C#","csharp":"C#","php":"PHP","ruby":"Ruby","rails":"Rails","mysql":"MySQL","sql server":"SQL Server","sql":"SQL","docker":"Docker","git":"Git","linux":"Linux","aws":"AWS","azure":"Azure","fastapi":"FastAPI","django":"Django","kubernetes":"Kubernetes","bootstrap":"Bootstrap","react native":"React Native","expo":"Expo","node.js":"Node.js","postgresql":"PostgreSQL","postgres":"PostgreSQL"}
            key = kw.lower()
            disp = display.get(key, kw.capitalize())
            if disp not in found and disp.lower() not in [f.lower() for f in found]:
                found.append(disp)
    # adiciona inglês como skill separada se houver
    data["skills"]=found[:20]
    # summary: bloco RESUMO PROFISSIONAL até próxima seção
    summary_block = _extract_section(text, "RESUMO PROFISSIONAL", ["HABILIDADES","CURSOS","FORMAÇÃO","PROJETOS","EXPERIÊNCIA","IDIOMA","OBJETIVO"])
    if summary_block and len(summary_block)>50:
        data["summary"]= " ".join(summary_block.split())[:800]
    else:
        # fallback: primeiros 800 chars após nome
        data["summary"]= " ".join(text.split())[:800]
    # languages
    m = re.search(r"Idioma:\s*([^\n]+)", text, re.I)
    if m:
        lang_line = m.group(1).strip()
        # ex: Inglês (B2 – intermediário alto)
        data["languages"]=[lang_line]
        # também adiciona em skills se não tiver
    elif "inglês" in tl or "ingles" in tl:
        # fallback
        data["languages"]=["Inglês"]
    # experiences: bloco EXPERIÊNCIA PROFISSIONAL até fim ou FORMAÇÃO etc
    exp_block = _extract_section(text, "EXPERIÊNCIA PROFISSIONAL", ["FORMAÇÃO","PROJETOS","CURSOS","IDIOMA"])
    if not exp_block:
        exp_block = _extract_section(text, "EXPERIENCIA PROFISSIONAL", ["FORMAÇÃO","PROJETOS","CURSOS","IDIOMA"])
    if exp_block:
        # regex para cabeçalhos: CARGO – EMPRESA | LOCAL | DATA (ex: DESENVOLVEDOR – AUTÔNOMO | LAVRAS/MG | 05/2024 – ATUAL)
        header_pattern = re.compile(r"^(.+?)\s*[–-]\s*(.+?)\s*\|\s*([^|\n]+?)\s*\|\s*(\d{2}/\d{4}\s*[–-]\s*(?:ATUAL|\d{2}/\d{4}|\d{4})|ATUAL|\d{4}\s*[–-]\s*ATUAL)", re.MULTILINE)
        headers = list(header_pattern.finditer(exp_block))
        # fallback: se não achou com 3 partes, tenta com 2 partes (cargo – empresa | data)
        if not headers:
            header_pattern2 = re.compile(r"^(.+?)\s*[–-]\s*(.+?)\s*\|\s*(\d{2}/\d{4}\s*[–-]\s*(?:ATUAL|\d{2}/\d{4})|ATUAL)", re.MULTILINE)
            headers = list(header_pattern2.finditer(exp_block))
        # terceiro fallback: formato sem pipe "Cargo - Empresa Data" (ex: Desenvolvedor Júnior - GaussFleet Maio de 2026 - Atual)
        if not headers:
            # detecta linhas que terminam com data e contêm " - "
            date_tail = re.compile(r"(\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\s*/?\s*(?:de\s*)?\d{4})\s*[–-]\s*(?:Atual|ATUAL|\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\s*/?\s*(?:de\s*)?\d{4})\s*$", re.I)
            tmp_headers=[]
            for m in re.finditer(r"^(.+)$", exp_block, re.MULTILINE):
                line=m.group(1).strip()
                if line and " - " in line and date_tail.search(line) and len(line)<120 and not line.startswith("-") and not line.startswith("•"):
                    # cria pseudo-match com grupos: cargo, empresa, periodo
                    # tenta separar cargo-empresa e data
                    date_match = date_tail.search(line)
                    if date_match:
                        period = date_match.group(0).strip()
                        prefix = line[:date_match.start()].strip()
                        # prefix é "Cargo - Empresa" ou "Cargo - Empresa Local"?
                        # separa no último " - "
                        if " - " in prefix:
                            parts = prefix.rsplit(" - ",1)
                            cargo = parts[0].strip()
                            empresa = parts[1].strip()
                        elif "–" in prefix:
                            parts = prefix.rsplit("–",1)
                            cargo = parts[0].strip()
                            empresa = parts[1].strip()
                        else:
                            # trata "Autônomo" sem separador: ex "Desenvolvedor Front-end Autônomo"
                            if re.search(r"Autônomo|Autonomo", prefix, re.I):
                                m2 = re.search(r"(.+?)\s+(Autônomo|Autonomo)\s*$", prefix, re.I)
                                if m2:
                                    cargo = m2.group(1).strip()
                                    empresa = m2.group(2).strip().title()
                                else:
                                    cargo = prefix
                                    empresa = ""
                            else:
                                cargo = prefix
                                empresa = ""
                        # cria objeto similar a match com groups e start/end
                        class Pseudo:
                            def __init__(self,s,e,g): self._s=s; self._e=e; self._g=g
                            def groups(self): return self._g
                            def start(self): return self._s
                            def end(self): return self._e
                            def group(self, n): return self._g[n-1]
                        tmp_headers.append(Pseudo(m.start(), m.end(), (cargo, empresa, period)))
            headers = tmp_headers
        if headers:
            for idx, m in enumerate(headers):
                # extrai cargo, empresa, local, periodo
                if len(m.groups()) == 4:
                    position_raw, company_raw, local_raw, period_raw = m.groups()
                    position = position_raw.strip().title()
                    company = company_raw.strip().title()
                    period = period_raw.strip()
                else:
                    position = m.group(1).strip().title()
                    company = m.group(2).strip().title()
                    period = m.group(3).strip()
                # highlights: texto entre fim deste header e inicio do próximo
                start = m.end()
                end = headers[idx+1].start() if idx+1 < len(headers) else len(exp_block)
                block = exp_block[start:end].strip()
                # remove prefix "Atividades desempenhadas:" e limpa
                block = re.sub(r"Atividades desempenhadas:\s*", "", block, flags=re.I)
                # junta linhas e quebra em frases por "." ou "•" ou "-"
                # primeiro normaliza quebras
                block = block.replace("\r"," ").replace("\n"," ")
                # split por "." + espaço (mantém frases)
                raw_highlights = []
                # tenta split por bullet " - " com espaços, "•" ou ". " (não quebra front-end)
                for part in re.split(r"\s+-\s+|[•\u2022]|\.\s+", block):
                    p = part.strip(" .;,-\n\r")
                    if len(p) > 20 and not p.lower().startswith("atividades"):
                        # evita duplicatas e linhas muito curtas
                        raw_highlights.append(p[:200])
                # se não achou, pega linhas originais
                if not raw_highlights:
                    for line in block.splitlines():
                        c = line.strip(" •-")
                        if len(c) > 20:
                            raw_highlights.append(c[:200])
                highlights = raw_highlights[:5]
                data["experiences"].append({"company": company or "Empresa", "position": position, "period": period, "highlights": highlights})
        else:
            # fallback antigo por linhas se regex não pegou (ex: formato diferente)
            lines = exp_block.splitlines()
            current = None
            for line in lines:
                clean = line.strip()
                if not clean: continue
                is_header = ("|" in clean and (re.search(r"\d{2}/\d{4}", clean) or "ATUAL" in clean.upper() or re.search(r"20\d{2}", clean)))
                if is_header:
                    if current: data["experiences"].append(current)
                    parts = [p.strip() for p in clean.split("|")]
                    cargo_empresa = parts[0] if len(parts)>=1 else clean
                    sep = "–" if "–" in cargo_empresa else ("-" if " - " in cargo_empresa else None)
                    if sep and sep in cargo_empresa:
                        ce_parts = cargo_empresa.split(sep)
                        if len(ce_parts)>=2:
                            position = ce_parts[0].strip().title()
                            company = ce_parts[1].strip().title()
                        else:
                            position = cargo_empresa.strip().title()
                            company = parts[1].strip().title() if len(parts)>1 else ""
                    else:
                        position = cargo_empresa.strip().title()
                        company = parts[1].strip().title() if len(parts)>1 else ""
                    period = parts[-1].strip() if len(parts)>=3 else (parts[1].strip() if len(parts)==2 else "")
                    if not re.search(r"\d{2}/\d{4}|20\d{2}|ATUAL", period, re.I):
                        mdate = re.search(r"(\d{2}/\d{4}\s*[–-]\s*(?:ATUAL|\d{2}/\d{4}|\d{4})|20\d{2}\s*[–-]\s*(?:ATUAL|20\d{2}))", clean)
                        if mdate: period = mdate.group(0).strip()
                    current = {"company": company or "Empresa", "position": position, "period": period, "highlights": []}
                else:
                    if current is not None:
                        low = clean.lower()
                        if clean.startswith("•") or clean.startswith("-") or len(clean) > 20:
                            if not low.startswith("atividades desempenhadas"):
                                hl = re.sub(r"^[•\-\u2022\s]+", "", clean).strip()
                                if hl and len(hl) > 10:
                                    current["highlights"].append(hl)
                    else:
                        pass
            if current: data["experiences"].append(current)
        # se ainda não achou, fallback antigo: tenta extrair blocos genéricos
        if not data["experiences"]:
            # tenta padrão simples: linhas com ano
            for m in re.finditer(r"([A-Za-zÀ-ú\s\-–]+)\s*[–-]\s*([A-Za-z0-9\s\/]+)\s*\|\s*([^\n]+)", exp_block):
                data["experiences"].append({"company": m.group(2).strip().title(), "position": m.group(1).strip().title(), "period": m.group(3).strip(), "highlights": []})
    # education: bloco FORMAÇÃO ACADÊMICA
    edu_block = _extract_section(text, "FORMAÇÃO ACADÊMICA", ["PROJETOS","EXPERIÊNCIA","CURSOS","HABILIDADES","IDIOMA"])
    if not edu_block:
        edu_block = _extract_section(text, "FORMAÇÃO", ["PROJETOS","EXPERIÊNCIA","CURSOS"])
    if edu_block:
        # ex: Tecnólogo em Análise e Desenvolvimento de Sistemas\nCentro Universitário Unilavras – Conclusão: 2022
        lines = [l.strip() for l in edu_block.splitlines() if l.strip()]
        degree = lines[0] if lines else ""
        institution = ""
        year = ""
        # procura instituição e ano
        for l in lines[1:]:
            if re.search(r"20\d{2}", l):
                # extrai ano
                my = re.search(r"20\d{2}", l)
                if my: year = my.group(0)
                # instituição é antes do "–" ou "Conclusão"
                if "–" in l:
                    institution = l.split("–")[0].strip()
                elif "conclusão" in l.lower():
                    # pega antes de "–" ou "conclusão"
                    institution = re.sub(r"–.*|conclusão.*", "", l, flags=re.I).strip()
                else:
                    institution = l.strip()
                break
            else:
                if not institution and len(l) > 5:
                    institution = l.strip()
        if degree:
            data["education"].append({"degree": degree.title(), "institution": institution.title() if institution else "Instituição", "year": year or "2022"})
    # fallback se não achou formação mas tem linha com "Tecnólogo" ou "Bacharel"
    if not data["education"]:
        m = re.search(r"(Tecnólogo|Bacharel|Graduação|Curso)[^\n]*", text, re.I)
        if m:
            deg = m.group(0).strip()
            # tenta pegar próxima linha como instituição
            idx = text.lower().find(deg.lower()) + len(deg)
            snippet = text[idx:idx+200]
            inst_m = re.search(r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)", snippet)
            inst = inst_m.group(0) if inst_m else ""
            ym = re.search(r"20\d{2}", snippet)
            year = ym.group(0) if ym else ""
            data["education"].append({"degree": deg.title(), "institution": inst.title() if inst else "Instituição", "year": year})

    # limpa highlights vazios e limita
    for exp in data["experiences"]:
        exp["highlights"] = exp["highlights"][:5]

    return data

def llm_parse_curriculum(text: str) -> dict:
    """Tenta usar IA (Config.LLM_PROVIDER) para parsear CV em JSON estruturado."""
    try:
        from config import Config
        # verifica se tem alguma chave configurada
        has_key = any([Config.GEMINI_API_KEY, Config.OPENAI_API_KEY, Config.CLAUDE_API_KEY, Config.GROQ_API_KEY, Config.OPENROUTER_API_KEY, Config.CUSTOM_LLM_KEY]) or Config.LLM_PROVIDER=="ollama"
        if not has_key:
            return {}
        from ats_optimizer import call_llm
        prompt = f"""
Você é um parser de currículos. Converta o texto de currículo abaixo para JSON EXATO no formato curriculum_base.json.

FORMATO ESPERADO (exemplo):
{{
  "personal_info": {{"name":"Nome Completo","email":"a@b.com","phone":"(11) 99999-9999","location":"Cidade - UF","linkedin":"https://linkedin.com/in/...","github":"https://github.com/..."}},
  "summary": "Resumo profissional em 2-3 frases mantendo veracidade...",
  "skills": ["Python","React","Docker"],
  "experiences": [{{"company":"Empresa","position":"Cargo","period":"05/2024 - Atual","highlights":["Fez X","Fez Y"]}}],
  "education": [{{"degree":"Tecnólogo em ...","institution":"Universidade","year":"2022"}}],
  "languages": ["Inglês (B2)"]
}}

REGRAS:
- NÃO invente dados, use apenas o texto fornecido.
- Extraia TODAS as experiências com company, position, period e highlights (cada atividade/bullet).
- Extraia formação acadêmica corretamente.
- Skills: extraia de "Habilidades"/"Tecnologias" (lista completa).
- Retorne APENAS JSON puro, sem markdown, sem ```json, sem comentários.

TEXTO DO CURRÍCULO:
{text[:4000]}
"""
        resp = call_llm(prompt)
        if not resp: return {}
        clean = resp.replace("```json","").replace("```","").strip()
        # pega primeiro { até último }
        start = clean.find("{")
        end = clean.rfind("}")
        if start==-1 or end==-1: return {}
        data = json.loads(clean[start:end+1])
        # valida chaves mínimas
        if "personal_info" in data and "experiences" in data:
            return data
    except Exception as e:
        print(f"[Importer][LLM] falhou: {e}")
    return {}

def import_file_to_curriculum(file_path: Path) -> dict:
    ext = file_path.suffix.lower()
    if ext==".pdf":
        txt = extract_text_from_pdf(file_path)
    elif ext in (".docx",".doc"):
        txt = extract_text_from_docx(file_path)
    elif ext in (".txt",".md"):
        txt = file_path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError("Formato não suportado. Use PDF, DOCX ou TXT.")
    # tenta LLM primeiro se configurada (melhor análise)
    llm_data = llm_parse_curriculum(txt)
    if llm_data and llm_data.get("experiences"):
        # mescla: LLM tem prioridade para experiências/educação, heurístico para fallback de contato
        heur = heuristic_parse_curriculum(txt)
        # garante personal_info completo
        for k,v in heur.get("personal_info",{}).items():
            if k not in llm_data.get("personal_info",{}) or not llm_data["personal_info"][k]:
                llm_data.setdefault("personal_info",{})[k]=v
        # se LLM não trouxe skills, usa heurístico
        if not llm_data.get("skills"):
            llm_data["skills"]=heur.get("skills",[])
        return llm_data
    return heuristic_parse_curriculum(txt)
