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

def requires_us_location(text: str) -> bool:
    """Detecta vagas do LinkedIn/exterior que exigem estar nos EUA (autorização de trabalho,
    cidadania, ou 'apenas candidatos dos EUA') — inaplicável pra quem mora no Brasil, mas
    aparecia no relatório porque buscas em inglês (ex: 'Desenvolvedor Python' -> 'Python
    Developer') trazem vagas americanas junto com as brasileiras."""
    if not text: return False
    t = text.lower()
    return any(re.search(p, t) for p in [
        r"authorized to work in the united states",
        r"must be (?:currently )?located in the united states",
        r"u\.?s\.?\s*applicants only",
        r"united states only",
        r"must be a u\.?s\.?\s*citizen",
        r"require[sd]? u\.?s\.?\s*citizenship",
    ])

# Códigos de 2 letras dos EUA que NÃO colidem com sigla de estado brasileiro (ex: "PA" é
# Pensilvânia nos EUA E Pará no Brasil — ambíguo demais, melhor não usar sigla sozinha nesses
# casos e confiar só no nome completo/menção ao país). Evita rejeitar vaga brasileira de
# Alagoas/Maranhão/Mato Grosso/Mato Grosso do Sul/Pará/Santa Catarina por engano.
_US_STATE_CODES_UNAMBIGUOUS = {
    "AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
    "ME","MD","MI","MN","MO","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","RI",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
}
_US_STATE_NAMES = [
    "alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
    "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
    "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
    "missouri","montana","nebraska","nevada","new hampshire","new jersey","new mexico",
    "new york","north carolina","north dakota","ohio","oklahoma","oregon","pennsylvania",
    "rhode island","south carolina","south dakota","tennessee","texas","utah","vermont",
    "virginia","washington","west virginia","wisconsin","wyoming",
]

# Cidades dos EUA nos estados "ambíguos" acima (AL/MA/MT/MS/PA/SC), pra quando o LinkedIn
# manda location sem sigla de estado nem nome do país — ex: "Mobile" ou "Mobile Metropolitan
# Area" (Mobile, Alabama) passava direto pelo filtro porque AL foi deliberadamente excluído
# de _US_STATE_CODES_UNAMBIGUOUS. Checado SÓ no campo location (nunca junto com o título),
# pra não confundir com título de vaga brasileira tipo "Desenvolvedor Mobile" (sobre
# desenvolvimento mobile, nada a ver com a cidade dos EUA).
_US_AMBIGUOUS_STATE_CITIES = [
    "mobile", "birmingham", "huntsville", "tuscaloosa", "hoover",  # Alabama
    "boston", "cambridge", "worcester", "lowell", "quincy",  # Massachusetts
    "billings", "missoula", "bozeman", "great falls", "helena",  # Montana
    "gulfport", "biloxi", "hattiesburg", "southaven",  # Mississippi
    "philadelphia", "pittsburgh", "allentown", "erie",  # Pennsylvania
    "charleston", "spartanburg", "myrtle beach",  # South Carolina
]

def is_foreign_job_location(location: str, title: str = "") -> bool:
    """Detecta vaga situada no exterior (hoje, na prática, quase sempre EUA vindo do LinkedIn)
    pelo campo location/título — diferente de requires_us_location() (que olha o texto da
    descrição): aqui pega vaga cuja localização já é claramente estrangeira mesmo quando a
    descrição não usa nenhuma das frases-padrão de "só EUA". NÃO barra vaga remota brasileira
    que aceita candidato no exterior — só barra quando a VAGA em si está localizada lá fora."""
    combined = f"{location} {title}".lower()
    if not combined.strip():
        return False
    if any(k in combined for k in ["estados unidos", "united states", " usa", "u.s.a"]):
        return True
    if any(name in combined for name in _US_STATE_NAMES):
        return True
    # padrão "Cidade, XX" (ou "Cidade, XX/", como em títulos com duas localizações)
    for code in re.findall(r",\s*([A-Za-z]{2})\b", location + " " + title):
        if code.upper() in _US_STATE_CODES_UNAMBIGUOUS:
            return True
    loc_l = (location or "").lower()
    if any(re.search(r"\b" + re.escape(city) + r"\b", loc_l) for city in _US_AMBIGUOUS_STATE_CITIES):
        return True
    return False

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
    # "Publicada em 25/08" ou "25/08/2026" (Catho/InfoJobs/Vagas.com mostram data absoluta,
    # não relativa — sem isso a vaga passava despercebida pelo filtro de idade máxima)
    m = re.search(r"public(?:ada|ado)\s+em\s+(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?", txt)
    if m:
        day, month, year = m.groups()
        try:
            day, month = int(day), int(month)
            year = int(year) if year else datetime.now().year
            if year < 100:
                year += 2000
            pub_date = datetime(year, month, day)
            if pub_date > datetime.now():
                pub_date = pub_date.replace(year=year - 1)
            return (datetime.now() - pub_date).days
        except ValueError:
            pass
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

    # 8.5. Vaga exige localização/autorização nos EUA (comum em vagas do LinkedIn em inglês
    # que "vazam" pra buscas genéricas tipo "Python Developer" — inaplicável no Brasil)
    if requires_us_location(desc):
        return False, "exige_localizacao_eua"

    # 8.6. Vaga está fisicamente no exterior (campo location/título), mesmo quando a descrição
    # não usa nenhuma frase-padrão de "só EUA" — ex: "Reston, Virginia" ou "Tampa, FL" direto
    # no location, sem "authorized to work..." em lugar nenhum do texto.
    if is_foreign_job_location(job.get("location",""), title):
        return False, "vaga_no_exterior"

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
