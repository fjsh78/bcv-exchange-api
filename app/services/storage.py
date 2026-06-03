"""
storage.py - SQLite persistence layer.

Esta implementación reemplaza el almacenamiento JSON con SQLite para que la
app use una base de datos local más robusta y compatible con despliegues.
"""
from __future__ import annotations

import json
import logging
import sqlite3
import threading
from datetime import date, datetime
from typing import List, Optional

from app.config import DB_FILE
from app.models import ExchangeRecord, Rates
from app.services.migration import check_and_migrate

logger = logging.getLogger("bcv.storage")
_lock = threading.Lock()


def _get_connection() -> sqlite3.Connection:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_binance_column(conn: sqlite3.Connection) -> None:
    row = conn.execute(
        "PRAGMA table_info(exchange_records)"
    ).fetchall()
    columns = [col[1] for col in row]
    if "binance" not in columns:
        conn.execute("ALTER TABLE exchange_records ADD COLUMN binance REAL")


def _init_db() -> None:
    with _get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS exchange_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                usd REAL,
                eur REAL,
                cny REAL,
                try_rate REAL,
                rub REAL,
                binance REAL,
                timestamp TEXT NOT NULL
            )
            """
        )
        _ensure_binance_column(conn)
        check_and_migrate(conn)
    _migrate_json_if_present()


def _migrate_json_if_present() -> None:
    legacy_json = DB_FILE.with_suffix(".json")
    if not legacy_json.exists():
        return

    logger.info("Migrando datos JSON desde %s a SQLite %s", legacy_json, DB_FILE)
    try:
        with open(legacy_json, "r", encoding="utf-8") as fh:
            raw_records = json.load(fh)
    except Exception as exc:
        logger.exception("Error leyendo JSON legacy: %s", exc)
        return

    with _get_connection() as conn:
        for raw in raw_records:
            try:
                rates = Rates(**raw["rates"])
                conn.execute(
                    """
                    INSERT OR IGNORE INTO exchange_records
                        (id, date, usd, eur, cny, try_rate, rub, binance, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        raw["id"],
                        raw["date"],
                        rates.USD,
                        rates.EUR,
                        rates.CNY,
                        rates.TRY,
                        rates.RUB,
                        rates.BINANCE,
                        raw["timestamp"],
                    ),
                )
            except Exception:
                logger.exception("Registro legacy inválido: %s", raw)
    logger.info("Migración JSON completada.")


def _row_to_record(row: sqlite3.Row) -> ExchangeRecord:
    return ExchangeRecord(
        id=row["id"],
        date=row["date"],
        rates=Rates(
            USD=row["usd"],
            EUR=row["eur"],
            CNY=row["cny"],
            TRY=row["try_rate"],
            RUB=row["rub"],
            BINANCE=row["binance"],
        ),
        timestamp=row["timestamp"],
    )


_init_db()


def get_all() -> List[ExchangeRecord]:
    """Return every stored record, oldest first."""
    with _lock, _get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM exchange_records ORDER BY id ASC"
        ).fetchall()
    return [_row_to_record(row) for row in rows]


def get_latest() -> Optional[ExchangeRecord]:
    """Return the most recently stored record, or None."""
    with _lock, _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM exchange_records ORDER BY id DESC LIMIT 1"
        ).fetchone()
    return _row_to_record(row) if row else None


def get_by_date(date_str: str) -> Optional[ExchangeRecord]:
    """Return the record for *date_str* (YYYY-MM-DD), or None."""
    with _lock, _get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM exchange_records WHERE date = ? ORDER BY id DESC LIMIT 1",
            (date_str,),
        ).fetchone()
    return _row_to_record(row) if row else None


def add_record(rates: Rates) -> ExchangeRecord:
    """Insert or update today's record in SQLite."""
    today = date.today().isoformat()
    now_str = datetime.now().isoformat(timespec="seconds")

    with _lock, _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO exchange_records
                (date, usd, eur, cny, try_rate, rub, binance, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                today,
                rates.USD,
                rates.EUR,
                rates.CNY,
                rates.TRY,
                rates.RUB,
                rates.BINANCE,
                now_str,
            ),
        )
        row = conn.execute(
            "SELECT * FROM exchange_records WHERE date = ? ORDER BY id DESC LIMIT 1",
            (today,),
        ).fetchone()

    if row is None:
        raise RuntimeError("No se pudo persistir el registro de hoy.")

    logger.info("Persistido registro para fecha %s", today)
    return _row_to_record(row)
