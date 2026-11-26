"""UTC storage / local display helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.utils.jalali import gregorian_of, jalali_of
from app.utils.text import apply_digits


def default_timezone() -> str:
    """Return the configured display timezone."""
    from app.config import get_settings

    return get_settings().timezone


def get_zone(name: str) -> ZoneInfo:
    """Return a ZoneInfo, falling back to UTC for unknown names."""
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def utcnow() -> datetime:
    """Current time as an aware UTC datetime."""
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Treat naive datetimes as UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def to_local(value: datetime, timezone: str) -> datetime:
    """Convert an aware datetime into the given timezone."""
    return ensure_aware(value).astimezone(get_zone(timezone))


def format_datetime(
    value: datetime | None, timezone: str, digits: str = "persian", with_time: bool = True
) -> str:
    """Render a datetime as a Jalali string like «۱۴۰۴/۰۸/۰۵ ۱۴:۳۰»."""
    if value is None:
        return "—"
    local = to_local(value, timezone)
    jalali = jalali_of(local.date())
    text = f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}"
    if with_time:
        text += f" {local.hour:02d}:{local.minute:02d}"
    return apply_digits(text, digits)


def format_date(value: date | None, digits: str = "persian") -> str:
    """Render a date as a Jalali string like «۱۴۰۴/۰۸/۰۵»."""
    if value is None:
        return "—"
    jalali = jalali_of(value)
    return apply_digits(f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}", digits)


def format_time(value: datetime | None, timezone: str, digits: str = "persian") -> str:
    """Render only the time part of a datetime."""
    if value is None:
        return "—"
    local = to_local(value, timezone)
    return apply_digits(f"{local.hour:02d}:{local.minute:02d}", digits)


def relative_days(value: datetime | None, now: datetime, timezone: str) -> int | None:
    """Whole days between ``now`` and ``value`` (positive when in the past)."""
    if value is None:
        return None
    return (to_local(now, timezone).date() - to_local(value, timezone).date()).days


def parse_jalali_date(text: str) -> date | None:
    """Parse «۱۴۰۴/۰۸/۰۵» or «1404-8-5» into a Gregorian date."""
    from app.utils.text import to_latin_digits

    cleaned = to_latin_digits(text or "").strip().replace("-", "/").replace(".", "/")
    parts = [p for p in cleaned.split("/") if p]
    if len(parts) != 3:
        return None
    try:
        year, month, day = (int(p) for p in parts)
    except ValueError:
        return None
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    try:
        return gregorian_of(year, month, day)
    except (ValueError, OverflowError):
        return None


def parse_jalali_datetime(text: str, timezone: str) -> datetime | None:
    """Parse «۱۴۰۴/۰۸/۰۵ ۱۴:۳۰» into an aware UTC datetime."""
    from app.utils.text import to_latin_digits

    cleaned = to_latin_digits(text or "").strip()
    parts = cleaned.split()
    if not parts:
        return None
    day = parse_jalali_date(parts[0])
    if day is None:
        return None
    hour, minute = 0, 0
    if len(parts) > 1 and ":" in parts[1]:
        raw_hour, _, raw_minute = parts[1].partition(":")
        try:
            hour, minute = int(raw_hour), int(raw_minute)
        except ValueError:
            return None
    local = datetime(day.year, day.month, day.day, hour, minute, tzinfo=get_zone(timezone))
    return local.astimezone(UTC)
