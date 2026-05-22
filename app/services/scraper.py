"""
scraper.py - Resilient BCV exchange-rate scraper.

Strategy:
  1. Download the BCV homepage.
  2. For each currency, iterate through CURRENCY_SELECTORS until a numeric
     value is found.  This means the scraper survives minor HTML restructuring.
  3. Return a Rates object; missing currencies are None so callers can decide.
"""
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from app.config import (
    BCV_URL,
    BINANCE_ASSET,
    BINANCE_FIAT,
    BINANCE_P2P_URL,
    BINANCE_TRADE_TYPE,
    CURRENCY_SELECTORS,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT,
)
from app.models import Rates

logger = logging.getLogger("bcv.scraper")

# Matches numbers like "517,96190000" or "517.96190000"
_NUMBER_RE = re.compile(r"[\d]+[,.][\d]+")


def _parse_value(raw: str) -> Optional[float]:
    """Convert BCV-formatted number strings to float."""
    # BCV uses comma as decimal separator sometimes
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    # If there are still multiple dots, keep only first two parts
    parts = cleaned.split(".")
    if len(parts) > 2:
        cleaned = parts[0] + "." + "".join(parts[1:])
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_number_from_element(element) -> Optional[float]:
    """Pull the first numeric string out of a BeautifulSoup element."""
    if element is None:
        return None
    text = element.get_text(separator=" ")
    match = _NUMBER_RE.search(text)
    if match:
        return _parse_value(match.group())
    return None


def _try_selector(soup: BeautifulSoup, currency: str) -> Optional[float]:
    """
    Iterate through registered selectors for *currency* and return the first
    numeric value found, or None if all strategies fail.
    """
    strategies = CURRENCY_SELECTORS.get(currency, [])

    for strategy in strategies:
        method = strategy["method"]
        params = strategy["params"]
        element = None

        try:
            if method == "id":
                element = soup.find(id=params["id"])

            elif method == "css":
                element = soup.select_one(params["selector"])

            elif method == "text":
                label = params["label"]
                # Search any tag whose text contains the currency label
                for tag in soup.find_all(["div", "span", "td", "li", "p"]):
                    if label in tag.get_text():
                        element = tag
                        break

            value = _extract_number_from_element(element)
            if value is not None:
                logger.debug(
                    "Currency %s → %.8f  (method=%s, params=%s)",
                    currency, value, method, params,
                )
                return value

        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Selector failed for %s (method=%s): %s", currency, method, exc
            )

    logger.error("All selectors exhausted for currency: %s", currency)
    return None

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def _fetch_binance_rate() -> Optional[float]:
    """Query Binance P2P for the current USDT/VES price."""
    payload = {
        "asset": BINANCE_ASSET,
        "fiat": BINANCE_FIAT,
        "merchantCheck": False,
        "page": 1,
        "rows": 1,
        "tradeType": BINANCE_TRADE_TYPE,
    }
    headers = {
        **REQUEST_HEADERS,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    logger.info("Fetching Binance P2P price: %s/%s", BINANCE_ASSET, BINANCE_FIAT)
    response = requests.post(BINANCE_P2P_URL, json=payload, headers=headers, timeout=REQUEST_TIMEOUT)
    if not response.ok:
        logger.warning("Binance P2P returned HTTP %s", response.status_code)
        return None

    data = response.json()
    if not isinstance(data, dict):
        logger.warning("Binance P2P returned unexpected payload")
        return None

    items = data.get("data") or []
    if not items:
        logger.warning("Binance P2P returned no data")
        return None

    try:
        price_text = items[0]["adv"]["price"]
        return _parse_value(str(price_text))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not parse Binance price: %s", exc)
        return None


def fetch_rates() -> tuple[Rates, list[str]]:
    """
    Download and parse the BCV homepage.

    Returns
    -------
    rates   : Rates object (missing currencies → None)
    warnings: list of warning strings (empty = perfect scrape)

    Raises
    ------
    requests.RequestException  – network / timeout errors
    RuntimeError               – HTTP error status
    """
    logger.info("Fetching BCV page: %s", BCV_URL)

    response = requests.get(
        BCV_URL,
        headers=REQUEST_HEADERS,
        timeout=REQUEST_TIMEOUT,
        verify=False,
    )

    if not response.ok:
        raise RuntimeError(
            f"BCV returned HTTP {response.status_code}: {response.reason}"
        )

    soup = BeautifulSoup(response.text, "html.parser")
    warnings: list[str] = []

    raw: dict[str, Optional[float]] = {}
    for currency in ("USD", "EUR", "CNY", "TRY", "RUB"):
        value = _try_selector(soup, currency)
        raw[currency] = value
        if value is None:
            warnings.append(f"Could not extract value for {currency}")

    binance_value = _fetch_binance_rate()
    raw["BINANCE"] = binance_value
    if binance_value is None:
        warnings.append("Could not retrieve Binance USDT/VES price")

    rates = Rates(**raw)
    logger.info(
        "Scrape complete. USD=%.5s BINANCE=%.5s warnings=%d",
        str(raw.get("USD")), str(raw.get("BINANCE")), len(warnings),
    )
    return rates, warnings
