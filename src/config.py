import os
import sys
import shutil
from pathlib import Path
from dotenv import load_dotenv

_project_root = Path(__file__).resolve().parent.parent

# Detecta PyInstaller via sys._MEIPASS ou sys.frozen ou caminho com _MEI
is_frozen = getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS') or "_MEI" in str(Path(__file__).resolve())
if is_frozen:
    # No .exe empacotado, o Chromium do Playwright vai bundlado dentro do próprio pacote
    # (o build em CI instala com PLAYWRIGHT_BROWSERS_PATH=0, que grava o navegador em
    # playwright/driver/package/.local-browsers em vez do cache global do usuário
    # ~/.cache/ms-playwright — cache que não existe em quem só baixou o .exe). Setado aqui
    # cedo, antes de qualquer uso do playwright, e só quando congelado: em modo dev o
    # desenvolvedor continua usando o cache global normal do 'playwright install chromium'.
    os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
    # Pasta onde o .exe foi colocado pelo usuário (Desktop, Downloads, pendrive...) — usada
    # só para localizar dados de uma instalação anterior (migração abaixo). Os dados do
    # usuário NÃO ficam mais aqui: cada pasta onde alguém soltasse o .exe criava sua própria
    # cópia de currículo/banco/logs, e uma pasta protegida (ex: Program Files) podia falhar
    # ao gravar.
    # IMPORTANTE: não dá pra comparar _legacy_dir contra "Path(__file__).resolve().parent.parent"
    # pra detectar o build local de teste (pasta dist/) — em modo congelado, __file__ aponta pra
    # dentro da pasta temporária de extração do PyInstaller (_MEIxxxxx), não pro repositório real,
    # então essa comparação nunca dá igual e a migração dispararia por engano em cima dos dados
    # reais do próprio repositório (já aconteceu uma vez durante o teste deste fix). O sinal
    # confiável é o nome da pasta do executável ("dist") checado abaixo, guardado em _is_dev_build.
    _is_dev_build = False
    try:
        exe_path = Path(sys.executable).resolve() if hasattr(sys, 'executable') else Path(__file__).resolve()
        exe_dir = exe_path.parent
        if exe_dir.name.lower() == "dist":
            # exe está em dist/ (build local de teste) -> projeto é um nível acima
            _legacy_dir = exe_dir.parent
            _is_dev_build = True
        else:
            # se exe está em Temp/_MEI, usa cwd (onde o exe foi lançado)
            if "_MEI" in str(exe_dir) or "Temp" in str(exe_dir):
                _legacy_dir = Path.cwd()
                if "_MEI" in str(_legacy_dir):
                    _legacy_dir = Path(sys.executable).resolve().parent
                    if _legacy_dir.name.lower() == "dist":
                        _legacy_dir = _legacy_dir.parent
                        _is_dev_build = True
            else:
                _legacy_dir = exe_dir
    except Exception:
        _legacy_dir = Path.cwd()

    # Dados do usuário agora ficam em %LOCALAPPDATA%\JobAutoFit, fora da pasta do .exe
    BASE_DIR = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "JobAutoFit"
    BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Migração única: versões anteriores gravavam tudo do lado do .exe. Se a pasta antiga
    # tiver dados de uma instalação real (não a pasta dist/ do build local, que é o próprio
    # repositório) e a nova ainda não, move em vez de deixar o usuário achando que perdeu
    # currículo/chaves/histórico de vagas.
    if not _is_dev_build and _legacy_dir != BASE_DIR:
        for _name in (".env", "curriculum_base.json", "jobs.db", "jobs.db-wal", "jobs.db-shm",
                      "search_config.json", "github_selection.json", "presets.json", ".wizard_done",
                      "output", "reports", "output_github", "output_github_test", "logs"):
            _src, _dst = _legacy_dir / _name, BASE_DIR / _name
            if _src.exists() and not _dst.exists():
                try:
                    shutil.move(str(_src), str(_dst))
                except Exception:
                    pass
else:
    BASE_DIR = _project_root
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)

class Config:
    # Diretores
    BASE_DIR = BASE_DIR
    OUTPUT_DIR = BASE_DIR / "output"
    REPORTS_DIR = BASE_DIR / "reports"
    DB_PATH = BASE_DIR / "jobs.db"
    CURRICULUM_PATH = BASE_DIR / "curriculum_base.json"

    # LLM / IA (gratuito ou pago — todos opcionais)
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini").lower()  # gemini|ollama|openai|claude|groq|openrouter|custom
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # "gemini-flash-latest" e "gemini-pro-latest" são aliases que o Google atualiza
    # automaticamente para o modelo estável mais recente — evita 404 quando uma
    # versão fixa (ex: gemini-1.5-flash, gemini-2.5-flash) é aposentada.
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "minimax/minimax-m3:free")  # vision free: minimax-m3, nemotron-3-nano-omni
    CUSTOM_LLM_URL = os.getenv("CUSTOM_LLM_URL", "")
    CUSTOM_LLM_KEY = os.getenv("CUSTOM_LLM_KEY", "")

    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST") or "smtp.gmail.com"
    SMTP_PORT = int(os.getenv("SMTP_PORT") or "587")  # "or" cobre tanto var ausente quanto salva vazia (ex: GUI limpou o campo)
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")

    # Credenciais
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
    LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
    LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
    GUPY_EMAIL = os.getenv("GUPY_EMAIL", "")
    GUPY_PASSWORD = os.getenv("GUPY_PASSWORD", "")

    # Preferências de Vaga (Padrão caso não sejam especificadas na execução)
    TARGET_KEYWORDS = ["Desenvolvedor Python", "Python Developer", "Engenheiro de Software", "Desenvolvedor Backend"]
    TARGET_LOCATION = "Brasil" # Ou "Remoto", "São Paulo"
    MIN_MATCH_SCORE = 60 # Porcentagem mínima de aderência para candidatar-se
    WORK_MODE = os.getenv("WORK_MODE", "remoto")  # remoto | presencial | hibrido | indiferente
    PRESENCIAL_LOCATION = os.getenv("PRESENCIAL_LOCATION", "")
    CONTRACT_TYPE = os.getenv("CONTRACT_TYPE", "indiferente")  # clt | pj | indiferente
    SEARCH_CONFIG_PATH = BASE_DIR / "search_config.json"
    # Filtros avançados (lidos de search_config.json)
    # Notificações
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
    DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "20") or 20)

    # Criar diretórios se não existirem
    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
