"""Jalali conversion, calendar grid and review-period boundary tests."""

from __future__ import annotations

import datetime as dt

from app.utils.jalali import (
    days_in_jalali_month,
    gregorian_of,
    is_leap_jalali,
    jalali_month_grid,
    jalali_of,
    period_bounds,
    previous_period,
    week_start,
)

NAWRUZ_1403 = dt.date(2024, 3, 20)
NAWRUZ_1404 = dt.date(2025, 3, 21)


def test_nawruz_anchors() -> None:
    """Nowruz is 20 March 2024 (1403) and 21 March 2025 (1404)."""
    assert gregorian_of(1403, 1, 1) == NAWRUZ_1403
    assert gregorian_of(1404, 1, 1) == NAWRUZ_1404
    assert (jalali_of(NAWRUZ_1403).year, jalali_of(NAWRUZ_1403).month) == (1403, 1)
    assert (jalali_of(NAWRUZ_1404).year, jalali_of(NAWRUZ_1404).month) == (1404, 1)


def test_leap_year_detection() -> None:
    """Esfand has 30 days in a Jalali leap year and 29 otherwise."""
    assert is_leap_jalali(1403) is True
    assert is_leap_jalali(1404) is False
    assert days_in_jalali_month(1403, 12) == 30
    assert days_in_jalali_month(1404, 12) == 29
    assert days_in_jalali_month(1404, 1) == 31
    assert days_in_jalali_month(1404, 7) == 30


def test_week_starts_on_saturday() -> None:
    """A week starts on Saturday and ends on Friday."""
    saturday = dt.date(2024, 3, 23)
    assert week_start(saturday) == saturday
    assert week_start(dt.date(2024, 3, 24)) == saturday
    assert week_start(dt.date(2024, 3, 29)) == saturday  # Friday belongs to the same week


def test_month_grid_covers_whole_weeks() -> None:
    """The grid starts on Saturday and ends on a Friday."""
    weeks = jalali_month_grid(1403, 1)
    assert weeks[0][0].weekday() == 5  # Saturday
    assert weeks[-1][-1].weekday() == 4  # Friday
    days = [day for week in weeks for day in week]
    assert NAWRUZ_1403 in days
    assert days[0] <= NAWRUZ_1403 <= days[-1]


def test_month_period_bounds() -> None:
    """A Jalali month period covers exactly one Jalali month."""
    start, end = period_bounds("month", dt.date(2024, 8, 5))
    jstart = jalali_of(start)
    assert (jstart.year, jstart.month, jstart.day) == (1403, 5, 1)
    assert (end - start).days + 1 == days_in_jalali_month(1403, 5)
    assert jalali_of(end).day == days_in_jalali_month(1403, 5)


def test_quarter_bounds() -> None:
    """A quarter covers three consecutive Jalali months."""
    start, end = period_bounds("quarter", dt.date(2024, 8, 5))
    jstart = jalali_of(start)
    jend = jalali_of(end)
    assert (jstart.year, jstart.month, jstart.day) == (1403, 4, 1)
    assert (jend.year, jend.month, jend.day) == (1403, 6, 31)
    assert (end - start).days + 1 == 31 * 3


def test_half_and_year_bounds() -> None:
    """Half-years and years follow the Jalali calendar."""
    start, end = period_bounds("half", dt.date(2024, 8, 5))
    assert start == NAWRUZ_1403
    assert jalali_of(end).month == 6

    start, end = period_bounds("year", dt.date(2024, 8, 5))
    assert start == NAWRUZ_1403
    assert end == NAWRUZ_1404 - dt.timedelta(days=1)


def test_previous_period() -> None:
    """The previous period is computed correctly."""
    start, end = period_bounds("month", dt.date(2024, 8, 5))
    prev_start, prev_end = previous_period("month", start, end)
    assert (jalali_of(prev_start).month, jalali_of(prev_start).day) == (4, 1)
    assert (jalali_of(prev_end).month, jalali_of(prev_end).day) == (4, 31)

    start, end = period_bounds("year", dt.date(2024, 8, 5))
    prev_start, prev_end = previous_period("year", start, end)
    assert prev_start == dt.date(2023, 3, 21)
    assert prev_end == dt.date(2024, 3, 19)


def test_previous_quarter_crosses_the_year_boundary() -> None:
    """The first quarter of a year follows the last quarter of the previous one."""
    start, end = period_bounds("quarter", dt.date(2024, 4, 5))
    prev_start, prev_end = previous_period("quarter", start, end)
    assert (jalali_of(prev_start).year, jalali_of(prev_start).month) == (1402, 10)
    assert (jalali_of(prev_end).year, jalali_of(prev_end).month) == (1402, 12)


def test_gregorian_period_mode() -> None:
    """The Gregorian calendar system can be selected."""
    start, end = period_bounds("month", dt.date(2024, 8, 5), calendar_system="gregorian")
    assert start == dt.date(2024, 8, 1)
    assert end == dt.date(2024, 8, 31)
