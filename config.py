import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
BASE_DIR = Path(__file__).resolve().parent
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
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:latest")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    CUSTOM_LLM_URL = os.getenv("CUSTOM_LLM_URL", "")
    CUSTOM_LLM_KEY = os.getenv("CUSTOM_LLM_KEY", "")

    # SMTP
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USER = os.getenv("SMTP_USER", "")
    SMTP_PASS = os.getenv("SMTP_PASS", "")

    # Credenciais
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
