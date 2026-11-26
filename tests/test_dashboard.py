"""Dashboard statistics and page tests."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import dashboard as dashboard_service
from app.services import tasks as task_service
from app.services import time_entries as time_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def test_counts_overdue_today_and_done(session: Session) -> None:
    """The dashboard counts the open, overdue and finished tasks."""
    overdue = task_service.create_task(
        session, title="تأخیردار", now=NOW, due_at=NOW - dt.timedelta(days=3)
    )
    today = task_service.create_task(
        session, title="امروز", now=NOW, due_at=dt.datetime(2024, 8, 5, 12, 0, tzinfo=dt.UTC)
    )
    done = task_service.create_task(session, title="انجام‌شده", now=NOW)
    task_service.set_status(session, done, "done", NOW)

    stats = dashboard_service.collect_stats(session, now=NOW, timezone="Asia/Tehran")
    assert stats.overdue_count == 1
    assert stats.today_count == 1
    assert stats.open_count == 2
    assert stats.done_this_week == 1
    assert overdue.id != today.id


def test_hours_by_kind_use_measured_entries_only(session: Session) -> None:
    """The chart is built from measured time entries only."""
    time_service.create_entry(session, kind="work", started_at=NOW, now=NOW, duration_minutes=120)
    time_service.create_entry(session, kind="study", started_at=NOW, now=NOW, duration_minutes=45)
    task_service.create_task(session, title="تخمینی", now=NOW, effort_minutes_estimate=600)
    stats = dashboard_service.collect_stats(session, now=NOW, timezone="Asia/Tehran")
    assert stats.hours_by_kind == {"work": 120, "study": 45}
    assert stats.weekly_measured_minutes == 165


def test_streak_counts_consecutive_active_days(session: Session) -> None:
    """The streak counts consecutive days with activity."""
    for offset in range(3):
        time_service.create_entry(
            session,
            kind="work",
            started_at=NOW - dt.timedelta(days=offset),
            now=NOW,
            duration_minutes=30,
        )
    stats = dashboard_service.collect_stats(session, now=NOW, timezone="Asia/Tehran")
    assert stats.streak_days == 3


def test_heatmap_has_ninety_days(session: Session) -> None:
    """The heatmap covers the last 90 days."""
    stats = dashboard_service.collect_stats(session, now=NOW, timezone="Asia/Tehran")
    assert len(stats.heatmap) == 90
    assert stats.heatmap[-1]["minutes"] == 0


def test_dashboard_page_renders_the_chart(client: TestClient) -> None:
    """The dashboard renders the Chart.js canvas and the counters."""
    response = client.get("/")
    assert response.status_code == 200
    assert "hours-chart" in response.text
    assert "داشبورد" in response.text
