import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7'
}

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

def collect_all_jobs(keywords_list: List[str], location: str = "Brasil", limit_per_source: int = 10) -> List[Dict]:
    """Orquestra a coleta em múltiplas fontes gratuitas."""
    all_jobs = []
    
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
        
    print(f"[Collector] Total de vagas coletadas (bruto): {len(all_jobs)}")
    return all_jobs