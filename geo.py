import requests
import re
from typing import Optional, Tuple

# Cache simples para geocoding
_GEO_CACHE = {}

def geocode(city_state: str) -> Optional[Tuple[float,float]]:
    """Geocodifica 'São Paulo, SP' via Nominatim (gratuito). Retorna (lat, lon) ou None."""
    if not city_state or city_state.lower() in ("brasil","remoto","remote"):
        return None
    key = city_state.strip().lower()
    if key in _GEO_CACHE:
        return _GEO_CACHE[key]
    try:
        url = "https://nominatim.openstreetmap.org/search"
        params = {"q": city_state, "format": "json", "limit": 1, "countrycodes": "br", "addressdetails": 0}
        headers = {"User-Agent": "JobAutoFit/1.0 (contato: jobautofit@local)"}
        r = requests.get(url, params=params, headers=headers, timeout=8)
        if r.status_code == 200 and r.json():
            data = r.json()[0]
            lat = float(data["lat"]); lon = float(data["lon"])
            _GEO_CACHE[key] = (lat, lon)
            return (lat, lon)
    except Exception as e:
        print(f"[Geo] erro geocode {city_state}: {e}")
    _GEO_CACHE[key] = None
    return None

def haversine(lat1, lon1, lat2, lon2) -> float:
    """Distância em km entre dois pontos (Haversine)."""
    import math
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def distance_km(origin: str, job_location: str) -> Optional[float]:
    """Calcula distância entre origin (usuário) e job_location. Retorna None se não geocodificável."""
    if not origin or not job_location: return None
    # pega primeira parte antes de " - " ou "," para cidade
    orig_city = origin.split(",")[0].strip()
    job_city = job_location.split(",")[0].split("-")[0].strip()
    # se job for remoto, distância 0
    if "remoto" in job_location.lower() or "remote" in job_location.lower():
        return 0.0
    o = geocode(orig_city)
    j = geocode(job_city)
    if o and j:
        return haversine(o[0], o[1], j[0], j[1])
    return None

# USD -> BRL conversão (taxa aproximada, atualizável)
USD_BRL = 5.20

def convert_salary_to_brl(text: str) -> Optional[int]:
    """Extrai maior salário do texto e converte para BRL (se USD)."""
    # já existe parse_salary em filters.py, mas aqui garante conversão
    try:
        from filters import parse_salary
        # parse_salary já converte USD*5, então reutiliza
        val = parse_salary(text)
        return val if val else None
    except:
        return None
