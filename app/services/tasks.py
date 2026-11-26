"""Task service: CRUD, quick-add, filters, soft delete, notes and domains."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.models.task import Domain, Task, TaskDomain, TaskNote
from app.utils.jalali import week_start
from app.utils.time import to_local, utcnow

OPEN_STATUSES = ("todo", "doing")


@dataclass(slots=True)
class TaskFilters:
    """Declarative filters for :func:`list_tasks`."""

    q: str | None = None
    status: str | None = None
    origin: str | None = None
    context: str | None = None
    domain_id: int | None = None
    due: str | None = None
    include_deleted: bool = False
    order_by: str = "created_at"
    descending: bool = True
    limit: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)


def _base_query(filters: TaskFilters) -> Select[tuple[Task]]:
    query = select(Task)
    if not filters.include_deleted:
        query = query.where(Task.deleted_at.is_(None))
    return query


def _apply_due_filter(
    query: Select[tuple[Task]],
    filters: TaskFilters,
    now: datetime,
    timezone: str,
) -> Select[tuple[Task]]:
    local_now = to_local(now, timezone)
    start_of_day = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)
    if filters.due == "today":
        query = query.where(Task.due_at >= start_of_day, Task.due_at < end_of_day)
    elif filters.due == "overdue":
        query = query.where(
            Task.due_at.is_not(None),
            Task.due_at < now,
            Task.status.notin_(("done", "cancelled")),
        )
    elif filters.due == "this_week":
        week_first = week_start(start_of_day.date())
        week_last = week_first + timedelta(days=7)
        query = query.where(Task.due_at >= week_first, Task.due_at < week_last)
    return query


def list_tasks(
    session: Session,
    filters: TaskFilters | None = None,
    now: datetime | None = None,
    timezone: str = "Asia/Tehran",
) -> list[Task]:
    """Return tasks matching the given filters."""
    filters = filters or TaskFilters()
    now = now or utcnow()
    query = _base_query(filters)

    if filters.q:
        pattern = f"%{filters.q.strip()}%"
        query = query.where(or_(Task.title.ilike(pattern), Task.description_md.ilike(pattern)))
    if filters.status:
        if filters.status == "open":
            query = query.where(Task.status.in_(OPEN_STATUSES))
        else:
            query = query.where(Task.status == filters.status)
    if filters.origin:
        query = query.where(Task.origin == filters.origin)
    if filters.context:
        query = query.where(Task.context == filters.context)
    if filters.domain_id is not None:
        query = query.join(TaskDomain, TaskDomain.task_id == Task.id).where(
            TaskDomain.domain_id == filters.domain_id
        )
    query = _apply_due_filter(query, filters, now, timezone)

    order_column = {
        "created_at": Task.created_at,
        "due_at": Task.due_at,
        "priority": Task.priority,
        "last_activity_at": Task.last_activity_at,
        "title": Task.title,
    }.get(filters.order_by, Task.created_at)
    query = query.order_by(order_column.desc() if filters.descending else order_column.asc())
    if filters.limit:
        query = query.limit(filters.limit)
    return list(session.scalars(query).unique().all())


def get_task(session: Session, task_id: int, include_deleted: bool = False) -> Task | None:
    """Return a single task or ``None``."""
    task = session.get(Task, task_id)
    if task is None:
        return None
    if task.deleted_at is not None and not include_deleted:
        return None
    return task


def create_task(
    session: Session,
    *,
    title: str,
    now: datetime,
    description_md: str = "",
    status: str = "todo",
    priority: int = 2,
    origin: str = "self_initiated",
    assigned_by: str | None = None,
    context: str = "personal",
    due_at: datetime | None = None,
    effort_minutes_estimate: int | None = None,
) -> Task:
    """Create a task and return it."""
    task = Task(
        title=title.strip(),
        description_md=description_md or "",
        status=status,
        priority=priority,
        origin=origin,
        assigned_by=(assigned_by or None),
        context=context,
        due_at=due_at,
        effort_minutes_estimate=effort_minutes_estimate,
        created_at=now,
        last_activity_at=now,
    )
    if status == "doing":
        task.started_at = now
    session.add(task)
    session.flush()
    return task


def update_task(session: Session, task: Task, now: datetime, **changes: Any) -> Task:
    """Apply a partial update to a task."""
    for field_name, value in changes.items():
        if field_name == "description_md":
            value = value or ""
        if hasattr(task, field_name):
            setattr(task, field_name, value)
    task.last_activity_at = now
    session.flush()
    return task


def set_status(session: Session, task: Task, status: str, now: datetime) -> Task:
    """Change the status of a task, maintaining the started/completed timestamps."""
    task.status = status
    if status == "doing" and task.started_at is None:
        task.started_at = now
    if status == "done":
        task.completed_at = now
        if task.started_at is None:
            task.started_at = task.created_at
    if status in ("todo", "doing"):
        task.completed_at = None
    task.last_activity_at = now
    session.flush()
    return task


def complete_task(session: Session, task: Task, now: datetime) -> Task:
    """Mark a task as done."""
    return set_status(session, task, "done", now)


def soft_delete(session: Session, task: Task, now: datetime) -> Task:
    """Soft-delete a task (kept for the audit trail)."""
    task.deleted_at = now
    task.last_activity_at = now
    session.flush()
    return task


def restore_task(session: Session, task: Task, now: datetime) -> Task:
    """Undo a soft delete."""
    task.deleted_at = None
    task.last_activity_at = now
    session.flush()
    return task


def touch_activity(session: Session, task: Task, now: datetime) -> Task:
    """Record an activity signal (note, board edit, status change…)."""
    task.last_activity_at = now
    session.flush()
    return task


def add_note(session: Session, task: Task, body_md: str, now: datetime) -> TaskNote:
    """Append a Markdown note to a task."""
    note = TaskNote(task_id=task.id, body_md=body_md or "", created_at=now)
    session.add(note)
    task.last_activity_at = now
    session.flush()
    return note


def list_notes(session: Session, task_id: int) -> list[TaskNote]:
    """Return the notes of a task, oldest first."""
    query = select(TaskNote).where(TaskNote.task_id == task_id).order_by(TaskNote.created_at.asc())
    return list(session.scalars(query).all())


# --- domains ------------------------------------------------------------


def list_domains(session: Session) -> list[Domain]:
    """Return all domains ordered by name."""
    return list(session.scalars(select(Domain).order_by(Domain.name.asc())).all())


def get_domain(session: Session, domain_id: int) -> Domain | None:
    """Return a domain by id."""
    return session.get(Domain, domain_id)


def find_domain_by_name(session: Session, name: str) -> Domain | None:
    """Return a domain with an exact (case-insensitive) name."""
    query = select(Domain).where(func.lower(Domain.name) == name.strip().lower())
    return session.scalars(query).first()


def create_domain(session: Session, name: str) -> Domain:
    """Create a domain (idempotent on name)."""
    existing = find_domain_by_name(session, name)
    if existing is not None:
        return existing
    domain = Domain(name=name.strip())
    session.add(domain)
    session.flush()
    return domain


def task_domains(session: Session, task_id: int) -> list[TaskDomain]:
    """Return the domain links of a task."""
    query = select(TaskDomain).where(TaskDomain.task_id == task_id)
    return list(session.scalars(query).all())


def assign_domain(
    session: Session,
    task: Task,
    domain: Domain,
    *,
    source: str = "user",
    confidence: float = 0.0,
    confirmed: bool = False,
) -> TaskDomain:
    """Link a task to a domain. A user assignment always wins over an AI one."""
    link = session.get(TaskDomain, (task.id, domain.id))
    if link is None:
        link = TaskDomain(
            task_id=task.id,
            domain_id=domain.id,
            source=source,
            confidence=confidence,
            confirmed=confirmed,
        )
        session.add(link)
    else:
        if source == "user" or link.source != "user":
            link.source = source
            link.confidence = confidence
        if confirmed:
            link.confirmed = True
    session.flush()
    return link


def set_task_domains(
    session: Session, task: Task, domain_ids: list[int], now: datetime
) -> list[TaskDomain]:
    """Replace the domain links of a task with the given (user-confirmed) ones."""
    current = {link.domain_id: link for link in task_domains(session, task.id)}
    wanted = set(domain_ids)
    for domain_id, link in current.items():
        if domain_id not in wanted:
            session.delete(link)
    for domain_id in wanted:
        domain = session.get(Domain, domain_id)
        if domain is None:
            continue
        assign_domain(session, task, domain, source="user", confirmed=True)
    task.last_activity_at = now
    session.flush()
    return task_domains(session, task.id)
