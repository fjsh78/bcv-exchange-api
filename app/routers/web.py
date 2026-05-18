"""
web.py - Jinja2-rendered HTML dashboard routes.
"""
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, HISTORY_LIMIT
from app.services import storage

router = APIRouter()

templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def dashboard(request: Request):
    latest  = storage.get_latest()
    history = storage.get_all()

    # Show last N records, most recent first
    history_display = list(reversed(history))[:HISTORY_LIMIT]

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request":  request,
            "latest":   latest,
            "history":  history_display,
        },
    )
