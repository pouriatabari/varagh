"""Reviews, the period comparison and the achievements."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import achievements as achievement_service
from app.services import reviews as review_service
from app.services import tasks as task_service
from app.services import time_entries as time_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)
TIMEZONE = "Asia/Tehran"


def _period(start: dt.date, end: dt.date) -> review_service.PeriodSelection:
    """Build a period selection for the tests."""
    return review_service.PeriodSelection("custom", start, end)


def test_stats_use_measured_entries_only(session: Session) -> None:
    """The statistics count the measured minutes, never the estimates."""
    task = task_service.create_task(session, title="تسک", now=NOW, effort_minutes_estimate=600)
    time_service.create_entry(
        session, kind="work", started_at=NOW, now=NOW, duration_minutes=90, task_id=task.id
    )
    stats = review_service.compute_stats(
        session, start=NOW.date(), end=NOW.date(), timezone=TIMEZONE
    )
    assert stats["measured_minutes_total"] == 90
    assert stats["measured_minutes_by_kind"] == {"work": 90}
    assert stats["estimated_minutes_total"] == 600
    assert stats["basis"]["measured"] == "time_entries"


def test_overtime_is_split_by_off_day(session: Session) -> None:
    """The overtime is split into the off-day and the regular-day part."""
    friday = dt.datetime(2024, 8, 2, 9, 0, tzinfo=dt.UTC)  # a Friday
    monday = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)
    for moment in (friday, monday):
        time_service.create_entry(
            session,
            kind="overtime",
            started_at=moment,
            now=moment,
            duration_minutes=60,
            reason="کار فوری",
        )
    stats = review_service.compute_stats(
        session, start=dt.date(2024, 8, 1), end=dt.date(2024, 8, 5), timezone=TIMEZONE
    )
    overtime = stats["overtime"]
    assert overtime["off_day_minutes"] == 60
    assert overtime["regular_day_minutes"] == 60
    assert overtime["reasons"] == {"کار فوری": 120}


def test_the_snapshot_is_immutable(session: Session) -> None:
    """A saved review keeps the statistics it was created with."""
    period = _period(dt.date(2024, 8, 1), dt.date(2024, 8, 31))
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone=TIMEZONE
    )
    review = review_service.create_review(session, period=period, stats=stats)
    time_service.create_entry(session, kind="work", started_at=NOW, now=NOW, duration_minutes=120)
    session.refresh(review)
    assert review.stats["measured_minutes_total"] == 0


def test_comparison_against_the_previous_period(session: Session) -> None:
    """A review is compared with the review of the previous period."""
    first = _period(dt.date(2024, 7, 1), dt.date(2024, 7, 31))
    first_stats = review_service.compute_stats(
        session, start=first.start, end=first.end, timezone=TIMEZONE
    )
    first_stats["measured_minutes_total"] = 100
    previous = review_service.create_review(session, period=first, stats=first_stats)

    second = _period(dt.date(2024, 8, 1), dt.date(2024, 8, 31))
    second_stats = review_service.compute_stats(
        session, start=second.start, end=second.end, timezone=TIMEZONE
    )
    second_stats["measured_minutes_total"] = 250
    current = review_service.create_review(session, period=second, stats=second_stats)

    found = review_service.find_previous_review(session, current)
    assert found is not None
    assert found.id == previous.id
    comparison = review_service.compare_stats(current.stats, found.stats)
    assert comparison["has_previous"] is True
    measured = next(row for row in comparison["rows"] if row["label"] == "زمان اندازه‌گیری‌شده")
    assert measured["current"] == 250
    assert measured["previous"] == 100
    assert measured["delta"] == 150


def test_comparison_without_a_previous_review(session: Session) -> None:
    """A first review has nothing to compare with."""
    period = _period(dt.date(2024, 8, 1), dt.date(2024, 8, 31))
    review = review_service.create_review(session, period=period, stats={"counts": {}})
    comparison = review_service.compare_stats(review.stats, None)
    assert comparison["has_previous"] is False
    assert comparison["rows"] == []


def test_export_markdown_contains_the_figures(session: Session) -> None:
    """The Markdown export carries the numbers of the snapshot."""
    period = _period(dt.date(2024, 8, 1), dt.date(2024, 8, 31))
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone=TIMEZONE
    )
    review = review_service.create_review(
        session, period=period, stats=stats, user_final_md="ماه خوبی بود.", rating=4
    )
    markdown = review_service.export_markdown(review)
    assert "# ارزیابی" in markdown
    assert "ماه خوبی بود." in markdown
    assert "4" in markdown


def test_achievements_are_grounded_in_tasks(session: Session) -> None:
    """An achievement links to the tasks that prove it."""
    task = task_service.create_task(session, title="تسک انجام‌شده", now=NOW)
    achievement = achievement_service.create_achievement(
        session,
        title="پیاده‌سازی قابلیت جدید",
        kind="technical",
        period_start=NOW.date(),
        period_end=NOW.date(),
        task_ids=[task.id, 9999],
    )
    linked = achievement_service.linked_task_ids(session, achievement)
    assert linked == [task.id]
    markdown = achievement_service.export_markdown(session, achievement)
    assert "پیاده‌سازی قابلیت جدید" in markdown
    assert "تسک انجام‌شده" in markdown


def test_review_pages_render(client: TestClient) -> None:
    """The review and achievement pages render."""
    assert client.get("/reviews").status_code == 200
    assert client.get("/reviews/new").status_code == 200
    assert client.get("/achievements").status_code == 200


def test_review_route_saves_the_snapshot(client: TestClient) -> None:
    """Saving a review stores the statistics of the period."""
    response = client.post(
        "/reviews",
        data={"period_type": "month", "user_final_md": "متن", "rating": "3"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    review_id = int(location.rsplit("/", 1)[-1].split("?")[0])
    detail = client.get(f"/reviews/{review_id}")
    assert detail.status_code == 200
    assert "متن" in detail.text
    export = client.get(f"/reviews/{review_id}/export.md")
    assert export.status_code == 200
    assert "ارزیابی" in export.text
