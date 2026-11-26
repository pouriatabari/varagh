"""Application settings stored as key/value JSON documents."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import Setting

DEFAULT_SETTINGS: dict[str, Any] = {
    "timezone": "Asia/Tehran",
    "calendar_system": "jalali",
    "digits": "persian",
    "weekly_hour_target": 40,
    "weekend_weekdays": [6],
    "ai": {
        "enabled": False,
        "provider": "",
        "api_key": "",
        "model": "",
        "base_url": "",
        "timeout_seconds": 30,
        "max_output_tokens": 2048,
        "auth_header": "both",
        "custom_url": "",
        "custom_method": "json",
        "custom_headers": "",
    },
    "notifications": {
        "due_soon_minutes": 30,
        "overdue_enabled": True,
        "digest_enabled": True,
        "digest_time": "20:00",
        "journal_nudge_enabled": True,
        "journal_nudge_time": "21:30",
        "review_reminder_enabled": True,
        "stale_learning_enabled": True,
        "stale_learning_days": 30,
        "channels": {"browser": True, "email": False, "webhook": False},
        "email": {"to": ""},
        "webhook": {"url": "", "format": "slack"},
    },
}

MUTABLE_KEYS = frozenset(DEFAULT_SETTINGS)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def get_all_settings(session: Session) -> dict[str, Any]:
    """Return the merged settings document (defaults + stored overrides)."""
    rows = session.scalars(select(Setting)).all()
    stored = {
        row.key: row.value
        for row in rows
        if isinstance(row.value, (dict, list, str, int, float, bool))
    }
    merged = copy.deepcopy(DEFAULT_SETTINGS)
    for key, value in stored.items():
        if key in MUTABLE_KEYS:
            merged[key] = _deep_merge(merged[key], value) if isinstance(value, dict) else value
    return merged


def get_stored_setting(session: Session, key: str) -> Any:
    """Return a stored setting without the defaults; ``None`` when it was never set."""
    row = session.get(Setting, key)
    if row is None:
        return None
    return row.value


def get_setting(session: Session, key: str, default: Any = None) -> Any:
    """Return a single setting value."""
    value = get_all_settings(session).get(key, default)
    return value


def set_setting(session: Session, key: str, value: Any) -> None:
    """Persist a single setting key."""
    if key not in MUTABLE_KEYS:
        raise ValueError(f"unknown setting: {key}")
    row = session.get(Setting, key)
    if row is None:
        row = Setting(key=key, value=value)
        session.add(row)
    else:
        row.value = value
    session.flush()


def update_settings(session: Session, values: dict[str, Any]) -> dict[str, Any]:
    """Merge and persist a partial settings update."""
    current = get_all_settings(session)
    for key, value in values.items():
        if key not in MUTABLE_KEYS:
            continue
        current[key] = _deep_merge(current[key], value) if isinstance(value, dict) else value
        set_setting(session, key, current[key])
    return current


def notification_settings(session: Session) -> dict[str, Any]:
    """Return the notification-related settings block."""
    return get_all_settings(session).get("notifications", {})


def timezone_name(session: Session) -> str:
    """Return the display timezone."""
    return str(get_setting(session, "timezone", "Asia/Tehran"))


def calendar_system(session: Session) -> str:
    """Return ``jalali`` or ``gregorian``."""
    return str(get_setting(session, "calendar_system", "jalali"))


def digit_mode(session: Session) -> str:
    """Return ``persian`` or ``latin``."""
    return str(get_setting(session, "digits", "persian"))


def weekend_weekdays(session: Session) -> frozenset[int]:
    """Return the Saturday-first weekday indexes that count as the weekend."""
    raw = get_setting(session, "weekend_weekdays", [6])
    try:
        return frozenset(int(value) for value in raw)
    except (TypeError, ValueError):
        return frozenset({6})


def weekly_hour_target(session: Session) -> int:
    """Return the weekly measured-hours target."""
    try:
        return int(get_setting(session, "weekly_hour_target", 40))
    except (TypeError, ValueError):
        return 40


def settings_updated_at(session: Session) -> datetime:
    """Return the last time any setting changed (UTC)."""
    rows = session.scalars(select(Setting)).all()
    stamps = [row.created_at for row in rows if row.created_at]
    if not stamps:
        return datetime(1970, 1, 1, tzinfo=UTC)
    return max(stamps)
