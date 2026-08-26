import re
import time
import os
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

# --- LinkedIn Posts: sinais de recrutador e de contratação ---
RECRUITER_SIGNALS = [
    "recruiter", "talent acquisition", "talent", "rh", "recursos humanos",
    "people", "hiring", "r&s", "recrutamento", "recrutadora", "recrutador",
    "human resources", "headhunter", "staffing", "hunter"
]

HIRING_KEYWORDS = [
    "vaga", "vagas", "oportunidade", "oportunidades", "contratando",
    "contrata-se", "estamos contratando", "envie seu cv", "envie seu currículo",
    "aplique", "candidatura", "processo seletivo", "hiring", "we're hiring",
    "job opening", "job opportunity", "apply now", "#vaga", "#vagas", "#hiring", "#oportunidade"
]

def extract_email(text: str) -> str:
    """Extrai e-mail de contato do texto da vaga se existente."""
    if not text:
        return ""
    email_regex = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(email_regex, text)
    # Filtra e-mails comuns irrelevantes (ex: exemplo@..., noreply@...)
    filtered = [e for e in matches if not any(x in e.lower() for x in ['example.com', 'noreply', 'domain.com', 'schema.org'])]
    return filtered[0] if filtered else ""

def fetch_gupy_jobs(keywords: str, limit: int = 15) -> List[Dict]:
    """Coleta vagas públicas da plataforma Gupy via API de Busca."""
    jobs = []
    url = f"https://portal.api.gupy.io/api/v1/jobs?jobName={requests.utils.quote(keywords)}&limit={limit}&offset=0"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('data', [])
            for item in results:
                job_url = item.get('jobUrl') or f"https://vagas.gupy.io/job/{item.get('id')}"
                description = item.get('description', '') or item.get('summary', '')
                
                # Buscar detalhes adicionais se descrição for curta
                if not description or len(description) < 100:
                    description = f"Vaga: {item.get('name')}. Tipo: {item.get('type')}. Cidade: {item.get('city')}, {item.get('state')}."
                
                jobs.append({
                    'title': item.get('name', 'Sem título'),
                    'company': item.get('careerPageName', 'Empresa Gupy'),
                    'location': f"{item.get('city', '')}, {item.get('state', '')}".strip(", "),
                    'url': job_url,
                    'platform': 'gupy',
                    'description': description,
                    'contact_email': extract_email(description)
                })
    except Exception as e:
        print(f"[Collector] Erro ao buscar vagas na Gupy: {e}")
    
    return jobs

def fetch_linkedin_jobs(keywords: str, location: str = "Brasil", limit: int = 15) -> List[Dict]:
    """Coleta vagas públicas do LinkedIn sem necessidade de login."""
    jobs = []
    base_url = f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?keywords={requests.utils.quote(keywords)}&location={requests.utils.quote(location)}&start=0"
    
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            job_cards = soup.find_all('li')
            
            for card in job_cards[:limit]:
                title_elem = card.find('h3', class_='base-search-card__title')
                company_elem = card.find('h4', class_='base-search-card__subtitle')
                location_elem = card.find('span', class_='job-search-card__location')
                link_elem = card.find('a', class_='base-card__full-link')
                
                if title_elem and link_elem:
                    job_title = title_elem.text.strip()
                    company = company_elem.text.strip() if company_elem else "LinkedIn Company"
                    loc = location_elem.text.strip() if location_elem else location
                    job_url = link_elem.get('href', '').split('?')[0]
                    
                    # Obter descrição detalhada da vaga individual
                    desc = fetch_linkedin_job_details(job_url)
                    
                    jobs.append({
                        'title': job_title,
                        'company': company,
                        'location': loc,
                        'url': job_url,
                        'platform': 'linkedin',
                        'description': desc or f"Vaga de {job_title} na empresa {company}.",
                        'contact_email': extract_email(desc)
                    })
                    time.sleep(1) # Pausa amigável
    except Exception as e:
        print(f"[Collector] Erro ao buscar vagas no LinkedIn: {e}")
        
    return jobs

