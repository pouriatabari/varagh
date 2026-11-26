"""Achievements: what was accomplished, grounded in concrete tasks."""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Achievement, AchievementTask
from app.models.task import Task

VALID_KINDS = ("technical", "work", "personal", "learning")


def list_achievements(
    session: Session, kind: str | None = None, period_start: date | None = None
) -> list[Achievement]:
    """Return the achievements, newest first."""
    query = select(Achievement).order_by(Achievement.period_end.desc(), Achievement.id.desc())
    if kind:
        query = query.where(Achievement.kind == kind)
    if period_start is not None:
        query = query.where(Achievement.period_start == period_start)
    return list(session.scalars(query).all())


def get_achievement(session: Session, achievement_id: int) -> Achievement | None:
    """Return an achievement by id."""
    return session.get(Achievement, achievement_id)


def create_achievement(
    session: Session,
    *,
    title: str,
    description_md: str = "",
    kind: str = "technical",
    period_start: date,
    period_end: date,
    impact_note: str | None = None,
    task_ids: list[int] | None = None,
    confirmed: bool = False,
) -> Achievement:
    """Create an achievement and link it to the tasks that prove it.

    Unknown task ids are rejected: an achievement must be grounded in tasks
    that really exist.
    """
    achievement = Achievement(
        title=title.strip(),
        description_md=description_md,
        kind=kind if kind in VALID_KINDS else "technical",
        period_start=period_start,
        period_end=period_end,
        impact_note=impact_note,
        confirmed=confirmed,
    )
    session.add(achievement)
    session.flush()
    if task_ids:
        link_tasks(session, achievement, task_ids)
    return achievement


def link_tasks(session: Session, achievement: Achievement, task_ids: list[int]) -> list[Task]:
    """Link an achievement to the tasks that ground it."""
    if not task_ids:
        return []
    tasks = session.scalars(select(Task).where(Task.id.in_(task_ids))).all()
    existing = {
        link.task_id
        for link in session.scalars(
            select(AchievementTask).where(AchievementTask.achievement_id == achievement.id)
        ).all()
    }
    for task in tasks:
        if task.id in existing:
            continue
        session.add(AchievementTask(achievement_id=achievement.id, task_id=task.id))
    session.flush()
    return list(tasks)


def linked_task_ids(session: Session, achievement: Achievement) -> list[int]:
    """Return the ids of the tasks linked to an achievement."""
    query = select(AchievementTask.task_id).where(AchievementTask.achievement_id == achievement.id)
    return list(session.scalars(query).all())


def confirm(session: Session, achievement: Achievement) -> Achievement:
    """Mark an achievement as confirmed."""
    achievement.confirmed = True
    session.flush()
    return achievement


def export_markdown(session: Session, achievement: Achievement) -> str:
    """Render the achievement as Markdown."""
    task_ids = linked_task_ids(session, achievement)
    lines = [
        f"# {achievement.title}",
        "",
        f"- دسته: {achievement.kind}",
        f"- بازه: {achievement.period_start} تا {achievement.period_end}",
    ]
    if achievement.impact_note:
        lines.append(f"- اثر: {achievement.impact_note}")
    if achievement.description_md.strip():
        lines += ["", achievement.description_md.strip()]
    if task_ids:
        lines += ["", "## تسک‌های مرتبط", ""]
        for task_id in task_ids:
            task = session.get(Task, task_id)
            if task is not None:
                lines.append(f"- {task.title} (#{task.id})")
    return "\n".join(lines) + "\n"
