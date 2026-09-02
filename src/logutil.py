import logging
from logging.handlers import RotatingFileHandler
from config import Config

_LOG_DIR = Config.BASE_DIR / "logs"
_logger = None

def get_logger():
    global _logger
    if _logger is not None:
        return _logger
    logger = logging.getLogger("jobautofit")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        try:
            _LOG_DIR.mkdir(exist_ok=True)
            fh = RotatingFileHandler(_LOG_DIR / "jobautofit.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            logger.addHandler(fh)
        except Exception:
            pass
    _logger = logger
    return _logger

def log_print(msg: str = ""):
    """Imprime no stdout (GUI captura via pipe/redirect) e grava também em logs/jobautofit.log,
    para dar pra investigar depois uma execução agendada que rodou sem ninguém olhando.
    O .exe é --windowed (sem console): sys.stdout pode ser None ali, e um print() comum
    lançaria AttributeError bem no meio de um except — por isso o print vai protegido."""
    try:
        print(msg)
    except Exception:
        pass
    try:
        get_logger().info(str(msg))
    except Exception:
        pass