def fetch_linkedin_job_details(job_url: str) -> str:
    """Busca o texto completo da descrição de uma vaga do LinkedIn."""
    try:
        response = requests.get(job_url, headers=HEADERS, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            desc_div = soup.find('div', class_='show-more-less-html__markup')
            if desc_div:
                return desc_div.text.strip()
    except Exception:
        pass
    return ""

def fetch_remotive_jobs(keywords: str, limit: int = 10) -> List[Dict]:
    """Coleta vagas remotas da API pública e gratuita da Remotive."""
    jobs = []
    url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(keywords)}"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = data.get('jobs', [])
            for item in results[:limit]:
                desc_raw = item.get('description', '')
                soup = BeautifulSoup(desc_raw, 'html.parser')
                clean_desc = soup.get_text(separator=' ')
                
                jobs.append({
                    'title': item.get('title'),
                    'company': item.get('company_name'),
                    'location': item.get('candidate_required_location', 'Remoto'),
                    'url': item.get('url'),
                    'platform': 'remotive',
                    'description': clean_desc,
                    'contact_email': extract_email(clean_desc)
                })
    except Exception as e:
        print(f"[Collector] Erro ao buscar vagas no Remotive: {e}")
        
    return jobs

# ── Helpers para posts de recrutadores ──
def _is_recruiter_text(text: str) -> bool:
    if not text: return False
    t = text.lower()
    return any(sig in t for sig in RECRUITER_SIGNALS)

def _has_hiring_keyword(text: str) -> bool:
    if not text: return False
    t = text.lower()
    return any(kw in t for kw in HIRING_KEYWORDS)

def _extract_title_from_post(post_text: str, keywords: str) -> str:
    if not post_text: return f"Vaga {keywords} (Post LinkedIn)"
    # primeira linha não vazia como título, limitada a 90 chars
    first_line = next((l.strip() for l in post_text.splitlines() if l.strip()), "")
    if len(first_line) > 90:
        first_line = first_line[:87] + "..."
    # se não parecer vaga, prefixa com keywords
    if not _has_hiring_keyword(first_line):
        return f"{keywords} - {first_line[:60]}" if first_line else f"Vaga {keywords} (Post LinkedIn)"
    return first_line or f"Vaga {keywords} (Post LinkedIn)"

def _extract_company_from_post(post_text: str, author: str) -> str:
    # tenta "Empresa X contratando" no texto
    m = re.search(r"@\s*([\w\s&\-]+?)\s*(?:está|esta|contratando|oportunidade|vaga)", post_text, re.I)
    if m:
        return m.group(1).strip()[:60]
    if author:
        return f"Post LinkedIn - {author[:40]}"
    return "Post LinkedIn"

