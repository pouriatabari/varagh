"""Shared FastAPI dependencies and template context helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.db import get_session
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


def base_context(request: Request, session: Session, **extra: Any) -> dict[str, Any]:
    """Build the template context shared by every page."""
    context: dict[str, Any] = {
        "request": request,
        "csrf_token": get_csrf_token(request),
        "digits": settings_service.digit_mode(session),
        "timezone": settings_service.timezone_name(session),
        "calendar_system": settings_service.calendar_system(session),
        "active_page": "",
        "messages": [],
    }
    context.update(extra)
    return context


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
