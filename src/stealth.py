import random
import time

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
]

def random_ua() -> str:
    return random.choice(USER_AGENTS)

def jitter_sleep(base: float = 1.5, jitter: float = 1.0):
    """Sleep com jitter: base ± jitter."""
    time.sleep(max(0.2, base + random.uniform(-jitter, jitter)))

def random_headers() -> dict:
    return {
        "User-Agent": random_ua(),
        "Accept-Language": random.choice(["pt-BR,pt;q=0.9,en-US;q=0.8", "en-US,en;q=0.9,pt-BR;q=0.8"]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
