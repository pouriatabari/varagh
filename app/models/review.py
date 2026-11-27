"""Review and achievement ORM models."""

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

from app.models.base import Base, TimestampMixin, utcnow


class Review(Base, TimestampMixin):
    """A periodic self-review with an immutable stats snapshot."""

    __tablename__ = "reviews"
    __table_args__ = (
        CheckConstraint(
            "period_type IN ('month', 'quarter', 'half', 'year', 'custom')",
            name="period_type_valid",
        ),
        CheckConstraint("rating IS NULL OR (rating >= 1 AND rating <= 5)", name="rating_range"),
        CheckConstraint("status IN ('draft', 'finished')", name="review_status_valid"),
        Index("ix_reviews_period_type", "period_type"),
        Index("ix_reviews_period_start", "period_start"),
        Index("ix_reviews_period_end", "period_end"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    period_type: Mapped[str] = mapped_column(String(20), default="month", nullable=False)
    # A muster is a draft until the user confirms it; nothing is given
    # before that moment.
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    stats: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    ai_draft: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    user_final_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Achievement(Base, TimestampMixin):
    """Something the user accomplished, optionally grounded in completed tasks."""

    __tablename__ = "achievements"
    __table_args__ = (
        CheckConstraint("kind IN ('technical', 'work', 'personal', 'learning')", name="kind_valid"),
        Index("ix_achievements_period_start", "period_start"),
        Index("ix_achievements_period_end", "period_end"),
        Index("ix_achievements_kind", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="technical", nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    impact_note: Mapped[str | None] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AchievementTask(Base):
    """Evidence link: an achievement is grounded in concrete tasks."""

    __tablename__ = "achievement_tasks"
    __table_args__ = (Index("ix_achievement_tasks_task_id", "task_id"),)

    achievement_id: Mapped[int] = mapped_column(
        ForeignKey("achievements.id", ondelete="CASCADE"), primary_key=True
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True
    )
