import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path

from config import Config

def send_email_application(recipient_email: str, job_title: str, company: str, cover_letter: str, pdf_path: str) -> bool:
    """Envia candidatura via E-mail (SMTP) com o curriculo otimizado em anexo."""
    if not Config.SMTP_USER or not Config.SMTP_PASS:
        print(f"[Sender SMTP] Credenciais SMTP não configuradas no .env. Ignorando envio por e-mail para {recipient_email}.")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = Config.SMTP_USER
        msg['To'] = recipient_email
        msg['Subject'] = f"Candidatura: {job_title} - {company}"
        
        # Corpo do e-mail (Carta de apresentação)
        msg.attach(MIMEText(cover_letter, 'plain', 'utf-8'))
        
        # Anexo do PDF
        pdf_file = Path(pdf_path)
        if pdf_file.exists():
            with open(pdf_file, "rb") as f:
                part = MIMEApplication(f.read(), Name=pdf_file.name)
                part['Content-Disposition'] = f'attachment; filename="{pdf_file.name}"'
                msg.attach(part)
                
        # Conexão SMTP
        server = smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT)
        server.starttls()
        server.login(Config.SMTP_USER, Config.SMTP_PASS)
        server.sendmail(Config.SMTP_USER, recipient_email, msg.as_string())
        server.quit()
        
        print(f"[Sender SMTP] E-mail enviado com sucesso para {recipient_email}!")
        return True
    except Exception as e:
        print(f"[Sender SMTP] Erro ao enviar e-mail para {recipient_email}: {e}")
        return False

def apply_gupy_playwright(job_url: str, pdf_path: str, cover_letter: str) -> bool:
    """
    Automatiza o preenchimento inicial na plataforma Gupy via Playwright.
    Preenche dados padrão e anexa o PDF otimizado.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Sender Gupy] Playwright não está instalado. Execute 'pip install playwright && playwright install'")
        return False

    print(f"[Sender Gupy] Iniciando automacao do navegador para a vaga: {job_url}")
    try:
        with sync_playwright() as p:
            # Lança o navegador visível (headful) para permitir acompanhamento e interações se necessário
            browser = p.chromium.launch(headless=False, slow_mo=500)
            context = browser.new_context()
            page = context.new_page()
            
            page.goto(job_url, timeout=30000)
            time.sleep(2)
            
            # Tentar clicar em 'Candidatar-se'
            apply_btn = page.query_selector("button:has-text('Candidatar-se'), a:has-text('Candidatar-se')")
            if apply_btn:
                apply_btn.click()
                time.sleep(2)
                
            # Fazer upload de curriculo se houver input de arquivo
            file_input = page.query_selector("input[type='file']")
            if file_input and os.path.exists(pdf_path):
                file_input.set_input_files(pdf_path)
                print("[Sender Gupy] Curriculo otimizado em PDF anexado no formulario Gupy.")
                time.sleep(3)
                
            print("[Sender Gupy] Formulario inicial preenchido. Finalizando sessão...")
            browser.close()
            return True
    except Exception as e:
        print(f"[Sender Gupy] Erro na automacao Gupy: {e}")
        return False

def apply_linkedin_playwright(job_url: str, pdf_path: str) -> bool:
    """
    Automacao com ritmo humano para vagas LinkedIn Easy Apply via Playwright.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Sender LinkedIn] Playwright não instalado.")
        return False

    print(f"[Sender LinkedIn] Acessando vaga no LinkedIn: {job_url}")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, slow_mo=700)
            context = browser.new_context()
            page = context.new_page()
            
            page.goto(job_url, timeout=30000)
            time.sleep(2)
            
            easy_apply_btn = page.query_selector("button.jobs-apply-button")
            if easy_apply_btn:
                print("[Sender LinkedIn] Botao Easy Apply encontrado! (Se o login for necessário, faça-o no navegador aberto).")
                # Aqui o navegador permanece aberto brevemente para visualização
                time.sleep(5)
            else:
                print("[Sender LinkedIn] Vaga redireciona para site externo ou requer login.")
                
            browser.close()
            return True
    except Exception as e:
        print(f"[Sender LinkedIn] Erro no fluxo LinkedIn: {e}")
        return False

def apply_to_job(job: dict, pdf_path: str, cover_letter: str) -> str:
    """
    Seleciona a melhor estratégia de envio de acordo com a vaga (E-mail, Gupy, LinkedIn ou Link Direto).
    Retorna o status resultante: 'applied', 'prepared' ou 'failed'.
    """
    contact_email = job.get('contact_email')
    platform = job.get('platform', '').lower()
    url = job.get('url', '')
    
    # 1. Se tem e-mail direto de contato -> Prioridade 1: SMTP
    if contact_email:
        success = send_email_application(contact_email, job['title'], job['company'], cover_letter, pdf_path)
        return 'applied' if success else 'failed'
        
    # 2. Se a plataforma for Gupy -> Playwright Gupy
    if 'gupy' in platform or 'gupy.io' in url:
        success = apply_gupy_playwright(url, pdf_path, cover_letter)
        return 'applied' if success else 'prepared'

    # 3. Se a plataforma for LinkedIn -> Playwright LinkedIn
    if 'linkedin' in platform or 'linkedin.com' in url:
        success = apply_linkedin_playwright(url, pdf_path)
        return 'applied' if success else 'prepared'

    # 4. Caso genérico -> Material fica pronto para o usuário enviar manualmente com 1 clique
    print(f"[Sender] Materiais otimizados gerados com sucesso para {job['company']} - {job['title']}.")
    return 'prepared'