"""Task-related ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Task(Base, TimestampMixin):
    """A single unit of work: assigned to the user or self-initiated."""

    __tablename__ = "tasks"
    __table_args__ = (
        CheckConstraint("status IN ('todo', 'doing', 'done', 'cancelled')", name="status_valid"),
        CheckConstraint("origin IN ('self_initiated', 'assigned')", name="origin_valid"),
        CheckConstraint("context IN ('company', 'personal', 'learning')", name="context_valid"),
        CheckConstraint("priority >= 0 AND priority <= 4", name="priority_range"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_due_at", "due_at"),
        Index("ix_tasks_last_activity_at", "last_activity_at"),
        Index("ix_tasks_context", "context"),
        Index("ix_tasks_origin", "origin"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="todo", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    origin: Mapped[str] = mapped_column(String(20), default="self_initiated", nullable=False)
    assigned_by: Mapped[str | None] = mapped_column(String(200))
    context: Mapped[str] = mapped_column(String(20), default="personal", nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effort_minutes_estimate: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # A private task keeps its text away from the AI and from the medals.
    is_private: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # A task that does not count for the medals may still be part of the
    # work: it is only kept out of the honours.
    counts_for_medals: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Domain(Base, TimestampMixin):
    """A user-defined classification area. Starts empty — no hard-coded taxonomy."""

    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id", ondelete="SET NULL"))


class TaskDomain(Base):
    """Link between a task and a domain, with provenance of the classification."""

    __tablename__ = "task_domains"
    __table_args__ = (
        CheckConstraint("source IN ('ai', 'user')", name="source_valid"),
        Index("ix_task_domains_domain_id", "domain_id"),
    )

    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
    domain_id: Mapped[int] = mapped_column(
        ForeignKey("domains.id", ondelete="CASCADE"), primary_key=True
    )
    source: Mapped[str] = mapped_column(String(10), default="ai", nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class TaskNote(Base, TimestampMixin):
    """A Markdown note attached to a task (the notes timeline)."""

    __tablename__ = "task_notes"
    __table_args__ = (Index("ix_task_notes_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, default="", nullable=False)


class BoardItem(Base, TimestampMixin):
    """A draggable sticky / text card on a task's board."""

    __tablename__ = "board_items"
    __table_args__ = (Index("ix_board_items_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="sticky", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    x: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    y: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="yellow", nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
