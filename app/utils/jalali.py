"""Jalali (Shamsi) calendar helpers.

The database always stores Gregorian/UTC values; every conversion to the
Persian calendar happens here, server-side.
"""

from __future__ import annotations

import datetime as dt

import jdatetime

PERSIAN_MONTHS: tuple[str, ...] = (
    "فروردین",
    "اردیبهشت",
    "خرداد",
    "تیر",
    "مرداد",
    "شهریور",
    "مهر",
    "آبان",
    "آذر",
    "دی",
    "بهمن",
    "اسفند",
)

# Saturday-first, because in Iran the week starts on Saturday and ends on Friday.
PERSIAN_WEEKDAYS: tuple[str, ...] = (
    "شنبه",
    "یکشنبه",
    "دوشنبه",
    "سه‌شنبه",
    "چهارشنبه",
    "پنجشنبه",
    "جمعه",
)

PERSIAN_WEEKDAYS_SHORT: tuple[str, ...] = ("ش", "ی", "د", "س", "چ", "پ", "ج")

PERSIAN_WEEKDAYS_SHORT_EN: tuple[str, ...] = ("Sa", "Su", "Mo", "Tu", "We", "Th", "Fr")

WEEKEND_JALALI_WEEKDAY = 6  # Friday (Saturday = 1 ... Friday = 7 in Persian usage)

# Jalali weekday index of the days that count as the weekend.
# Saturday-first ordering: شنبه=0 ... جمعه=6.
DEFAULT_WEEKEND_WEEKDAYS: frozenset[int] = frozenset({6})

PERIOD_TYPES: tuple[str, ...] = ("month", "quarter", "half", "year", "custom")


def jalali_of(value: dt.date) -> jdatetime.date:
    """Convert a Gregorian date into a Jalali date."""
    return jdatetime.date.fromgregorian(date=value)


def gregorian_of(year: int, month: int, day: int) -> dt.date:
    """Convert a Jalali year/month/day into a Gregorian date."""
    return jdatetime.date(year, month, day).togregorian()


# A Jalali year is a leap year when its remainder modulo 33 is one of these.
_LEAP_REMAINDERS = frozenset({1, 5, 9, 13, 17, 22, 26, 30})


def is_leap_jalali(year: int) -> bool:
    """Return True when the given Jalali year has 366 days."""
    return year % 33 in _LEAP_REMAINDERS


def days_in_jalali_month(year: int, month: int) -> int:
    """Return the number of days in a Jalali month (handles Esfand leap years)."""
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if is_leap_jalali(year) else 29


def jalali_month_grid(year: int, month: int) -> list[list[dt.date]]:
    """Return the Jalali month as a list of weeks (Saturday-first)."""
    first = gregorian_of(year, month, 1)
    length = days_in_jalali_month(year, month)
    last = first + dt.timedelta(days=length - 1)
    grid_start = week_start(first)
    grid_end = week_start(last) + dt.timedelta(days=6)

    weeks: list[list[dt.date]] = []
    cursor = grid_start
    while cursor <= grid_end:
        week = [cursor + dt.timedelta(days=i) for i in range(7)]
        weeks.append(week)
        cursor += dt.timedelta(days=7)
    return weeks


def week_start(value: dt.date) -> dt.date:
    """Return the Saturday that starts the week containing ``value``."""
    return value - dt.timedelta(days=(value.weekday() - 5) % 7)


def jalali_input_string(value: dt.date | None) -> str:
    """Return a date as ``YYYY/MM/DD`` in Jalali form with Latin digits."""
    if value is None:
        return ""
    jalali = jalali_of(value)
    return f"{jalali.year:04d}/{jalali.month:02d}/{jalali.day:02d}"


def week_start_jalali(value: jdatetime.date) -> jdatetime.date:
    """Return the Jalali Saturday that starts the week containing ``value``."""
    greg = value.togregorian()
    return jalali_of(week_start(greg))


def is_jalali_weekend(value: dt.date, weekend_weekdays: frozenset[int] | None = None) -> bool:
    """True when the date falls on one of the configured weekend weekdays."""
    days = weekend_weekdays or DEFAULT_WEEKEND_WEEKDAYS
    return jalali_weekday_index(value) in days


def jalali_weekday_index(value: dt.date) -> int:
    """Return the Saturday-first weekday index of a Gregorian date (شنبه = 0)."""
    return (value.weekday() - 5) % 7


