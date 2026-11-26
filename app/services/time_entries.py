"""Time-entry service — the *measured* layer of the three-layer time model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.task import Task
from app.models.timing import TimeEntry
from app.services import holidays
from app.utils.jalali import jalali_weekday_index

OVERTIME = "overtime"


@dataclass(slots=True)
class OffDayPolicy:
    """Which weekdays count as the weekend."""

    weekend_weekdays: frozenset[int]
    holidays: set[date]


def build_off_day_policy(
    weekend_weekdays: frozenset[int], holiday_dates: set[date] | None = None
) -> OffDayPolicy:
    """Build the policy used to compute ``is_off_day``."""
    return OffDayPolicy(
        weekend_weekdays=weekend_weekdays,
        holidays=holiday_dates if holiday_dates is not None else holidays.holiday_dates(),
    )


def policy_from_settings(session: Session) -> OffDayPolicy:
    """Build the off-day policy from the user's settings."""
    from app.services import settings as settings_service

    return build_off_day_policy(settings_service.weekend_weekdays(session))


def compute_is_off_day(value: date, policy: OffDayPolicy) -> bool:
    """True when the date is a weekend day or a configured holiday."""
    if value in policy.holidays:
        return True
    return jalali_weekday_index(value) in policy.weekend_weekdays


def _duration_minutes(started_at: datetime, ended_at: datetime | None) -> int | None:
    if ended_at is None:
        return None
    delta = ended_at - started_at
    return max(0, int(delta.total_seconds() // 60))


def create_entry(
    session: Session,
    *,
    kind: str,
    started_at: datetime,
    now: datetime,
    ended_at: datetime | None = None,
    duration_minutes: int | None = None,
    task_id: int | None = None,
    learning_item_id: int | None = None,
    reason: str | None = None,
    note: str | None = None,
    policy: OffDayPolicy | None = None,
) -> TimeEntry:
    """Create a measured time entry.

    ``kind='overtime'`` requires a non-empty reason — the constraint is also
    enforced by the database.
    """
    if kind == OVERTIME and not (reason or "").strip():
        raise ValueError("overtime_reason_required")
    if ended_at is not None and duration_minutes is None:
        duration_minutes = _duration_minutes(started_at, ended_at)
    if duration_minutes is None and ended_at is None:
        raise ValueError("duration_minutes_required")
    if duration_minutes is not None and duration_minutes < 0:
        raise ValueError("duration_non_negative")

    off_day_policy = policy or build_off_day_policy(frozenset({6}))
    entry = TimeEntry(
        task_id=task_id,
        learning_item_id=learning_item_id,
        kind=kind,
        started_at=started_at,
        ended_at=ended_at,
        duration_minutes=duration_minutes,
        reason=(reason or None),
        note=(note or None),
        is_off_day=compute_is_off_day(started_at.date(), off_day_policy),
        created_at=now,
    )
    session.add(entry)
    session.flush()
    return entry


def get_entry(session: Session, entry_id: int) -> TimeEntry | None:
    """Return a time entry by id."""
    return session.get(TimeEntry, entry_id)


def delete_entry(session: Session, entry: TimeEntry) -> None:
    """Delete a time entry."""
    session.delete(entry)
    session.flush()


def list_entries(
    session: Session,
    *,
    start: datetime | None = None,
    end: datetime | None = None,
    task_id: int | None = None,
    learning_item_id: int | None = None,
    kind: str | None = None,
) -> list[TimeEntry]:
    """Return time entries filtered by time range and/or related object."""
    query = select(TimeEntry).order_by(TimeEntry.started_at.desc())
    if start is not None:
        query = query.where(TimeEntry.started_at >= start)
    if end is not None:
        query = query.where(TimeEntry.started_at < end)
    if task_id is not None:
        query = query.where(TimeEntry.task_id == task_id)
    if learning_item_id is not None:
        query = query.where(TimeEntry.learning_item_id == learning_item_id)
    if kind is not None:
        query = query.where(TimeEntry.kind == kind)
    return list(session.scalars(query).all())


def list_entries_for_day(session: Session, day: date) -> list[TimeEntry]:
    """Return the entries that started on the given Gregorian day."""
    start = datetime(day.year, day.month, day.day, tzinfo=UTC)
    end = start + timedelta(days=1)
    return list_entries(session, start=start, end=end)


def minutes_by_day(session: Session, start: date, end: date) -> dict[date, int]:
    """Return measured minutes per day for the inclusive date range."""
    start_dt = datetime(start.year, start.month, start.day, tzinfo=UTC)
    end_dt = datetime(end.year, end.month, end.day, tzinfo=UTC) + timedelta(days=1)
    entries = list_entries(session, start=start_dt, end=end_dt)
    totals: dict[date, int] = {}
    for entry in entries:
        if entry.duration_minutes is None:
            continue
        day = entry.started_at.date()
        totals[day] = totals.get(day, 0) + entry.duration_minutes
    return totals


def totals_by_kind(session: Session, start: datetime, end: datetime) -> dict[str, int]:
    """Return measured minutes grouped by entry kind."""
    totals: dict[str, int] = {}
    for entry in list_entries(session, start=start, end=end):
        if entry.duration_minutes is None:
            continue
        totals[entry.kind] = totals.get(entry.kind, 0) + entry.duration_minutes
    return totals


def running_entry(session: Session) -> TimeEntry | None:
    """Return the currently running timer (an entry without ``ended_at``)."""
    query = (
        select(TimeEntry)
        .where(TimeEntry.ended_at.is_(None))
        .order_by(TimeEntry.started_at.desc())
        .limit(1)
    )
    return session.scalars(query).first()


def start_timer(
    session: Session,
    *,
    now: datetime,
    kind: str = "work",
    task_id: int | None = None,
    learning_item_id: int | None = None,
    reason: str | None = None,
    policy: OffDayPolicy | None = None,
) -> TimeEntry:
    """Start a running timer."""
    if kind == OVERTIME and not (reason or "").strip():
        raise ValueError("overtime_reason_required")
    off_day_policy = policy or build_off_day_policy(frozenset({6}))
    entry = TimeEntry(
        task_id=task_id,
        learning_item_id=learning_item_id,
        kind=kind,
        started_at=now,
        ended_at=None,
        duration_minutes=None,
        reason=(reason or None),
        is_off_day=compute_is_off_day(now.date(), off_day_policy),
        created_at=now,
    )
    session.add(entry)
    session.flush()
    return entry


def stop_timer(session: Session, entry: TimeEntry, now: datetime) -> TimeEntry:
    """Stop a running timer and freeze its duration."""
    entry.ended_at = now
    entry.duration_minutes = _duration_minutes(entry.started_at, now) or 0
    session.flush()
    return entry


def measured_minutes_for_task(session: Session, task_id: int) -> int:
    """Return the total measured minutes recorded against a task."""
    entries = list_entries(session, task_id=task_id)
    return sum(entry.duration_minutes or 0 for entry in entries)


def task_hours_basis(task: Task, session: Session) -> dict[str, int | None]:
    """Return the three honest time layers for a single task."""
    measured = measured_minutes_for_task(session, task.id)
    elapsed: int | None = None
    if task.completed_at is not None:
        start = task.started_at or task.created_at
        elapsed = max(0, int((task.completed_at - start).total_seconds() // 60))
    return {
        "measured_minutes": measured,
        "estimated_minutes": task.effort_minutes_estimate,
        "elapsed_minutes": elapsed,
    }
