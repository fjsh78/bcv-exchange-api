"""
config.py - Centralized configuration and multi-selector definitions.
All tunable parameters live here so changing them requires no code edits.
"""
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent
DATA_DIR   = BASE_DIR / "data"
DB_FILE    = DATA_DIR / "exchange_rates.db"

# Ensure data directory exists at import time
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── Scraping ─────────────────────────────────────────────────────────────────
BCV_URL     = "https://www.bcv.org.ve/"
REQUEST_TIMEOUT = 15          # seconds
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-VE,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Currency selector strategies (tried in order until one succeeds) ─────────
# Each entry is a dict with 'method' and 'params'.
#
# method "id"   → soup.find(id=params["id"])  → look for numeric text inside
# method "css"  → soup.select_one(params["selector"])
# method "text" → find <strong> or <div> whose text matches params["label"]
#
CURRENCY_SELECTORS: dict[str, list[dict]] = {
    "USD": [
        {"method": "id",   "params": {"id": "dolar"}},
        {"method": "css",  "params": {"selector": "#dolar strong"}},
        {"method": "css",  "params": {"selector": ".dolar strong"}},
        {"method": "text", "params": {"label": "USD"}},
    ],
    "EUR": [
        {"method": "id",   "params": {"id": "euro"}},
        {"method": "css",  "params": {"selector": "#euro strong"}},
        {"method": "css",  "params": {"selector": ".euro strong"}},
        {"method": "text", "params": {"label": "EUR"}},
    ],
    "CNY": [
        {"method": "id",   "params": {"id": "yuan"}},
        {"method": "css",  "params": {"selector": "#yuan strong"}},
        {"method": "css",  "params": {"selector": ".yuan strong"}},
        {"method": "text", "params": {"label": "CNY"}},
    ],
    "TRY": [
        {"method": "id",   "params": {"id": "lira"}},
        {"method": "css",  "params": {"selector": "#lira strong"}},
        {"method": "css",  "params": {"selector": ".lira strong"}},
        {"method": "text", "params": {"label": "TRY"}},
    ],
    "RUB": [
        {"method": "id",   "params": {"id": "rublo"}},
        {"method": "css",  "params": {"selector": "#rublo strong"}},
        {"method": "css",  "params": {"selector": ".rublo strong"}},
        {"method": "text", "params": {"label": "RUB"}},
    ],
}

# ── API ───────────────────────────────────────────────────────────────────────
API_V1_PREFIX = "/api/v1"
HISTORY_LIMIT = 10            # rows shown in dashboard table
