"""
models.py - Pydantic data models shared across the application.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class Rates(BaseModel):
    USD: Optional[float] = None
    EUR: Optional[float] = None
    CNY: Optional[float] = None
    TRY: Optional[float] = None
    RUB: Optional[float] = None
    BINANCE: Optional[float] = None


class ExchangeRecord(BaseModel):
    id: int
    date: str                       # ISO format: YYYY-MM-DD
    rates: Rates
    timestamp: str                  # ISO format datetime

    @classmethod
    def build(cls, record_id: int, rates: Rates) -> "ExchangeRecord":
        now = datetime.now()
        return cls(
            id=record_id,
            date=now.date().isoformat(),
            rates=rates,
            timestamp=now.isoformat(timespec="seconds"),
        )


class ScrapeResult(BaseModel):
    success: bool
    message: str
    record: Optional[ExchangeRecord] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
