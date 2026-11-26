"""Time-entry and daily-journal ORM models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TimeEntry(Base, TimestampMixin):
    """A measured block of time.

    ``duration_minutes`` is the source of truth for the *measured* time layer;
    it is derived from ``started_at``/``ended_at`` when the latter are given.
    """

    __tablename__ = "time_entries"
    __table_args__ = (
        CheckConstraint("kind IN ('work', 'overtime', 'study', 'learning')", name="kind_valid"),
        CheckConstraint(
            "kind <> 'overtime' OR (reason IS NOT NULL AND length(btrim(reason)) > 0)",
            name="overtime_reason_required",
        ),
        CheckConstraint(
            "duration_minutes IS NULL OR duration_minutes >= 0", name="duration_non_negative"
        ),
        Index("ix_time_entries_started_at", "started_at"),
        Index("ix_time_entries_task_id", "task_id"),
        Index("ix_time_entries_kind", "kind"),
        Index("ix_time_entries_learning_item_id", "learning_item_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    learning_item_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_items.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(20), default="work", nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    is_off_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DailyJournal(Base, TimestampMixin):
    """Free-form Persian end-of-day journal entry."""

    __tablename__ = "daily_journal"
    __table_args__ = (Index("ix_daily_journal_date", "date", unique=True),)

    id: Mapped[int] = mapped_column(primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    raw_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    parsed: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
