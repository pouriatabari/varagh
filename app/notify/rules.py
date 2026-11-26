"""The notification rules.

Every rule produces notifications with a ``window_key``; the de-duplication in
``notification_log`` makes sure the same window never fires twice.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.system import NotificationLog
from app.models.task import Task
from app.models.timing import DailyJournal
from app.notify.channels import Channel, build_channels
from app.notify.messages import Notification
from app.services import learning as learning_service
from app.services import time_entries as time_service
from app.utils.jalali import period_bounds
from app.utils.time import to_local

logger = logging.getLogger("varagh.notify.rules")

KIND_DUE_SOON = "due_soon"
KIND_OVERDUE = "overdue"
KIND_DIGEST = "daily_digest"
KIND_JOURNAL = "journal_nudge"
KIND_REVIEW = "review_reminder"
KIND_STALE_LEARNING = "stale_learning"


def _open_tasks(session: Session) -> list[Task]:
    """Return the tasks that are still open."""
    query = select(Task).where(Task.deleted_at.is_(None), Task.status.in_(("todo", "doing")))
    return list(session.scalars(query).all())


def _due_soon(session: Session, *, now: datetime, minutes: int) -> list[Notification]:
    """Tasks whose deadline is close."""
    if minutes <= 0:
        return []
    limit = now + timedelta(minutes=minutes)
    notifications = []
    for task in _open_tasks(session):
        if task.due_at is None or not (now <= task.due_at <= limit):
            continue
        notifications.append(
            Notification(
                kind=KIND_DUE_SOON,
                ref_id=task.id,
                title="تسک نزدیک مهلت",
                body=f"«{task.title}» تا {int(minutes)} دقیقه دیگر مهلت دارد.",
                window_key=f"due-{task.due_at.isoformat()}",
                url=f"/tasks/{task.id}",
            )
        )
    return notifications


def _overdue(session: Session, *, now: datetime, local_date: str) -> list[Notification]:
    """Tasks that are past their deadline."""
    notifications = []
    for task in _open_tasks(session):
        if task.due_at is None or task.due_at >= now:
            continue
        notifications.append(
            Notification(
                kind=KIND_OVERDUE,
                ref_id=task.id,
                title="تسک تأخیردار",
                body=f"«{task.title}» از مهلتش گذشته است.",
                window_key=f"overdue-{local_date}",
                url=f"/tasks/{task.id}",
            )
        )
    return notifications


def _daily_digest(
    session: Session, *, now: datetime, timezone: str, local_date: str
) -> list[Notification]:
    """The daily summary, sent once a day at the configured time."""
    totals = time_service.totals_by_kind(session, now - timedelta(days=1), now + timedelta(days=1))
    parts = [f"{kind}: {minutes} دقیقه" for kind, minutes in sorted(totals.items())]
    body = "، ".join(parts) if parts else "امروز هنوز زمانی ثبت نشده است."
    return [
        Notification(
            kind=KIND_DIGEST,
            ref_id=0,
            title="خلاصهٔ روز",
            body=body,
            window_key=f"digest-{local_date}",
            url="/",
        )
    ]


def _journal_nudge(
    session: Session, *, now: datetime, local_date: str, day: Any
) -> list[Notification]:
    """The end-of-day nudge to write the journal."""
    existing = session.scalars(select(DailyJournal).where(DailyJournal.date == day)).first()
    if existing is not None:
        return []
    return [
        Notification(
            kind=KIND_JOURNAL,
            ref_id=0,
            title="ژورنال روزانه",
            body="دیدت چه کردی؟ چند خط فارسی بنویس.",
            window_key=f"journal-{local_date}",
            url="/journal",
        )
    ]


def _review_reminder(
    session: Session,
    *,
    now: datetime,
    timezone: str,
    calendar_system: str,
    period_type: str = "month",
    days_before_end: int = 3,
) -> list[Notification]:
    """Remind the user to write the period review before the period ends."""
    start, end = period_bounds(period_type, now.date(), calendar_system)
    remaining = (end - now.date()).days
    if remaining > days_before_end or remaining < 0:
        return []
    existing = session.scalars(
        select(Review).where(
            Review.period_type == period_type,
            Review.period_start == start,
            Review.period_end == end,
        )
    ).first()
    if existing is not None:
        return []
    return [
        Notification(
            kind=KIND_REVIEW,
            ref_id=0,
            title="ارزیابی دوره",
            body=f"دورهٔ {period_type} رو به پایان است؛ وقت ارزیابی است.",
            window_key=f"review-{period_type}-{start.isoformat()}",
            url="/reviews/new",
        )
    ]


def _stale_learning(
    session: Session, *, now: datetime, threshold_days: int, local_date: str
) -> list[Notification]:
    """Learning items that have not been touched for a while."""
    if threshold_days <= 0:
        return []
    notifications = []
    for item, _progress in learning_service.stale_items(
        session, threshold_days=threshold_days, now=now
    ):
        notifications.append(
            Notification(
                kind=KIND_STALE_LEARNING,
                ref_id=item.id,
                title="یادگیری راکد",
                body=f"«{item.title}» مدتی است جلو نرفته.",
                window_key=f"stale-{item.id}-{local_date[:7]}",
                url=f"/learning/{item.id}",
            )
        )
    return notifications


def _passed_time(now: datetime, timezone: str, hhmm: str) -> bool:
    """True when the local wall-clock time is at or after ``hhmm``."""
    local = to_local(now, timezone)
    try:
        raw_hour, _, raw_minute = hhmm.partition(":")
        hour, minute = int(raw_hour), int(raw_minute or 0)
    except ValueError:
        return False
    return (local.hour, local.minute) >= (hour, minute)


def collect_notifications(
    session: Session,
    *,
    now: datetime,
    timezone: str,
    config: dict[str, Any],
    calendar_system: str = "jalali",
) -> list[Notification]:
    """Collect every notification the rules want to raise right now."""
    local = to_local(now, timezone)
    local_date = local.date().isoformat()
    notifications: list[Notification] = []

    if config.get("due_soon_minutes"):
        notifications += _due_soon(session, now=now, minutes=int(config.get("due_soon_minutes", 0)))
    if config.get("overdue_enabled", True):
        notifications += _overdue(session, now=now, local_date=local_date)
    if config.get("digest_enabled", True) and _passed_time(
        now, timezone, str(config.get("digest_time", "20:00"))
    ):
        notifications += _daily_digest(session, now=now, timezone=timezone, local_date=local_date)
    if config.get("journal_nudge_enabled", True) and _passed_time(
        now, timezone, str(config.get("journal_nudge_time", "21:30"))
    ):
        notifications += _journal_nudge(session, now=now, local_date=local_date, day=local.date())
    if config.get("review_reminder_enabled", True):
        notifications += _review_reminder(
            session,
            now=now,
            timezone=timezone,
            calendar_system=calendar_system,
        )
    if config.get("stale_learning_enabled", True):
        notifications += _stale_learning(
            session,
            now=now,
            threshold_days=int(config.get("stale_learning_days", 30)),
            local_date=local_date,
        )
    return notifications


def dispatch(
    session: Session,
    *,
    now: datetime,
    timezone: str,
    config: dict[str, Any],
    calendar_system: str = "jalali",
) -> int:
    """Deliver the pending notifications on every enabled channel."""
    notifications = collect_notifications(
        session,
        now=now,
        timezone=timezone,
        config=config,
        calendar_system=calendar_system,
    )
    if not notifications:
        return 0
    channels: list[Channel] = build_channels(session, now, config)
    sent = 0
    for notification in notifications:
        for channel in channels:
            try:
                if channel.send(notification):
                    sent += 1
            except Exception:  # a broken channel must not stop the others
                logger.exception("notification channel %s failed", channel.name)
    return sent


def pending_browser_notifications(session: Session) -> list[Notification]:
    """Return the notifications the browser has not picked up yet."""
    query = (
        select(NotificationLog)
        .where(
            NotificationLog.channel == "browser",
            NotificationLog.delivered_at.is_(None),
        )
        .order_by(NotificationLog.sent_at.asc())
    )
    rows = session.scalars(query).all()
    notifications = []
    for row in rows:
        payload = row.payload or {}
        notifications.append(
            Notification(
                kind=row.kind,
                ref_id=row.ref_id,
                title=str(payload.get("title", row.kind)),
                body=str(payload.get("body", "")),
                window_key=row.window_key,
                url=str(payload.get("url", "/")),
            )
        )
    return notifications