def fetch_linkedin_post_details(post_url: str) -> str:
    """Busca texto completo de um post individual do LinkedIn (guest)."""
    try:
        resp = requests.get(post_url, headers=HEADERS, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # posts geralmente em divs com data-urn ou article
            candidates = []
            for sel in ["div.feed-shared-update-v2__description", "div.update-components-text", "article", "div.show-more-less-html__markup", "span.break-words"]:
                for el in soup.select(sel):
                    txt = el.get_text(separator=' ', strip=True)
                    if len(txt) > 80:
                        candidates.append(txt)
            if candidates:
                # pega o maior bloco
                return max(candidates, key=len)
            # fallback: todo texto visível
            text = soup.get_text(separator=' ', strip=True)
            if len(text) > 120:
                return text[:4000]
    except Exception:
        pass
    return ""

def _fetch_linkedin_posts_guest(keywords: str, limit: int = 10) -> List[Dict]:
    """Scraping guest da busca de conteúdo do LinkedIn (sem login)."""
    jobs: List[Dict] = []
    # amplia keywords com termo de contratação para melhorar precisão
    expanded = f"{keywords} vaga contratando hiring"
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={requests.utils.quote(expanded)}&origin=GLOBAL_SEARCH_HEADER&sid=jobautofit"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=12)
        if resp.status_code in (999, 429):
            print(f"[Collector][Posts] LinkedIn rate-limit ({resp.status_code}) — tente com login/Playwright ou aguarde.")
            return jobs
        if resp.status_code == 999:
            return jobs
        if resp.status_code != 200:
            print(f"[Collector][Posts] Busca guest retornou {resp.status_code}")
            return jobs

        soup = BeautifulSoup(resp.text, 'html.parser')
        # LinkedIn guest frequentemente redireciona para authwall — detectar
        if "authwall" in resp.text.lower() or "login" in soup.title.text.lower() if soup.title else False:
            # ainda tenta extrair links visíveis
            pass

        # Coleta links de posts: /posts/, /feed/update/, /pulse/
        post_links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if any(pat in href for pat in ["/posts/", "/feed/update/", "/pulse/"]):
                # normaliza linkedin.com URL
                if href.startswith("/"):
                    href = "https://www.linkedin.com" + href
                href = href.split("?")[0]
                if href not in post_links:
                    post_links.append(href)
            if len(post_links) >= limit * 2:
                break

        # Também busca blocos de texto próximos aos links para inferir autoria
        for url in post_links[:limit*2]:
            if len(jobs) >= limit:
                break
            text = fetch_linkedin_post_details(url)
            if not text or len(text) < 60:
                continue
            if not _has_hiring_keyword(text):
                continue
            # infere autor do URL ou do texto
            author = ""
            # tenta extrair autor do HTML do post já buscado
            try:
                r2 = requests.get(url, headers=HEADERS, timeout=8)
                s2 = BeautifulSoup(r2.text, 'html.parser')
                author_el = s2.find('a', class_=re.compile(r'update-components-actor__title|feed-shared-actor__name'))
                if author_el:
                    author = author_el.get_text(strip=True)
                title_el = s2.find('span', class_=re.compile(r'update-components-actor__description'))
                author_title = title_el.get_text(strip=True) if title_el else ""
            except Exception:
                author_title = ""

            # filtro recrutador: se temos título do autor e não é recrutador, ainda aceita mas marca
            is_recruiter = _is_recruiter_text(author_title) or _is_recruiter_text(text[:500])
            # para não perder vagas, aceita mesmo não-recrutador se tiver hiring keyword forte
            # mas prioriza recrutadores
            if not is_recruiter and not any(kw in text.lower() for kw in ["vaga", "oportunidade", "hiring", "contratando"]):
                continue

            jobs.append({
                'title': _extract_title_from_post(text, keywords),
                'company': _extract_company_from_post(text, author),
                'location': "Brasil",
                'url': url,
                'platform': 'linkedin_post',
                'description': text[:4000],
                'contact_email': extract_email(text),
                'author': author,
                'author_title': author_title
            })
            time.sleep(1.2)

        # fallback: se não achou links, tenta extrair blocos de post diretamente da página de busca
        if not jobs:
            # procura por blocos com texto longo de post na própria busca
            candidates = []
            for div in soup.find_all('div'):
                txt = div.get_text(separator=' ', strip=True)
                if 120 < len(txt) < 3000 and _has_hiring_keyword(txt):
                    candidates.append(txt)
            for txt in candidates[:limit]:
                if len(jobs) >= limit: break
                jobs.append({
                    'title': _extract_title_from_post(txt, keywords),
                    'company': _extract_company_from_post(txt, ""),
                    'location': "Brasil",
                    'url': search_url,
                    'platform': 'linkedin_post',
                    'description': txt[:4000],
                    'contact_email': extract_email(txt)
                })

    except Exception as e:
        print(f"[Collector][Posts] Erro no scraping guest: {e}")
    return jobs[:limit]

def _fetch_linkedin_posts_via_playwright(keywords: str, limit: int = 10) -> List[Dict]:
    """Scraping via Playwright com login (se credenciais disponíveis)."""
    jobs: List[Dict] = []
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return jobs

    linkedin_email = os.getenv("LINKEDIN_EMAIL", "")
    linkedin_pass = os.getenv("LINKEDIN_PASSWORD", "")
    # também verifica .env via config se disponível
    if not linkedin_email:
        try:
            from config import Config
            linkedin_email = Config.LINKEDIN_EMAIL
            linkedin_pass = Config.LINKEDIN_PASSWORD
        except: pass

    if not linkedin_email or not linkedin_pass:
        return jobs

    expanded = f"{keywords} vaga contratando"
    search_url = f"https://www.linkedin.com/search/results/content/?keywords={requests.utils.quote(expanded)}&origin=GLOBAL_SEARCH_HEADER"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(user_agent=HEADERS['User-Agent'], locale="pt-BR")
            page = ctx.new_page()
            print("[Collector][Posts] Playwright: fazendo login no LinkedIn...")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=30000)
            page.fill('input[name="session_key"]', linkedin_email)
            page.fill('input[name="session_password"]', linkedin_pass)
            page.click('button[type="submit"]')
            page.wait_for_timeout(4000)
            # se ainda em login (captcha/2FA), dá tempo para usuário resolver
            if "checkpoint" in page.url or "challenge" in page.url:
                print("[Collector][Posts] Checkpoint/CAPTCHA detectado — aguarde 30s para resolver manualmente...")
                page.wait_for_timeout(30000)
            page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            # scroll para carregar posts
            for _ in range(3):
                page.mouse.wheel(0, 2000)
                page.wait_for_timeout(2000)

            # extrai posts visíveis
            posts = page.query_selector_all('div.feed-shared-update-v2, div.search-result__wrapper, div.entity-result')
            for post in posts[:limit*2]:
                if len(jobs) >= limit: break
                try:
                    text_el = post.query_selector('div.feed-shared-update-v2__description, span.break-words, div.update-components-text')
                    text = text_el.inner_text() if text_el else post.inner_text()
                    if not text or len(text) < 60 or not _has_hiring_keyword(text):
                        continue
                    author_el = post.query_selector('span.feed-shared-actor__name, a.update-components-actor__title')
                    author = author_el.inner_text().strip() if author_el else ""
                    author_title_el = post.query_selector('span.update-components-actor__description')
                    author_title = author_title_el.inner_text().strip() if author_title_el else ""

                    link_el = post.query_selector('a[href*="/posts/"], a[href*="/feed/update/"]')
                    url = link_el.get_attribute('href') if link_el else search_url
                    if url and url.startswith("/"): url = "https://www.linkedin.com" + url
                    if url: url = url.split("?")[0]

                    jobs.append({
                        'title': _extract_title_from_post(text, keywords),
                        'company': _extract_company_from_post(text, author),
                        'location': "Brasil",
                        'url': url or search_url,
                        'platform': 'linkedin_post',
                        'description': text[:4000],
                        'contact_email': extract_email(text),
                        'author': author,
                        'author_title': author_title
                    })
                except Exception:
                    continue
            browser.close()
    except Exception as e:
        print(f"[Collector][Posts] Playwright erro: {e}")
    return jobs[:limit]

