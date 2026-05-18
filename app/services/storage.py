"""
storage.py - JSON-file persistence layer.

The file acts as a simple append-only table of ExchangeRecord objects.
Concurrency is handled with a threading.Lock (single-process deployments).
For multi-worker deployments, swap the lock for a file-level advisory lock
or migrate to SQLite/PostgreSQL.
"""
from __future__ import annotations

import json
import logging
import threading
from typing import List, Optional

from app.config import DB_FILE
from app.models import ExchangeRecord, Rates

logger = logging.getLogger("bcv.storage")

_lock = threading.Lock()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_raw() -> list[dict]:
    if not DB_FILE.exists() or DB_FILE.stat().st_size == 0:
        return []
    with open(DB_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _dump_raw(records: list[dict]) -> None:
    with open(DB_FILE, "w", encoding="utf-8") as fh:
        json.dump(records, fh, indent=2, ensure_ascii=False)


def _to_record(raw: dict) -> ExchangeRecord:
    return ExchangeRecord(
        id=raw["id"],
        date=raw["date"],
        rates=Rates(**raw["rates"]),
        timestamp=raw["timestamp"],
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_all() -> List[ExchangeRecord]:
    """Return every stored record, oldest first."""
    with _lock:
        raw_list = _load_raw()
    return [_to_record(r) for r in raw_list]


def get_latest() -> Optional[ExchangeRecord]:
    """Return the most recently stored record, or None."""
    with _lock:
        raw_list = _load_raw()
    if not raw_list:
        return None
    return _to_record(raw_list[-1])


def get_by_date(date_str: str) -> Optional[ExchangeRecord]:
    """Return the record for *date_str* (YYYY-MM-DD), or None."""
    with _lock:
        raw_list = _load_raw()
    for r in raw_list:
        if r.get("date") == date_str:
            return _to_record(r)
    return None


def upsert(rates: Rates) -> ExchangeRecord:
    """
    Insert or update today's record.

    - If no record exists for today → create a new one with next auto-id.
    - If a record already exists   → update its rates + timestamp in place.
    """
    from datetime import datetime

    today = datetime.now().date().isoformat()

    with _lock:
        raw_list = _load_raw()

        # Find existing record for today
        existing_idx: Optional[int] = None
        for idx, r in enumerate(raw_list):
            if r.get("date") == today:
                existing_idx = idx
                break

        now_str = datetime.now().isoformat(timespec="seconds")

        if existing_idx is not None:
            # Update in place
            record_id = raw_list[existing_idx]["id"]
            raw_list[existing_idx]["rates"] = rates.model_dump()
            raw_list[existing_idx]["timestamp"] = now_str
            logger.info("Updated existing record id=%d for date=%s", record_id, today)
        else:
            # Create new record
            record_id = (max((r["id"] for r in raw_list), default=0)) + 1
            raw_list.append(
                {
                    "id": record_id,
                    "date": today,
                    "rates": rates.model_dump(),
                    "timestamp": now_str,
                }
            )
            logger.info("Created new record id=%d for date=%s", record_id, today)

        _dump_raw(raw_list)

        # Return the freshly persisted record
        saved = next(r for r in raw_list if r["id"] == record_id)
        return _to_record(saved)
