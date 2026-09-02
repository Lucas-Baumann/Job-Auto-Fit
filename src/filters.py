import re
from datetime import datetime, timedelta
from typing import Dict, List

# Helpers de parsing

def parse_salary(text: str) -> int:
    """Extrai maior valor salarial encontrado em reais (R$). Retorna 0 se não achar."""
    if not text:
        return 0
    # padrões: R$ 5.000, R$ 5000, R$ 5.000,00, R$ 15k, 5000 BRL
    vals = []
    for m in re.finditer(r"R\$\s*([\d\.\,]+)\s*(k)?", text, re.I):
        raw = m.group(1).replace(".", "").replace(",", ".")
        try:
            v = float(raw)
            if m.group(2):  # k
                v *= 1000
            vals.append(int(v))
        except: pass
    for m in re.finditer(r"(\d{4,6})\s*BRL", text, re.I):
        try: vals.append(int(m.group(1)))
        except: pass
    # USD fallback ~5x (apenas indicativo)
    for m in re.finditer(r"\$\s*([\d\.\,]+)", text):
        try:
            raw = m.group(1).replace(".", "").replace(",", ".")
            v = float(raw)
            if v > 500:  # evitar $5
                vals.append(int(v*5))
        except: pass
    return max(vals) if vals else 0

def detect_level(title: str, desc: str) -> str:
    t = (title + " " + desc).lower()
    if any(k in t for k in ["estágio", "estagio", "intern", "trainee"]):
        return "estagio"
    if any(k in t for k in ["junior", "jr ", "jr.", "júnior"]):
        return "junior"
    if any(k in t for k in ["pleno", "mid-level", "mid level", "mid senior"]):
        return "pleno"
    if any(k in t for k in ["senior", "sênior", "sr ", "sr.", "staff", "principal", "lead", "tech lead"]):
        return "senior"
    return "nao_especificado"

def is_pcd(text: str) -> bool:
    if not text: return False
    t=text.lower()
    return any(k in t for k in ["pcd","pessoa com deficiência","vaga afirmativa","exclusiva pcd"])

def requires_english(text: str) -> bool:
    if not text: return False
    t=text.lower()
    return any(k in t for k in ["inglês avançado","ingles avançado","english fluent","inglês fluente","english advanced","inglês intermediário"])

def parse_published_days(job: Dict) -> int | None:
    """Tenta extrair idade da vaga em dias (se tiver campo). Retorna None se não disponível."""
    for key in ["publication_date","published_at","created_at","date_posted"]:
        v = job.get(key)
        if v:
            try:
                # Remotive: 2024-08-26T...
                dt = datetime.fromisoformat(v.replace("Z","+00:00"))
                # naive compare
                delta = datetime.now(dt.tzinfo) - dt
                return delta.days
            except: pass
    txt = (job.get("description","") + " " + job.get("title","")).lower()
    # "há 2 dias", "2 days ago"
    m = re.search(r"há\s*(\d+)\s*dias?", txt)
    if m: return int(m.group(1))
    m = re.search(r"(\d+)\s*days?\s*ago", txt)
    if m: return int(m.group(1))
    return None

def matches_filters(job: Dict, cfg: Dict) -> tuple[bool, str]:
    """
    cfg keys: min_salary, level, exclude_keywords[], max_age_days, only_pcd, english_filter (indiferente/sim/nao), blocked_companies[], mandatory_words[], max_distance_km (não usado estritamente, filtra por cidade se >0)
    Retorna (passou, motivo_rejeição)
    """
    title = job.get("title","") or ""
    company = job.get("company","") or ""
    desc = job.get("description","") or ""
    combined = f"{title} {desc}".lower()
    company_l = company.lower()

    # 1. Excluir palavras-chave
    for kw in cfg.get("exclude_keywords", []):
        if kw.lower() in combined or kw.lower() in title.lower():
            return False, f"excluir_keyword:{kw}"

    # 2. Obrigatórias (pelo menos uma)
    mand = [w for w in cfg.get("mandatory_words",[]) if w.strip()]
    if mand and not any(w.lower() in combined for w in mand):
        return False, "sem_palavra_obrigatoria"

    # 3. Empresas bloqueadas
    for b in cfg.get("blocked_companies",[]):
        if b.lower() in company_l:
            return False, f"empresa_bloqueada:{b}"

    # 4. Favoritas não bloqueia, apenas para relatório - ignorado aqui

    # 5. Salário mínimo
    min_sal = int(cfg.get("min_salary",0) or 0)
    if min_sal > 0:
        sal = parse_salary(desc + " " + title)
        if sal and sal < min_sal:
            return False, f"salario_baixo:{sal}<{min_sal}"
        # se não encontrou salário, não rejeita (mantém vaga)

    # 6. Nível
    level_cfg = cfg.get("level","indiferente")
    if level_cfg and level_cfg != "indiferente":
        lvl = detect_level(title, desc)
        # mapear junior/pleno/senior: se cfg pede 'senior' mas vaga é junior, rejeita
        # simplificado: nível deve conter substring
        if level_cfg.lower() not in lvl and lvl != "nao_especificado":
            # permitir senior quando pede pleno? não - ser estrito
            # mas se vaga nao especificado, passa
            return False, f"nivel_incompativel:{lvl}!={level_cfg}"

    # 7. Apenas PCD
    if cfg.get("only_pcd"):
        if not is_pcd(desc):
            return False, "nao_e_pcd"

    # 8. Inglês
    eng = cfg.get("english_filter","indiferente")
    if eng == "sim" and not requires_english(desc):
        return False, "nao_exige_ingles"
    if eng == "nao" and requires_english(desc):
        return False, "exige_ingles"

    # 9. Idade da vaga
    max_age = int(cfg.get("max_age_days",0) or 0)
    if max_age > 0:
        age = parse_published_days(job)
        if age is not None and age > max_age:
            return False, f"vaga_antiga:{age}d>{max_age}d"

    # 10. Distância km - simplificado: se presencial e cidade não bate, rejeita
    # cfg[max_distance_km] >0 e presencial_location definido -> exige que location contenha cidade
    # Implementação aproximada (sem geocoding)
    # Deixar para gui validar

    return True, "ok"

def filter_jobs(jobs: List[Dict], cfg: Dict) -> List[Dict]:
    out=[]
    for j in jobs:
        ok, reason = matches_filters(j, cfg)
        j["_filter_reason"] = reason
        if ok:
            out.append(j)
    return out
