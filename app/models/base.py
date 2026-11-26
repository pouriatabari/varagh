"""Declarative base, shared column mixins and small enum vocabularies."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import DateTime, MetaData
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

JSONType = JSONB


def utcnow() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    type_annotation_map: ClassVar[dict[Any, Any]] = {dict[str, Any]: JSONB, list[Any]: JSONB}


class TimestampMixin:
    """Adds a timezone-aware ``created_at`` column."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


# --- Vocabularies -------------------------------------------------------

TASK_STATUSES = ("todo", "doing", "done", "cancelled")
TASK_ORIGINS = ("self_initiated", "assigned")
TASK_CONTEXTS = ("company", "personal", "learning")
TIME_ENTRY_KINDS = ("work", "overtime", "study", "learning")
LEARNING_ITEM_KINDS = ("book", "course", "article", "other")
LEARNING_ITEM_STATUSES = ("not_started", "in_progress", "done", "dropped")
ACHIEVEMENT_KINDS = ("technical", "work", "personal", "learning")
REVIEW_PERIOD_TYPES = ("month", "quarter", "half", "year", "custom")
DOMAIN_SOURCES = ("ai", "user")
BOARD_ITEM_TYPES = ("sticky", "text")