def fetch_linkedin_recruiter_posts(keywords: str, limit: int = 10) -> List[Dict]:
    """
    Coleta vagas divulgadas em posts de recrutadores no LinkedIn.
    - Tenta Playwright autenticado se LINKEDIN_EMAIL/PASSWORD disponíveis
    - Senão cai para scraping guest (mais frágil, mas gratuito)
    - Filtra por sinais de recrutador + keywords de contratação
    - Expande keywords automaticamente: 'python developer' -> 'python developer vaga contratando hiring'
    """
    print(f"[Collector][Posts] Buscando posts de recrutadores para '{keywords}'...")
    # 1. tenta Playwright se tiver credenciais
    jobs = _fetch_linkedin_posts_via_playwright(keywords, limit=limit)
    if jobs:
        print(f"[Collector][Posts] Playwright encontrou {len(jobs)} posts")
        return jobs
    # 2. fallback guest
    jobs = _fetch_linkedin_posts_guest(keywords, limit=limit)
    print(f"[Collector][Posts] Guest encontrou {len(jobs)} posts")
    return jobs

def collect_all_jobs(keywords_list: List[str], location: str = "Brasil", limit_per_source: int = 10, enable_linkedin_posts: bool = True, linkedin_posts_limit: int = None) -> List[Dict]:
    """Orquestra a coleta em múltiplas fontes gratuitas."""
    all_jobs = []
    if linkedin_posts_limit is None:
        linkedin_posts_limit = limit_per_source
    
    for kw in keywords_list:
        print(f"[Collector] Buscando vagas para '{kw}'...")
        
        # 1. Gupy
        gupy_jobs = fetch_gupy_jobs(kw, limit=limit_per_source)
        all_jobs.extend(gupy_jobs)
        
        # 2. LinkedIn
        linkedin_jobs = fetch_linkedin_jobs(kw, location=location, limit=limit_per_source)
        all_jobs.extend(linkedin_jobs)
        
        # 3. Remotive
        remotive_jobs = fetch_remotive_jobs(kw, limit=limit_per_source)
        all_jobs.extend(remotive_jobs)

        # 4. LinkedIn Posts de recrutadores (nova fonte)
        if enable_linkedin_posts:
            try:
                posts_jobs = fetch_linkedin_recruiter_posts(kw, limit=linkedin_posts_limit)
                all_jobs.extend(posts_jobs)
            except Exception as e:
                print(f"[Collector][Posts] Erro geral: {e}")
            # pausa extra para evitar rate-limit no LinkedIn
            time.sleep(2)
        
    print(f"[Collector] Total de vagas coletadas (bruto): {len(all_jobs)}")
    return all_jobs