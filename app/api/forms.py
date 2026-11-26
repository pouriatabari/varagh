"""Helpers to read and parse HTML form submissions."""

from __future__ import annotations

from datetime import datetime

from starlette.datastructures import FormData

from app.utils.time import parse_jalali_datetime


def form_str(form: FormData, key: str, default: str = "") -> str:
    """Return a stripped string field."""
    value = form.get(key)
    if value is None:
        return default
    return str(value).strip()


def form_optional_str(form: FormData, key: str) -> str | None:
    """Return a stripped string field, or ``None`` when it is empty."""
    value = form_str(form, key)
    return value or None


def form_int(form: FormData, key: str, default: int | None = None) -> int | None:
    """Return an integer field, or ``default`` when it is missing or invalid."""
    raw = form_str(form, key)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def form_bool(form: FormData, key: str) -> bool:
    """Return True when a checkbox is checked."""
    return form_str(form, key).lower() in {"1", "true", "on", "yes"}


def form_datetime(form: FormData, key: str, timezone: str) -> datetime | None:
    """Parse a Jalali date/time field («1404/08/05 14:30») into an aware UTC datetime."""
    raw = form_str(form, key)
    if not raw:
        return None
    return parse_jalali_datetime(raw, timezone)