def period_bounds(
    period_type: str, reference: dt.date, calendar_system: str = "jalali"
) -> tuple[dt.date, dt.date]:
    """Return the (start, end) Gregorian bounds of a review period.

    ``reference`` is any date inside the wanted period.
    """
    if period_type == "custom":
        return reference, reference
    if calendar_system == "gregorian":
        return _gregorian_period_bounds(period_type, reference)
    return _jalali_period_bounds(period_type, reference)


def _jalali_period_bounds(period_type: str, reference: dt.date) -> tuple[dt.date, dt.date]:
    jd = jalali_of(reference)
    year = jd.year
    if period_type == "month":
        first_month, last_month = jd.month, jd.month
    elif period_type == "quarter":
        first_month = ((jd.month - 1) // 3) * 3 + 1
        last_month = first_month + 2
    elif period_type == "half":
        first_month = 1 if jd.month <= 6 else 7
        last_month = first_month + 5
    elif period_type == "year":
        first_month, last_month = 1, 12
    else:
        return reference, reference
    start = gregorian_of(year, first_month, 1)
    end = gregorian_of(year, last_month, days_in_jalali_month(year, last_month))
    return start, end


def _gregorian_period_bounds(period_type: str, reference: dt.date) -> tuple[dt.date, dt.date]:
    year = reference.year
    if period_type == "month":
        first_month, last_month = reference.month, reference.month
    elif period_type == "quarter":
        first_month = ((reference.month - 1) // 3) * 3 + 1
        last_month = first_month + 2
    elif period_type == "half":
        first_month = 1 if reference.month <= 6 else 7
        last_month = first_month + 5
    elif period_type == "year":
        first_month, last_month = 1, 12
    else:
        return reference, reference

    def month_end(month: int) -> dt.date:
        if month == 12:
            return dt.date(year, 12, 31)
        return dt.date(year, month + 1, 1) - dt.timedelta(days=1)

    return dt.date(year, first_month, 1), month_end(last_month)


def previous_period(
    period_type: str, start: dt.date, end: dt.date, calendar_system: str = "jalali"
) -> tuple[dt.date, dt.date]:
    """Return the bounds of the period immediately before the given one."""
    if period_type == "custom":
        # A custom period has no calendar anchor: the previous one is the
        # period of the same length that ends the day before it starts.
        length = (end - start).days + 1
        prev_end = start - dt.timedelta(days=1)
        return prev_end - dt.timedelta(days=length - 1), prev_end
    if calendar_system == "gregorian":
        length = (end - start).days + 1
        prev_end = start - dt.timedelta(days=1)
        return prev_end - dt.timedelta(days=length - 1), prev_end
    jstart = jalali_of(start)
    if period_type == "month":
        if jstart.month == 1:
            prev_year, prev_month = jstart.year - 1, 12
        else:
            prev_year, prev_month = jstart.year, jstart.month - 1
        p_start = gregorian_of(prev_year, prev_month, 1)
        p_end = gregorian_of(prev_year, prev_month, days_in_jalali_month(prev_year, prev_month))
    elif period_type == "quarter":
        quarter = (jstart.month - 1) // 3
        if quarter == 0:
            prev_year, prev_q = jstart.year - 1, 3
        else:
            prev_year, prev_q = jstart.year, quarter - 1
        first_month = prev_q * 3 + 1
        last_month = first_month + 2
        p_start = gregorian_of(prev_year, first_month, 1)
        p_end = gregorian_of(prev_year, last_month, days_in_jalali_month(prev_year, last_month))
    elif period_type == "half":
        half = 0 if jstart.month <= 6 else 1
        if half == 0:
            prev_year, prev_h = jstart.year - 1, 1
        else:
            prev_year, prev_h = jstart.year, 0
        first_month = 1 + prev_h * 6
        last_month = first_month + 5
        p_start = gregorian_of(prev_year, first_month, 1)
        p_end = gregorian_of(prev_year, last_month, days_in_jalali_month(prev_year, last_month))
    elif period_type == "year":
        prev_year = jstart.year - 1
        p_start = gregorian_of(prev_year, 1, 1)
        p_end = gregorian_of(prev_year, 12, days_in_jalali_month(prev_year, 12))
    else:
        return start, end
    return p_start, p_end
