"""
main.py - FastAPI application factory and startup configuration.

Run with:
    uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging
import logging.config

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import API_V1_PREFIX
from app.routers import api, web

# ── Logging ───────────────────────────────────────────────────────────────────
logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
            }
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "bcv": {"level": "DEBUG", "propagate": True},
            "uvicorn.error": {"level": "INFO"},
            "uvicorn.access": {"level": "WARNING"},
        },
    }
)

# ── Scheduled job ─────────────────────────────────────────────────────────────
logger = logging.getLogger("bcv.scheduler")

def scheduled_refresh():
    """Runs every day at 07:40 — scrapes BCV and saves to JSON."""
    from app.services import scraper, storage
    try:
        logger.info("⏰ Scheduled refresh starting...")
        rates, warnings = scraper.fetch_rates()
        record = storage.upsert(rates)
        logger.info("✅ Scheduled refresh OK — USD=%.8f", record.rates.USD or 0)
        if warnings:
            logger.warning("Warnings: %s", "; ".join(warnings))
    except Exception as exc:
        logger.error("❌ Scheduled refresh failed: %s", exc)


scheduler = BackgroundScheduler(timezone="America/Caracas")
scheduler.add_job(
    scheduled_refresh,
    trigger=CronTrigger(hour=7, minute=40),
    id="daily_bcv_refresh",
    name="BCV daily rate refresh",
    replace_existing=True,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.start()
    logger.info("🗓️  Scheduler started — daily refresh at 07:40 VET")
    yield
    scheduler.shutdown()
    logger.info("Scheduler stopped.")


# ── Application ───────────────────────────────────────────────────────────────
app = FastAPI(
    lifespan=lifespan,
    title="BCV Exchange Rate API",
    description=(
        "API RESTful para consulta y almacenamiento histórico de los tipos de "
        "cambio oficiales del Banco Central de Venezuela."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(web.router)                          # /  → dashboard
app.include_router(api.router, prefix=API_V1_PREFIX)    # /api/v1/…
