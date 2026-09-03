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

_ACCENT_MAP = str.maketrans(
    "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
    "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC"
)
_DATE_RANGE_RX = re.compile(
    r"(\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\.?\s*/?\s*(?:de\s*)?\d{4})"
    r"\s*[–-]\s*"
    r"(?:Atual|ATUAL|Present|Current|\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\.?\s*/?\s*(?:de\s*)?\d{4})",
    re.I
)

def _fold(s: str) -> str:
    """minúsculas + sem acento, preservando o comprimento (1 char -> 1 char) para os índices
    baterem com o texto original. Extração de PDF às vezes perde acentos de forma inconsistente
    (ex: cabeçalho "EXPERIÊNCIA" no texto mas marcador de busca acentuado não batia)."""
    return s.translate(_ACCENT_MAP).lower()

def _extract_section(text: str, start_marker: str, end_markers: list) -> str:
    """Extrai bloco entre start_marker e o próximo end_marker (apenas cabeçalhos em linha própria)."""
    low = _fold(text)
    start = low.find(_fold(start_marker))
    if start == -1:
        return ""
    start += len(start_marker)
    # se o cabeçalho continua na mesma linha (ex: "COMPETÊNCIAS & HABILIDADES", "COMPETÊNCIAS
    # TÉCNICAS E TECNOLOGIAS"), o marcador buscado é só um prefixo do título real — pula até a
    # quebra de linha pra não deixar a sobra ("& Habilidades") vazar pro conteúdo da seção. Mas
    # se vier ":" logo em seguida (ex: "Skills: Python, SQL"), o conteúdo pode estar colado na
    # mesma linha — aí só pula o ":" e os espaços, sem descartar a linha inteira.
    tail = re.match(r"\s*:\s*", text[start:start+10])
    if tail:
        start += tail.end()
    else:
        nl = text.find("\n", start)
        if nl != -1:
            start = nl + 1
    end = len(text)
    # procura end_marker apenas como cabeçalho (início de linha, com ou sem espaços)
    for m in end_markers:
        # regex para cabeçalho: quebra de linha + opcionais espaços + marker
        pattern = re.compile(r"\n\s*" + re.escape(_fold(m)))
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
    # nome: alguns modelos quebram o nome em uma palavra por linha (ex: "MARIANA\nCOSTA\n
    # RODRIGUES") — tenta juntar linhas consecutivas de 1 palavra em maiúsculas no topo antes
    # de cair no caso comum (nome inteiro numa linha só)
    name_lines = []
    for line in text.splitlines()[:6]:
        line = line.strip()
        if not line:
            if name_lines: break
            continue
        if len(line.split()) == 1 and line.isupper() and 1 < len(line) < 25 and "@" not in line:
            name_lines.append(line)
        else:
            break
    if len(name_lines) >= 2:
        data["personal_info"]["name"] = " ".join(name_lines).title()
    # nome: primeira linha não vazia com 2+ palavras e sem @ (só roda se o caso "1 palavra por
    # linha" acima não achou nada, senão o título do cargo logo abaixo do nome — também em
    # maiúsculas — acabava sobrescrevendo o nome já correto)
    if "name" not in data["personal_info"]:
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
    # tenta extrair bloco Skills/Competências primeiro — testa o cabeçalho completo antes do
    # parcial ("COMPETÊNCIAS TÉCNICAS E TECNOLOGIAS", usado nos PDFs que o próprio app gera)
    # pra não cortar o marcador no meio e deixar sobra ("E TECNOLOGIAS") vazando pra dentro
    # do bloco de skills
    skills_end_markers = ["EXPERIÊNCIA","FORMAÇÃO","RESUMO","PROJETOS","CURSOS","IDIOMA","OBJETIVO","EXPERIENCE","EDUCATION","SUMMARY","CONTATO","IDIOMAS"]
    skills_block = ""
    for alias in ["COMPETÊNCIAS TÉCNICAS E TECNOLOGIAS","COMPETÊNCIAS TÉCNICAS","COMPETÊNCIAS","HABILIDADES","SKILLS"]:
        skills_block = _extract_section(text, alias, skills_end_markers)
        if skills_block:
            break
    tl = (skills_block if skills_block else text).lower()
    # extrai de "Tecnologias:" ou linha com "•" do PDF gerado
    m = re.search(r"Tecnologias:\s*([^\n]+)", text, re.I)
    if m:
        tech_line = m.group(1)
        for part in re.split(r"[,;/•]", tech_line):
            p=part.strip()
            if p and len(p)<30 and p not in found:
                found.append(p)
    # extração genérica do bloco de habilidades: qualquer item vira skill, não só os da
    # lista de tecnologia abaixo — sem isso, áreas como Direito/Administrativo/PowerBI
    # ficavam sempre com skills vazias (nenhum termo delas bate com "python"/"react"/etc.)
    if skills_block:
        # remove linhas que são só um sub-rótulo (ex: "Ferramentas & Conhecimentos Técnicos:")
        # e tira o prefixo "Rótulo: " de linhas tipo "Linguagens: Python, SQL" — nos dois casos
        # o rótulo em si não é uma skill, só teria virado uma entrada bagunçada
        lines_clean = []
        for l in skills_block.splitlines():
            l = l.strip()
            if not l or l.endswith(":"):
                continue
            l = re.sub(r"^[^:\n]{2,30}:\s*", "", l)
            if l:
                lines_clean.append(l)
        cleaned_block = "\n".join(lines_clean)
        for part in re.split(r"[,;••\n|]", cleaned_block):
            p = part.strip(" .-\t")
            # limite maior que o de antes (40->60): listas "Rótulo: Skill1 Skill2 Skill3" sem
            # vírgula viram um item só (composto) em vez de serem descartadas inteiras por
            # estourar o tamanho — pior formatado, mas visível e editável, não some
            if 2 <= len(p) <= 60 and p.lower() not in ["competências técnicas e tecnologias","habilidades","skills","competências","technical skills"]:
                if p.lower() not in [f.lower() for f in found]:
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
    # summary: tenta vários cabeçalhos comuns (não só "RESUMO PROFISSIONAL" — currículos de
    # outras áreas/idiomas usam "Perfil", "Objetivo", "About", "Summary" etc.)
    summary_block = ""
    summary_end_markers = ["HABILIDADES","COMPETÊNCIAS","CURSOS","FORMAÇÃO","PROJETOS","EXPERIÊNCIA","IDIOMA","OBJETIVO","EDUCATION","EXPERIENCE","SKILLS"]
    for alias in ["RESUMO PROFISSIONAL","PERFIL PROFISSIONAL","OBJETIVO PROFISSIONAL","SOBRE MIM","SOBRE","PROFESSIONAL SUMMARY","SUMMARY","PROFILE","OBJECTIVE"]:
        summary_block = _extract_section(text, alias, summary_end_markers)
        if summary_block and len(summary_block) > 20:
            break
    if summary_block and len(summary_block) > 20:
        data["summary"] = " ".join(summary_block.split())[:800]
    else:
        # sem seção identificável: usa o topo do texto, mas corta na última frase completa
        # (em vez de truncar no meio de uma palavra/frase, o que deixava o resumo bagunçado)
        raw = " ".join(text.split())[:800]
        cut = raw.rfind(". ")
        data["summary"] = raw[:cut+1] if cut > 200 else raw
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
    exp_end_markers = ["FORMAÇÃO","PROJETOS","CURSOS","IDIOMA","EDUCATION","SKILLS","LANGUAGES","COMPETÊNCIAS"]
    exp_block = ""
    for alias in ["EXPERIÊNCIA PROFISSIONAL","EXPERIENCIA PROFISSIONAL","HISTÓRICO PROFISSIONAL","EXPERIÊNCIA","PROFESSIONAL EXPERIENCE","WORK EXPERIENCE","EXPERIENCE"]:
        exp_block = _extract_section(text, alias, exp_end_markers)
        if exp_block:
            break
    if exp_block:
        # pseudo-match usado pelos fallbacks que não vêm de um único re.finditer (grupos
        # (cargo, empresa, periodo) montados manualmente)
        class Pseudo:
            def __init__(self,s,e,g): self._s=s; self._e=e; self._g=g
            def groups(self): return self._g
            def start(self): return self._s
            def end(self): return self._e
            def group(self, n): return self._g[n-1]
        # regex para cabeçalhos: CARGO – EMPRESA | LOCAL | DATA (ex: DESENVOLVEDOR – AUTÔNOMO | LAVRAS/MG | 05/2024 – ATUAL)
        header_pattern = re.compile(r"^(.+?)\s*[–-]\s*(.+?)\s*\|\s*([^|\n]+?)\s*\|\s*(\d{2}/\d{4}\s*[–-]\s*(?:ATUAL|\d{2}/\d{4}|\d{4})|ATUAL|\d{4}\s*[–-]\s*ATUAL)", re.MULTILINE)
        headers = list(header_pattern.finditer(exp_block))
        # fallback: se não achou com 3 partes, tenta com 2 partes (cargo – empresa | data)
        if not headers:
            header_pattern2 = re.compile(r"^(.+?)\s*[–-]\s*(.+?)\s*\|\s*(\d{2}/\d{4}\s*[–-]\s*(?:ATUAL|\d{2}/\d{4})|ATUAL)", re.MULTILINE)
            headers = list(header_pattern2.finditer(exp_block))
        # fallback "cargo/empresa em linha(s) própria(s) + período sozinho na linha seguinte":
        # cobre tanto "Cargo - Empresa\nPeríodo" (2 linhas) quanto "Cargo\nEmpresa\nPeríodo"
        # (3 linhas, cargo e empresa cada um na sua própria linha, formato comum em modelos
        # de currículo de outras áreas) — sem isso, o próximo fallback (data no fim da MESMA
        # linha) só casava a linha da data, perdendo cargo/empresa e deixando "position" vazio
        if not headers:
            date_only_rx = re.compile(r"^\s*(\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\.?\s*/?\s*(?:de\s*)?\d{4})\s*[–-]\s*(?:Atual|ATUAL|Present|Current|\d{2}/\d{4}|20\d{2}|(?:Jan|Fev|Mar|Abr|Mai|Jun|Jul|Ago|Set|Out|Nov|Dez)[a-z]*\.?\s*/?\s*(?:de\s*)?\d{4})\s*$", re.I)
            tmp_headers=[]; recent=[]; offset=0
            for raw in exp_block.splitlines(keepends=True):
                line=raw.strip(); line_start=offset; offset+=len(raw)
                if not line:
                    # quebra de parágrafo: o que vem depois é quase sempre uma nova entrada,
                    # não continuação da anterior — limpa candidatos acumulados
                    recent=[]
                    continue
                if date_only_rx.match(line) and recent:
                    if len(recent)>=2:
                        title, title_start = recent[-2]
                        comp_line, _ = recent[-1]
                        cargo, empresa = title, comp_line
                    else:
                        title, title_start = recent[-1]
                        sep = "–" if "–" in title else (" - " if " - " in title else None)
                        if sep:
                            parts = title.rsplit(sep,1)
                            cargo, empresa = parts[0].strip(), parts[1].strip()
                        else:
                            cargo, empresa = title, ""
                    tmp_headers.append(Pseudo(title_start, line_start+len(line), (cargo, empresa, line)))
                    recent=[]
                elif not date_only_rx.match(line):
                    # só vira candidato a "cargo/empresa" se parecer um rótulo curto — uma
                    # frase de destaque (bullet/atividade) também costuma ser curta em número
                    # de palavras, então o critério real é não terminar em "." (frase), a não
                    # ser que a última "palavra" seja uma sigla curta tipo "S.A."/"Ltda."
                    ends_like_sentence = line.endswith(".") and len(line.rsplit(" ",1)[-1]) > 5
                    if len(line) < 80 and len(line.split()) <= 8 and not ends_like_sentence:
                        recent.append((line, line_start))
                        recent = recent[-2:]
                    else:
                        recent = []
            headers = tmp_headers
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
                    company = ""
                    if sep and sep in cargo_empresa:
                        ce_parts = cargo_empresa.split(sep)
                        if len(ce_parts)>=2:
                            position = ce_parts[0].strip().title()
                            company = ce_parts[1].strip().title()
                        else:
                            position = cargo_empresa.strip().title()
                    else:
                        position = cargo_empresa.strip().title()
                    # período: procura um intervalo de datas em qualquer parte após o cargo —
                    # em layouts de 2 colunas ("Cargo | Empresa" numa coluna, data na outra),
                    # a extração de texto do PDF costuma colar tudo numa linha só, então o
                    # período pode vir grudado no fim do nome da empresa (ex: "Empresa Junho
                    # de 2020 – Atual"). Sem isso, tanto "company" quanto "period" ficavam com
                    # essa string inteira (empresa + data juntos, sem separar nada)
                    rest = " | ".join(parts[1:]) if len(parts) > 1 else ""
                    date_embedded = _DATE_RANGE_RX.search(rest)
                    if date_embedded:
                        period = date_embedded.group(0).strip()
                        if not company:
                            company = rest[:date_embedded.start()].strip(" |").title()
                    else:
                        if not company and len(parts) > 1:
                            company = parts[1].strip().title()
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
        # último fallback: nenhum padrão de cabeçalho reconheceu o formato (currículo de outra
        # área/modelo, bem diferente do que o próprio app gera) — em vez de deixar a lista de
        # experiências vazia, trata cada parágrafo do bloco como uma experiência
        if not data["experiences"]:
            date_rx = re.compile(r"(\d{2}/\d{4}|20\d{2})\s*[–-]\s*(Atual|ATUAL|Present|Current|\d{2}/\d{4}|20\d{2})", re.I)
            for para in [p.strip() for p in re.split(r"\n\s*\n", exp_block) if p.strip()][:10]:
                lines = [l.strip() for l in para.splitlines() if l.strip()]
                if not lines: continue
                dm = date_rx.search(para)
                highlights = [l.strip(" •-") for l in lines[1:] if len(l.strip(" •-")) > 15][:5]
                data["experiences"].append({"company": "Empresa", "position": lines[0][:120].title(), "period": dm.group(0).strip() if dm else "", "highlights": highlights})
    # education: bloco FORMAÇÃO ACADÊMICA
    edu_block = ""
    for alias in ["FORMAÇÃO ACADÊMICA","FORMAÇÃO","EDUCAÇÃO","EDUCATION","ACADEMIC BACKGROUND"]:
        edu_block = _extract_section(text, alias, ["PROJETOS","EXPERIÊNCIA","CURSOS","HABILIDADES","COMPETÊNCIAS","IDIOMA","EXPERIENCE","SKILLS"])
        if edu_block:
            break
    if edu_block:
        # ex: Tecnólogo em Análise e Desenvolvimento de Sistemas\nCentro Universitário Unilavras – Conclusão: 2022
        lines_all = [l for l in edu_block.splitlines()]
        # quebra o bloco em uma entrada por linha que começa com palavra-chave de qualificação
        # — sem isso só a primeira formação era capturada, perdendo qualquer segunda
        # graduação/curso listado no mesmo currículo (comum ter ensino médio + superior, ou
        # 2 graduações)
        degree_kw = re.compile(r"^\s*(Tecnólogo|Tecnologo|Bacharel(ado)?|Gradua(ção|do)|MBA|Ensino (Médio|Fundamental|Superior)|Pós[- ]?gradua|Curso T[ée]cnico|Técnico em|Mestrado|Doutorado|Licenciatura)", re.I)
        starts = [i for i, l in enumerate(lines_all) if l.strip() and degree_kw.match(l.strip())]
        if starts:
            chunks = []
            for idx, s in enumerate(starts):
                e = starts[idx+1] if idx+1 < len(starts) else len(lines_all)
                chunks.append([l.strip() for l in lines_all[s:e] if l.strip()])
        else:
            chunks = [[l.strip() for l in lines_all if l.strip()]]
        for lines in chunks[:6]:
            if not lines: continue
            degree = lines[0]
            institution = ""
            year = ""
            # procura instituição e ano
            for l in lines[1:]:
                if re.search(r"20\d{2}", l):
                    my = re.search(r"20\d{2}", l)
                    if my: year = my.group(0)
                    # só usa esta linha como instituição se uma linha anterior ainda não deu
                    # uma — senão uma segunda linha com ano (ex: "Em andamento (Previsão:
                    # 12/2027)") sobrescrevia a instituição já correta com essa data
                    if not institution:
                        if "–" in l:
                            institution = l.split("–")[0].strip()
                        elif "conclusão" in l.lower():
                            institution = re.sub(r"–.*|conclusão.*", "", l, flags=re.I).strip()
                        else:
                            institution = l.strip()
                    break
                else:
                    if not institution and len(l) > 5:
                        institution = l.strip()
            if not year:
                # o ano às vezes vem grudado no próprio título (ex: "Bacharelado em Ciência
                # da Computação Concluído em 2023"), sem linha separada pra formação/instituição
                my = re.search(r"20\d{2}", degree)
                if my:
                    year = my.group(0)
                    degree = re.sub(r"\s*Conclu[ií]d[oa]?\s*(em)?\s*20\d{2}\s*$", "", degree, flags=re.I).strip()
            data["education"].append({"degree": degree.title(), "institution": institution.title() if institution else "Instituição", "year": year})
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
