"""Learning tracker service: books, courses, units and study logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.learning import LearningItem, LearningLog, LearningUnit

VALID_KINDS = ("book", "course", "article", "other")
VALID_STATUSES = ("not_started", "in_progress", "done", "dropped")


@dataclass(slots=True)
class ItemProgress:
    """Progress of a learning item."""

    item_id: int
    total_units: int
    done_units: int
    minutes: int
    last_activity_at: datetime | None

    @property
    def percent(self) -> int:
        """Percentage of finished units (0 when there are no units)."""
        if self.total_units <= 0:
            return 0
        return round(self.done_units / self.total_units * 100)


def create_item(
    session: Session,
    *,
    title: str,
    kind: str = "book",
    author_or_provider: str | None = None,
    notes_md: str = "",
    now: datetime,
    started_at: date | None = None,
) -> LearningItem:
    """Create a learning item."""
    item = LearningItem(
        kind=kind if kind in VALID_KINDS else "book",
        title=title.strip(),
        author_or_provider=(author_or_provider or None),
        status="not_started",
        notes_md=notes_md or "",
        started_at=started_at,
    )
    session.add(item)
    session.flush()
    return item


def list_items(
    session: Session, status: str | None = None, include_deleted: bool = False
) -> list[LearningItem]:
    """Return the learning items, optionally filtered by status."""
    query = select(LearningItem).order_by(LearningItem.created_at.desc())
    if not include_deleted:
        query = query.where(LearningItem.deleted_at.is_(None))
    if status:
        query = query.where(LearningItem.status == status)
    return list(session.scalars(query).all())


def get_item(
    session: Session, item_id: int, include_deleted: bool = False
) -> LearningItem | None:
    """Return a learning item by id."""
    item = session.get(LearningItem, item_id)
    if item is None:
        return None
    if item.deleted_at is not None and not include_deleted:
        return None
    return item


def soft_delete(session: Session, item: LearningItem, now: datetime) -> LearningItem:
    """Soft-delete a learning item (kept for the audit trail)."""
    item.deleted_at = now
    session.flush()
    return item


def restore(session: Session, item: LearningItem) -> LearningItem:
    """Undo a soft delete."""
    item.deleted_at = None
    session.flush()
    return item


def set_status(session: Session, item: LearningItem, status: str, now: datetime) -> LearningItem:
    """Change the status of a learning item."""
    item.status = status if status in VALID_STATUSES else item.status
    if item.status == "in_progress" and item.started_at is None:
        item.started_at = now.date()
    if item.status == "done":
        item.finished_at = now.date()
        if item.started_at is None:
            item.started_at = now.date()
    if item.status == "dropped":
        item.finished_at = None
    session.flush()
    return item


def list_units(session: Session, item_id: int) -> list[LearningUnit]:
    """Return the ordered units of a learning item."""
    query = (
        select(LearningUnit)
        .where(LearningUnit.item_id == item_id)
        .order_by(LearningUnit.position.asc(), LearningUnit.id.asc())
    )
    return list(session.scalars(query).all())


def add_unit(
    session: Session, item: LearningItem, title: str, position: int | None = None
) -> LearningUnit:
    """Append a unit to a learning item."""
    if position is None:
        existing = list_units(session, item.id)
        position = len(existing)
    unit = LearningUnit(item_id=item.id, position=position, title=title.strip())
    session.add(unit)
    session.flush()
    return unit


def set_units(session: Session, item: LearningItem, titles: list[str]) -> list[LearningUnit]:
    """Replace the units of an item with the given ordered titles."""
    for unit in list_units(session, item.id):
        session.delete(unit)
    session.flush()
    units = []
    for index, title in enumerate(titles):
        cleaned = title.strip()
        if cleaned:
            units.append(add_unit(session, item, cleaned, index))
    return units


def tick_unit(session: Session, unit: LearningUnit, done: bool, now: datetime) -> LearningUnit:
    """Mark a unit as done or not done."""
    unit.done_at = now if done else None
    session.flush()
    return unit


def log_activity(
    session: Session,
    item: LearningItem,
    *,
    now: datetime,
    minutes: int | None = None,
    unit_id: int | None = None,
    note: str | None = None,
) -> LearningLog:
    """Record a study session."""
    entry = LearningLog(
        item_id=item.id,
        unit_id=unit_id,
        logged_at=now,
        minutes=minutes,
        note=(note or None),
    )
    session.add(entry)
    if item.status == "not_started":
        item.status = "in_progress"
        item.started_at = now.date()
    session.flush()
    return entry


def progress(session: Session, item: LearningItem) -> ItemProgress:
    """Return the progress of a learning item."""
    units = list_units(session, item.id)
    logs = list(session.scalars(select(LearningLog).where(LearningLog.item_id == item.id)).all())
    minutes = sum(log.minutes or 0 for log in logs)
    last_activity = max((log.logged_at for log in logs), default=None)
    return ItemProgress(
        item_id=item.id,
        total_units=len(units),
        done_units=sum(1 for unit in units if unit.done_at is not None),
        minutes=minutes,
        last_activity_at=last_activity,
    )


def progress_series(
    session: Session, items: list[LearningItem]
) -> dict[str, dict[str, Any]]:
    """Return the series of the progress and the study minutes of the items."""
    labels: list[str] = []
    percents: list[float] = []
    minutes: list[float] = []
    for item in items:
        item_progress = progress(session, item)
        labels.append(item.title)
        percents.append(float(item_progress.percent))
        minutes.append(float(item_progress.minutes))
    return {
        "progress_by_item": {
            "labels": labels,
            "values": percents,
            "unit": "units.percent",
        },
        "minutes_by_item": {
            "labels": labels,
            "values": minutes,
            "unit": "units.minutes",
        },
    }


def stale_items(
    session: Session, *, threshold_days: int, now: datetime
) -> list[tuple[LearningItem, ItemProgress]]:
    """Return in-progress items without any activity for too long."""
    result: list[tuple[LearningItem, ItemProgress]] = []
    for item in list_items(session, status="in_progress"):
        item_progress = progress(session, item)
        last = item_progress.last_activity_at or item.created_at
        if last is None:
            continue
        if now - last > timedelta(days=threshold_days):
            result.append((item, item_progress))
    return result


def learning_report(session: Session, *, now: datetime) -> dict[str, object]:
    """Return the yearly/custom learning report."""
    items = list_items(session)
    finished = [item for item in items if item.status == "done"]
    in_progress = [item for item in items if item.status == "in_progress"]
    dropped = [item for item in items if item.status == "dropped"]
    not_started = [item for item in items if item.status == "not_started"]
    details = []
    for item in items:
        item_progress = progress(session, item)
        details.append(
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "status": item.status,
                "percent": item_progress.percent,
                "minutes": item_progress.minutes,
                "units_done": item_progress.done_units,
                "units_total": item_progress.total_units,
            }
        )
    return {
        "total_items": len(items),
        "finished": len(finished),
        "in_progress": len(in_progress),
        "dropped": len(dropped),
        "not_started": len(not_started),
        "total_minutes": sum(int(item["minutes"]) for item in details),
        "items": details,
        "generated_at": now.isoformat(),
    }
