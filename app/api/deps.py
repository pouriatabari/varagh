"""Shared FastAPI dependencies and template context helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_session
from app.i18n import t
from app.security import get_csrf_token
from app.services import settings as settings_service
from app.utils.clock import Clock, system_clock
from app.utils.time import utcnow


def get_clock() -> Clock:
    """Return the injected clock."""
    return system_clock()


def now() -> datetime:
    """Return the current UTC time (aware)."""
    return utcnow()


def flash_messages(request: Request) -> list[tuple[str, str]]:
    """Build flash messages from the query string."""
    messages: list[tuple[str, str]] = []
    flash = request.query_params.get("flash")
    if flash:
        count = request.query_params.get("count")
        messages.append(("success", t(flash, count=int(count)) if count else t(flash)))
    error = request.query_params.get("error")
    if error:
        messages.append(("error", t(error)))
    return messages


def base_context(request: Request, session: Session, **extra: Any) -> dict[str, Any]:
    """Build the template context shared by every page."""
    from app.services import time_entries as time_service

    running = time_service.running_entry(session)
    context: dict[str, Any] = {
        "request": request,
        "csrf_token": get_csrf_token(request),
        "digits": settings_service.digit_mode(session),
        "timezone": settings_service.timezone_name(session),
        "calendar_system": settings_service.calendar_system(session),
        "lexicon": settings_service.lexicon(session),
        "theme": settings_service.theme(session),
        "theme_is_default": settings_service.get_stored_setting(session, "theme") is None,
        "active_page": "",
        "messages": flash_messages(request),
        "running_timer": (
            {"started_at_iso": running.started_at.isoformat()} if running is not None else None
        ),
    }
    context.update(extra)
    return context


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
