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

def heuristic_parse_curriculum(text: str) -> dict:
    """Parse simples: tenta extrair nome, email, telefone, skills e resumo."""
    data = {"personal_info": {}, "summary": "", "skills": [], "experiences": [], "education": [], "languages": []}
    # email
    m = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}", text)
    if m: data["personal_info"]["email"] = m.group(0)
    # telefone BR
    m = re.search(r"\(?\d{2}\)?\s*9?\d{4}[-.\s]?\d{4}", text)
    if m: data["personal_info"]["phone"] = m.group(0)
    # linkedin
    m = re.search(r"https?://[^\s]*linkedin[^\s]*", text, re.I)
    if m: data["personal_info"]["linkedin"] = m.group(0)
    # github
    m = re.search(r"https?://[^\s]*github[^\s]*", text, re.I)
    if m: data["personal_info"]["github"] = m.group(0)
    # nome: primeira linha não vazia com 2+ palavras e sem @
    for line in text.splitlines():
        line=line.strip()
        if line and len(line.split())>=2 and "@" not in line and len(line)<60:
            # heurística nome
            if not any(k in line.lower() for k in ["curriculum","currículo","resumo","objetivo"]):
                data["personal_info"]["name"]=line
                break
    # skills: procurar linha com skills/tecnologias
    skill_keywords = ["python","java","javascript","sql","docker","git","react","node","aws","azure","linux","fastapi","django","kubernetes","typescript","html","css"]
    found=[]
    tl=text.lower()
    for kw in skill_keywords:
        if kw in tl:
            found.append(kw.capitalize() if kw!="sql" else "SQL")
    data["skills"]=found
    # summary: primeiros 500 chars após nome
    data["summary"]=text[:500].strip().replace("\n"," ")[:600]
    return data

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
    return heuristic_parse_curriculum(txt)
