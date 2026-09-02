import requests
from pathlib import Path
from config import Config

def notify_desktop(title: str, message: str):
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=6)
        return True
    except Exception as e:
        print(f"[Notify] desktop falhou: {e}")
        # fallback win10 toast via powershell not needed
        return False

def _escape_markdown(text: str) -> str:
    """Escapa caracteres do Markdown legado do Telegram — sem isso, nome de vaga/empresa com
    '_', '*', '`' ou '[' quebra a entidade e a API retorna 400 (notificação simplesmente não chega)."""
    if not text:
        return text
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, "\\" + ch)
    return text

def notify_telegram(message: str) -> bool:
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return False
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        r = requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}, timeout=8)
        if r.status_code != 200:
            # fallback sem formatação, caso ainda assim a Markdown tenha quebrado
            r = requests.post(url, json={"chat_id": chat_id, "text": message.replace("*", "").replace("\\", "")}, timeout=8)
        return r.status_code == 200
    except Exception as e:
        print(f"[Notify] telegram erro: {e}")
        return False

def notify_all(title: str, message: str):
    notify_desktop(title, message)
    # telegram com titulo + msg (escapados — ver _escape_markdown)
    notify_telegram(f"*{_escape_markdown(title)}*\n{_escape_markdown(message)}")
