"""
api.py - RESTful endpoints for the BCV exchange-rate API.
"""
from __future__ import annotations

import logging

import requests
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.models import ExchangeRecord, ScrapeResult
from app.services import scraper, storage

logger = logging.getLogger("bcv.api")

router = APIRouter()


# ── Scrape & persist ──────────────────────────────────────────────────────────

@router.post("/rates/refresh", response_model=ScrapeResult, tags=["Scraping"])
def refresh_rates() -> ScrapeResult:
    """
    Trigger a live scrape of BCV, persist the result, and return it.
    This endpoint is called both from the dashboard button and directly.
    """
    try:
        rates, warnings = scraper.fetch_rates()
    except requests.exceptions.Timeout:
        raise HTTPException(
            status_code=504,
            detail="Timeout al conectar con el BCV. Intente nuevamente.",
        )
    except requests.exceptions.ConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Error de conexión con el BCV: {exc}",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected scraping error")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {exc}")

    # Validate that we got at least one currency
    if all(v is None for v in rates.model_dump().values()):
        raise HTTPException(
            status_code=422,
            detail=(
                "El scraper no pudo extraer ninguna divisa. "
                "El BCV pudo haber cambiado su estructura HTML."
            ),
        )

    record = storage.add_record(rates)

    message = "Tasas actualizadas correctamente."
    if warnings:
        message += f" Advertencias: {'; '.join(warnings)}"

    return ScrapeResult(success=True, message=message, record=record)


# ── Query endpoints ───────────────────────────────────────────────────────────

@router.get("/rates/latest", response_model=ExchangeRecord, tags=["Consulta"])
def get_latest():
    """Retorna el tipo de cambio más reciente almacenado."""
    record = storage.get_latest()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No hay registros almacenados. Realice un /rates/refresh primero.",
        )
    return record


@router.get("/rates/history", response_model=list[ExchangeRecord], tags=["Consulta"])
def get_history():
    """Retorna el historial completo de tipos de cambio."""
    return storage.get_all()


@router.get("/rates/{date}", response_model=ExchangeRecord, tags=["Consulta"])
def get_by_date(date: str):
    """
    Retorna el tipo de cambio para una fecha específica.

    Formato esperado: YYYY-MM-DD  (ej. 2026-05-19)
    """
    import re
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise HTTPException(
            status_code=422,
            detail="Formato de fecha inválido. Use YYYY-MM-DD.",
        )
    record = storage.get_by_date(date)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"No se encontró registro para la fecha {date}.",
        )
    return record


# ── Conversion endpoint ───────────────────────────────────────────────────────

from pydantic import BaseModel as _Base

class ConversionResult(_Base):
    usd: float
    usd_rate: float
    bolivares: float
    date: str
    timestamp: str

@router.get("/convert", response_model=ConversionResult, tags=["Conversión"])
def convert_usd_to_bs(amount: float = 1.0):
    """
    Convierte dólares (USD) a bolívares usando la tasa más reciente del BCV.

    Parámetros:
    - **amount**: cantidad en USD (por defecto 1.0)

    Ejemplo: /api/v1/convert?amount=50
    """
    record = storage.get_latest()
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No hay tasas almacenadas. Realice un /rates/refresh primero.",
        )
    if record.rates.USD is None:
        raise HTTPException(
            status_code=503,
            detail="La tasa USD no está disponible en el último registro.",
        )
    return ConversionResult(
        usd=amount,
        usd_rate=record.rates.USD,
        bolivares=round(amount * record.rates.USD, 2),
        date=record.date,
        timestamp=record.timestamp,
    )
