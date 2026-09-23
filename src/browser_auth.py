"""Login via navegador real, sem guardar email/senha no app.

Abre um Chromium de verdade (o mesmo bundlado no .exe) na página de login do site; o
usuário loga do jeito que quiser (senha, Google, 2FA) e o app nunca vê a credencial —
só salva a SESSÃO (cookies) via Playwright `storage_state` quando detecta que saiu da
URL de login. Buscas/candidaturas seguintes reusam essa sessão sem pedir login de novo;
se expirar, `session_expired` detecta e avisa sem travar a automação.

A sessão em disco é criptografada com o DPAPI do Windows (chave amarrada à conta do
Windows que logou — não decifra em outra máquina/usuário sem a senha do Windows).
Fora do Windows não há equivalente sem uma dependência extra de keyring do sistema;
a sessão fica sem criptografia nesse caso (sem regressão — nunca teve proteção antes).
"""
import json
import sys
from pathlib import Path
from config import BASE_DIR


def _is_windows() -> bool:
    return sys.platform == "win32"


def _dpapi_protect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [ctypes.POINTER(DATA_BLOB), wintypes.LPCWSTR, ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    crypt32.CryptProtectData.restype = wintypes.BOOL

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptProtectData(ctypes.byref(blob_in), "VampHunter session", None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _dpapi_unprotect(data: bytes) -> bytes:
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptUnprotectData.argtypes = [ctypes.POINTER(DATA_BLOB), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(DATA_BLOB), ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DATA_BLOB)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf, ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    if not crypt32.CryptUnprotectData(ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        kernel32.LocalFree(blob_out.pbData)


def _encrypt_bytes(data: bytes) -> bytes:
    if not _is_windows():
        return data
    return _dpapi_protect(data)


def _decrypt_bytes(data: bytes) -> bytes:
    if not _is_windows():
        return data
    return _dpapi_unprotect(data)

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
                state = ctx.storage_state()
                raw = json.dumps(state).encode("utf-8")
                session_path(service).write_bytes(_encrypt_bytes(raw))
                print(f"[BrowserAuth] Login em {SERVICE_LABELS.get(service, service)} detectado e sessão salva com sucesso"
                      + (" (criptografada com a conta do Windows)." if _is_windows() else "."))
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
            raw = _decrypt_bytes(sp.read_bytes())
            state = json.loads(raw)
            return browser.new_context(storage_state=state)
        except Exception as e:
            print(f"[BrowserAuth] Sessão salva de {service} não pôde ser lida (corrompida, de uma versão antiga sem criptografia, ou de outra conta do Windows) — faça login novamente na aba 'IA & Conexões'. Detalhe: {e}")
    return browser.new_context()
