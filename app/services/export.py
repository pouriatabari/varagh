"""Export everything as JSON."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning import LearningItem, LearningLog, LearningUnit
from app.models.review import Achievement, AchievementTask, Review
from app.models.system import NotificationLog, Setting
from app.models.task import BoardItem, Domain, Task, TaskDomain, TaskNote
from app.models.timing import DailyJournal, TimeEntry


def _iso(value: datetime | date | None) -> str | None:
    """Render a timestamp or a date as an ISO string."""
    return value.isoformat() if value is not None else None


def export_all(session: Session) -> dict[str, Any]:
    """Return the whole database as a JSON-serialisable document."""
    tasks = session.scalars(select(Task).order_by(Task.id.asc())).all()
    domains = session.scalars(select(Domain).order_by(Domain.id.asc())).all()
    links = session.scalars(select(TaskDomain)).all()
    entries = session.scalars(select(TimeEntry).order_by(TimeEntry.id.asc())).all()
    notes = session.scalars(select(TaskNote).order_by(TaskNote.id.asc())).all()
    board_items = session.scalars(select(BoardItem).order_by(BoardItem.id.asc())).all()
    journals = session.scalars(select(DailyJournal).order_by(DailyJournal.date.asc())).all()
    items = session.scalars(select(LearningItem).order_by(LearningItem.id.asc())).all()
    units = session.scalars(select(LearningUnit).order_by(LearningUnit.id.asc())).all()
    logs = session.scalars(select(LearningLog).order_by(LearningLog.id.asc())).all()
    reviews = session.scalars(select(Review).order_by(Review.id.asc())).all()
    achievements = session.scalars(select(Achievement).order_by(Achievement.id.asc())).all()
    achievement_links = session.scalars(select(AchievementTask)).all()
    settings = session.scalars(select(Setting)).all()
    notifications = session.scalars(
        select(NotificationLog).order_by(NotificationLog.id.asc())
    ).all()

    domain_names = {domain.id: domain.name for domain in domains}

    return {
        "exported_at": datetime.now().astimezone().isoformat(),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "description_md": task.description_md,
                "status": task.status,
                "priority": task.priority,
                "origin": task.origin,
                "assigned_by": task.assigned_by,
                "context": task.context,
                "due_at": _iso(task.due_at),
                "effort_minutes_estimate": task.effort_minutes_estimate,
                "started_at": _iso(task.started_at),
                "completed_at": _iso(task.completed_at),
                "created_at": _iso(task.created_at),
                "last_activity_at": _iso(task.last_activity_at),
                "deleted_at": _iso(task.deleted_at),
                "domains": [
                    domain_names[link.domain_id]
                    for link in links
                    if link.task_id == task.id and link.domain_id in domain_names
                ],
            }
            for task in tasks
        ],
        "domains": [{"id": domain.id, "name": domain.name} for domain in domains],
        "time_entries": [
            {
                "id": entry.id,
                "task_id": entry.task_id,
                "learning_item_id": entry.learning_item_id,
                "kind": entry.kind,
                "started_at": _iso(entry.started_at),
                "ended_at": _iso(entry.ended_at),
                "duration_minutes": entry.duration_minutes,
                "is_off_day": entry.is_off_day,
                "reason": entry.reason,
                "note": entry.note,
            }
            for entry in entries
        ],
        "task_notes": [
            {
                "id": note.id,
                "task_id": note.task_id,
                "body_md": note.body_md,
                "created_at": _iso(note.created_at),
            }
            for note in notes
        ],
        "board_items": [
            {
                "id": item.id,
                "task_id": item.task_id,
                "type": item.type,
                "content": item.content,
                "x": item.x,
                "y": item.y,
                "color": item.color,
            }
            for item in board_items
        ],
        "daily_journal": [
            {
                "date": entry.date.isoformat(),
                "raw_text": entry.raw_text,
                "parsed": entry.parsed,
                "confirmed": entry.confirmed,
            }
            for entry in journals
        ],
        "learning_items": [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "author_or_provider": item.author_or_provider,
                "status": item.status,
                "notes_md": item.notes_md,
                "started_at": _iso(item.started_at),
                "finished_at": _iso(item.finished_at),
                "units": [
                    {
                        "id": unit.id,
                        "position": unit.position,
                        "title": unit.title,
                        "done_at": _iso(unit.done_at),
                    }
                    for unit in units
                    if unit.item_id == item.id
                ],
                "logs": [
                    {
                        "id": log.id,
                        "logged_at": _iso(log.logged_at),
                        "minutes": log.minutes,
                        "note": log.note,
                    }
                    for log in logs
                    if log.item_id == item.id
                ],
            }
            for item in items
        ],
        "reviews": [
            {
                "id": review.id,
                "period_type": review.period_type,
                "period_start": review.period_start.isoformat(),
                "period_end": review.period_end.isoformat(),
                "stats": review.stats,
                "ai_draft": review.ai_draft,
                "user_final_md": review.user_final_md,
                "rating": review.rating,
                "created_at": _iso(review.created_at),
            }
            for review in reviews
        ],
        "achievements": [
            {
                "id": achievement.id,
                "title": achievement.title,
                "description_md": achievement.description_md,
                "kind": achievement.kind,
                "period_start": achievement.period_start.isoformat(),
                "period_end": achievement.period_end.isoformat(),
                "impact_note": achievement.impact_note,
                "confirmed": achievement.confirmed,
                "task_ids": [
                    link.task_id
                    for link in achievement_links
                    if link.achievement_id == achievement.id
                ],
            }
            for achievement in achievements
        ],
        "settings": {row.key: row.value for row in settings},
        "notification_log": [
            {
                "id": row.id,
                "kind": row.kind,
                "ref_id": row.ref_id,
                "channel": row.channel,
                "window_key": row.window_key,
                "sent_at": _iso(row.sent_at),
                "delivered_at": _iso(row.delivered_at),
            }
            for row in notifications
        ],
    }
