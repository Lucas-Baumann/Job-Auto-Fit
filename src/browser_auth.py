"""Login via navegador real, sem guardar email/senha no app.

Em vez de pedir email+senha e salvar isso no .env (mesmo com boa proteção, é uma
credencial real de login guardada por um app de terceiro), abre um Chromium de
verdade (o mesmo bundlado no .exe, ver JobAutoFit.spec) direto na página de login
do site. O usuário loga do jeito que quiser — senha, "Continuar com Google", 2FA —
e o app nunca vê nada disso: só salva a SESSÃO (cookies) localmente via
Playwright `storage_state`, depois que detecta que o login deu certo (saiu da
URL de login). Buscas/candidaturas seguintes reusam essa sessão carregando o
storage_state num contexto novo, sem pedir login de novo — e se a sessão expirar,
o app detecta e avisa (ver `session_expired`), sem travar a automação.

Mecanismo validado empiricamente antes de implementar: salvar storage_state de um
contexto e carregar num contexto novo preserva os cookies sem precisar logar de
novo (testado com o próprio Playwright/Chromium bundlado no projeto).
"""
from pathlib import Path
from config import BASE_DIR

LOGIN_URLS = {
    "linkedin": "https://www.linkedin.com/login",
    # login único de candidato, funciona pra qualquer empresa que usa Gupy —
    # confirmado navegando o portal.gupy.io real (botão "Entrar" aponta pra cá)
    "gupy": "https://login.gupy.io/candidates/signin",
}

SERVICE_LABELS = {"linkedin": "LinkedIn", "gupy": "Gupy"}


def session_path(service: str) -> Path:
    return BASE_DIR / f"{service}_session.json"


def has_session(service: str) -> bool:
    return session_path(service).exists()


def clear_session(service: str):
    try:
        session_path(service).unlink(missing_ok=True)
    except Exception:
        pass


def _is_login_url(service: str, url: str) -> bool:
    """Detecta se uma URL ainda é a tela de login (login pendente ou sessão expirada)."""
    u = (url or "").lower()
    if service == "linkedin":
        return "/login" in u or "/checkpoint" in u or "authwall" in u or "/uas/" in u
    if service == "gupy":
        return "signin" in u or "sign-in" in u or "/login" in u
    return "login" in u


def session_expired(service: str, current_url: str) -> bool:
    """Chame depois de navegar com um contexto que carregou storage_state salvo: se a URL
    caiu de volta na tela de login, a sessão salva não é mais válida."""
    return _is_login_url(service, current_url)


def login_via_browser(service: str, timeout_seconds: int = 300) -> bool:
    """Abre um Chromium visível na página de login do serviço e espera o usuário logar
    manualmente. Detecta sucesso quando a URL sai da tela de login, salva a sessão em
    disco e retorna True. Retorna False se fechar a janela ou estourar o tempo limite
    sem detectar login (nesse caso nada é salvo)."""
    login_url = LOGIN_URLS.get(service)
    if not login_url:
        print(f"[BrowserAuth] Serviço '{service}' não suportado.")
        return False
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[BrowserAuth] Playwright não está disponível nesta instalação — login via navegador não roda.")
        return False

    success = False
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
            ctx = browser.new_context(locale="pt-BR")
            page = ctx.new_page()
            page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            elapsed = 0
            step = 1000
            while elapsed < timeout_seconds * 1000:
                try:
                    if page.is_closed():
                        break
                    if not _is_login_url(service, page.url):
                        success = True
                        break
                except Exception:
                    break
                page.wait_for_timeout(step)
                elapsed += step
            if success:
                ctx.storage_state(path=str(session_path(service)))
                print(f"[BrowserAuth] Login em {SERVICE_LABELS.get(service, service)} detectado e sessão salva com sucesso.")
            else:
                print(f"[BrowserAuth] Login em {SERVICE_LABELS.get(service, service)} não foi concluído (janela fechada ou tempo esgotado) — nada foi salvo.")
            try:
                browser.close()
            except Exception:
                pass
    except Exception as e:
        print(f"[BrowserAuth] Erro no login via navegador ({service}): {e}")
    return success


def new_context(browser, service: str):
    """Cria um contexto do navegador já autenticado, se houver sessão salva pra esse
    serviço; senão, um contexto anônimo normal (comportamento de sempre)."""
    sp = session_path(service)
    if sp.exists():
        try:
            return browser.new_context(storage_state=str(sp))
        except Exception as e:
            print(f"[BrowserAuth] Sessão salva de {service} corrompida/inválida ({e}) — abrindo sem login.")
    return browser.new_context()
