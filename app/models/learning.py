"""Learning-tracker ORM models."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class LearningItem(Base, TimestampMixin):
    """A book, course, article or other thing the user is studying."""

    __tablename__ = "learning_items"
    __table_args__ = (
        CheckConstraint("kind IN ('book', 'course', 'article', 'other')", name="kind_valid"),
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'done', 'dropped')",
            name="status_valid",
        ),
        Index("ix_learning_items_status", "status"),
        Index("ix_learning_items_finished_at", "finished_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20), default="book", nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    author_or_provider: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="not_started", nullable=False)
    started_at: Mapped[date | None] = mapped_column(Date)
    finished_at: Mapped[date | None] = mapped_column(Date)
    notes_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearningUnit(Base, TimestampMixin):
    """An ordered unit (chapter, lesson, section) inside a learning item."""

    __tablename__ = "learning_units"
    __table_args__ = (
        Index("ix_learning_units_item_id", "item_id"),
        CheckConstraint("position >= 0", name="position_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("learning_items.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LearningLog(Base, TimestampMixin):
    """A study session: either time spent, or "read up to unit X"."""

    __tablename__ = "learning_logs"
    __table_args__ = (
        Index("ix_learning_logs_item_id", "item_id"),
        Index("ix_learning_logs_logged_at", "logged_at"),
        CheckConstraint("minutes IS NULL OR minutes >= 0", name="minutes_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("learning_items.id", ondelete="CASCADE"), nullable=False
    )
    unit_id: Mapped[int | None] = mapped_column(
        ForeignKey("learning_units.id", ondelete="SET NULL")
    )
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    minutes: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
