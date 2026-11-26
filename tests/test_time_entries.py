"""Time-entry, off-day, calendar and journal tests."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import holidays
from app.services import tasks as task_service
from app.services import time_entries as time_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)
FRIDAY = dt.date(2024, 8, 2)
MONDAY = dt.date(2024, 8, 5)


@pytest.fixture(autouse=True)
def _isolated_holidays(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the holiday file at a temporary directory for every test."""
    path = tmp_path / "holidays_jalali.json"
    path.write_text('{"holidays": []}', encoding="utf-8")
    monkeypatch.setattr(holidays, "holidays_path", lambda: path)
    return path


def test_overtime_requires_a_reason(session: Session) -> None:
    """Overtime without a reason is refused by the service."""
    with pytest.raises(ValueError, match="overtime_reason_required"):
        time_service.create_entry(
            session, kind="overtime", started_at=NOW, now=NOW, duration_minutes=60
        )


def test_overtime_with_a_reason_is_stored(session: Session) -> None:
    """Overtime with a reason keeps the reason."""
    entry = time_service.create_entry(
        session,
        kind="overtime",
        started_at=NOW,
        now=NOW,
        duration_minutes=60,
        reason="تحویل فوری",
    )
    assert entry.reason == "تحویل فوری"


def test_friday_is_an_off_day(session: Session) -> None:
    """Friday counts as the weekly day off."""
    policy = time_service.build_off_day_policy(frozenset({6}), set())
    assert time_service.compute_is_off_day(FRIDAY, policy) is True
    assert time_service.compute_is_off_day(MONDAY, policy) is False


def test_configured_holidays_are_off_days() -> None:
    """A holiday added to the JSON file becomes an off day."""
    added = holidays.add_holiday("1403/05/14", "تعطیلی آزمایشی")
    assert added is not None
    gregorian = added.gregorian
    assert gregorian is not None
    policy = time_service.build_off_day_policy(frozenset(), holidays.holiday_dates())
    assert time_service.compute_is_off_day(gregorian, policy) is True
    assert holidays.remove_holiday("1403/05/14") is True
    assert holidays.holiday_dates() == set()


def test_invalid_holiday_date_is_rejected() -> None:
    """An unparsable holiday date is refused."""
    assert holidays.add_holiday("not-a-date") is None
    assert holidays.remove_holiday("not-a-date") is False


def test_manual_entry_uses_the_given_duration(session: Session) -> None:
    """A manual entry keeps the duration the user typed."""
    entry = time_service.create_entry(
        session, kind="work", started_at=NOW, now=NOW, duration_minutes=90
    )
    assert entry.duration_minutes == 90
    assert entry.ended_at is None


def test_entry_duration_is_derived_from_start_and_end(session: Session) -> None:
    """When both ends are given the duration is computed."""
    entry = time_service.create_entry(
        session,
        kind="work",
        started_at=NOW,
        ended_at=NOW + dt.timedelta(minutes=45),
        now=NOW,
    )
    assert entry.duration_minutes == 45


def test_timer_start_and_stop(session: Session) -> None:
    """The running timer is found and stopped."""
    entry = time_service.start_timer(session, now=NOW, kind="work")
    assert time_service.running_entry(session) is entry
    time_service.stop_timer(session, entry, NOW + dt.timedelta(minutes=30))
    assert entry.duration_minutes == 30
    assert time_service.running_entry(session) is None


def test_minutes_by_day_groups_the_entries(session: Session) -> None:
    """Measured minutes are grouped per day."""
    time_service.create_entry(session, kind="work", started_at=NOW, now=NOW, duration_minutes=60)
    time_service.create_entry(
        session,
        kind="study",
        started_at=NOW + dt.timedelta(days=1),
        now=NOW,
        duration_minutes=30,
    )
    totals = time_service.minutes_by_day(
        session, MONDAY - dt.timedelta(days=1), MONDAY + dt.timedelta(days=3)
    )
    assert totals[MONDAY] == 60
    assert totals[MONDAY + dt.timedelta(days=1)] == 30


def test_task_time_basis_reports_all_three_layers(session: Session) -> None:
    """A task exposes measured, estimated and elapsed minutes separately."""
    task = task_service.create_task(
        session,
        title="تسک زمان",
        now=NOW,
        effort_minutes_estimate=120,
    )
    time_service.create_entry(
        session, kind="work", started_at=NOW, now=NOW, duration_minutes=45, task_id=task.id
    )
    task_service.set_status(session, task, "done", NOW + dt.timedelta(hours=3))
    basis = time_service.task_hours_basis(task, session)
    assert basis["measured_minutes"] == 45
    assert basis["estimated_minutes"] == 120
    assert basis["elapsed_minutes"] == 180


def test_calendar_page_renders_the_grid(client: TestClient) -> None:
    """The calendar page shows the Jalali month grid."""
    response = client.get("/calendar")
    assert response.status_code == 200
    assert "calendar-grid" in response.text


def test_calendar_shows_the_measured_total(client: TestClient, session: Session) -> None:
    """A measured entry shows up as the day's total."""
    time_service.create_entry(session, kind="work", started_at=NOW, now=NOW, duration_minutes=125)
    response = client.get("/calendar?year=1403&month=5")
    assert response.status_code == 200
    assert "ساعت و" in response.text


def test_manual_entry_route(client: TestClient, session: Session) -> None:
    """A manual entry can be added from the calendar."""
    response = client.post(
        "/time/entries",
        data={
            "date": "1403/05/14",
            "start_time": "09:00",
            "duration_minutes": "45",
            "kind": "work",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    entries = time_service.list_entries(session)
    assert len(entries) == 1
    assert entries[0].duration_minutes == 45


def test_overtime_route_requires_a_reason(client: TestClient, session: Session) -> None:
    """The calendar refuses overtime without a reason."""
    response = client.post(
        "/time/entries",
        data={
            "date": "1403/05/11",
            "start_time": "09:00",
            "duration_minutes": "60",
            "kind": "overtime",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=time.overtime_reason_required" in response.headers["location"]
    assert time_service.list_entries(session) == []


def test_journal_page_and_manual_entry(client: TestClient, session: Session) -> None:
    """The daily journal stores free Persian text without any AI."""
    response = client.post(
        "/journal",
        data={"date": "1403/05/14", "raw_text": "امروز روی گرافانا کار کردم، حدود ۳ ساعت"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    page = client.get("/journal")
    assert page.status_code == 200
    assert "گرافانا" in page.text


def test_done_prompt_appears_after_completing_a_task(client: TestClient, session: Session) -> None:
    """Completing a task asks roughly how long it took."""
    task = task_service.create_task(session, title="تقریباً", now=NOW)
    response = client.post(
        f"/tasks/{task.id}/status", data={"status": "done"}, follow_redirects=False
    )
    assert response.status_code == 303
    assert "prompt=hours" in response.headers["location"]
    page = client.get(f"/tasks/{task.id}?prompt=hours")
    assert "تقریباً چند ساعت؟" in page.text


def test_estimate_route_records_the_estimate(client: TestClient, session: Session) -> None:
    """The reported duration is stored as the task's estimate."""
    task = task_service.create_task(session, title="تخمین", now=NOW)
    response = client.post(
        f"/tasks/{task.id}/estimate",
        data={"minutes": "150", "note": "تقریباً"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert task.effort_minutes_estimate == 150
