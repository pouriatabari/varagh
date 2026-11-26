"""Dashboard statistics.

Every number here states its basis: measured minutes come from ``time_entries``,
elapsed minutes from the task timestamps, and estimated minutes from the
estimates the user wrote down.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.services import time_entries as time_service
from app.utils.jalali import week_start
from app.utils.time import to_local

HEATMAP_DAYS = 90


@dataclass(slots=True)
class DashboardStats:
    """Everything the dashboard needs."""

    overdue_count: int = 0
    today_count: int = 0
    done_this_week: int = 0
    open_count: int = 0
    hours_by_kind: dict[str, int] = field(default_factory=dict)
    weekly_measured_minutes: int = 0
    weekly_target_minutes: int = 0
    weekly_elapsed_minutes: int = 0
    heatmap: list[dict[str, object]] = field(default_factory=list)
    streak_days: int = 0
    basis_note: str = ""


def _week_bounds(now: datetime, timezone: str) -> tuple[datetime, datetime]:
    """Return the UTC bounds of the Jalali week containing ``now``."""
    local = to_local(now, timezone)
    first_day = week_start(local.date())
    start_local = datetime(first_day.year, first_day.month, first_day.day, tzinfo=local.tzinfo)
    return start_local.astimezone(now.tzinfo), (start_local + timedelta(days=7)).astimezone(
        now.tzinfo
    )


def collect_stats(
    session: Session,
    *,
    now: datetime,
    timezone: str = "Asia/Tehran",
    weekly_target_hours: int = 40,
) -> DashboardStats:
    """Collect the dashboard numbers."""
    stats = DashboardStats()
    local_now = to_local(now, timezone)
    start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    open_tasks = list(
        session.scalars(
            select(Task).where(Task.deleted_at.is_(None), Task.status.in_(("todo", "doing")))
        ).all()
    )
    stats.open_count = len(open_tasks)
    stats.overdue_count = sum(
        1 for task in open_tasks if task.due_at is not None and task.due_at < now
    )
    stats.today_count = sum(
        1
        for task in open_tasks
        if task.due_at is not None and start_of_day <= task.due_at < end_of_day
    )

    week_start_utc, week_end_utc = _week_bounds(now, timezone)
    completed = session.scalars(
        select(Task).where(
            Task.deleted_at.is_(None),
            Task.completed_at.is_not(None),
            Task.completed_at >= week_start_utc,
            Task.completed_at < week_end_utc,
        )
    ).all()
    stats.done_this_week = len(completed)

    entries = time_service.list_entries(session, start=week_start_utc, end=week_end_utc)
    for entry in entries:
        minutes = entry.duration_minutes or 0
        stats.hours_by_kind[entry.kind] = stats.hours_by_kind.get(entry.kind, 0) + minutes
        stats.weekly_measured_minutes += minutes

    stats.weekly_target_minutes = max(0, weekly_target_hours) * 60
    for task in completed:
        if task.started_at and task.completed_at:
            delta = task.completed_at - task.started_at
            stats.weekly_elapsed_minutes += max(0, int(delta.total_seconds() // 60))

    stats.heatmap, stats.streak_days = _activity_heatmap(session, now=now, timezone=timezone)
    return stats


def _activity_heatmap(
    session: Session, *, now: datetime, timezone: str
) -> tuple[list[dict[str, object]], int]:
    """Return the activity heatmap of the last 90 days and the current streak."""
    local_now = to_local(now, timezone)
    today = local_now.date()
    first_day = today - timedelta(days=HEATMAP_DAYS - 1)

    minutes = time_service.minutes_by_day(session, first_day, today)
    activity_days: set[date] = set(minutes)

    tasks = session.scalars(select(Task).where(Task.last_activity_at.is_not(None))).all()
    for task in tasks:
        if task.last_activity_at is not None:
            activity_days.add(to_local(task.last_activity_at, timezone).date())

    peak = max(minutes.values(), default=0)
    cells: list[dict[str, object]] = []
    for offset in range(HEATMAP_DAYS):
        day = first_day + timedelta(days=offset)
        day_minutes = minutes.get(day, 0)
        level = 0
        if day_minutes > 0:
            level = 1 if peak <= 60 else min(4, 1 + int(day_minutes / peak * 3))
        cells.append({"date": day, "minutes": day_minutes, "level": level})

    streak = 0
    cursor = today
    while cursor in activity_days:
        streak += 1
        cursor -= timedelta(days=1)
    return cells, streak
