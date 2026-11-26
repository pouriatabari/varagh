"""Holiday list backed by ``data/holidays_jalali.json``.

The file is user-owned: we ship an empty example and never hard-code official
holidays. Format::

    {
      "holidays": [
        {"date": "1404/01/01", "title": "نام تعطیلی"}
      ]
    }

``date`` is a Jalali date in ``YYYY/MM/DD`` form. Anything else is ignored.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.utils.jalali import jalali_of
from app.utils.time import parse_jalali_date


@dataclass(frozen=True, slots=True)
class Holiday:
    """A single user-defined holiday."""

    jalali_date: str
    title: str

    @property
    def gregorian(self) -> date | None:
        """Return the Gregorian date of the holiday, if it parses."""
        return parse_jalali_date(self.jalali_date)


def holidays_path() -> Path:
    """Return the path of the holidays JSON file."""
    return Path(get_settings().data_dir) / "holidays_jalali.json"


def _read_raw() -> dict:
    path = holidays_path()
    if not path.exists():
        return {"holidays": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"holidays": []}
    if not isinstance(payload, dict):
        return {"holidays": []}
    return payload


def list_holidays() -> list[Holiday]:
    """Return the holidays stored in the file, sorted by Jalali date."""
    payload = _read_raw()
    raw = payload.get("holidays") or []
    holidays: list[Holiday] = []
    for item in raw:
        if isinstance(item, str):
            holidays.append(Holiday(jalali_date=item.strip(), title=""))
        elif isinstance(item, dict):
            date_str = str(item.get("date", "")).strip()
            if date_str:
                holidays.append(Holiday(jalali_date=date_str, title=str(item.get("title", ""))))
    holidays.sort(key=lambda item: item.jalali_date)
    return holidays


def holiday_dates() -> set[date]:
    """Return the Gregorian dates of all configured holidays."""
    return {holiday.gregorian for holiday in list_holidays() if holiday.gregorian is not None}


def is_holiday(value: date) -> bool:
    """True when the given Gregorian date is a configured holiday."""
    return value in holiday_dates()


def save_holidays(holidays: list[Holiday]) -> None:
    """Write the holiday list back to disk."""
    path = holidays_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "description": 'روزهای تعطیل کاربر — قالب: {"date": "۱۴۰۴/۰۱/۰۱", "title": "نام"}',
        "holidays": [{"date": holiday.jalali_date, "title": holiday.title} for holiday in holidays],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _normalise(jalali_date: str) -> str | None:
    """Return the canonical ``YYYY/MM/DD`` Jalali form of a date string."""
    parsed = parse_jalali_date(jalali_date)
    if parsed is None:
        return None
    jalali = jalali_of(parsed)
    return f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}"


def add_holiday(jalali_date: str, title: str = "") -> Holiday | None:
    """Add a holiday; returns ``None`` when the date is invalid or duplicated."""
    normalised = _normalise(jalali_date)
    if normalised is None:
        return None
    holidays = [h for h in list_holidays() if h.jalali_date != normalised]
    holidays.append(Holiday(jalali_date=normalised, title=title.strip()))
    holidays.sort(key=lambda item: item.jalali_date)
    save_holidays(holidays)
    return Holiday(jalali_date=normalised, title=title.strip())


def remove_holiday(jalali_date: str) -> bool:
    """Remove a holiday; returns True when something was removed."""
    normalised = _normalise(jalali_date)
    if normalised is None:
        return False
    holidays = list_holidays()
    remaining = [h for h in holidays if h.jalali_date != normalised]
    if len(remaining) == len(holidays):
        return False
    save_holidays(remaining)
    return True
