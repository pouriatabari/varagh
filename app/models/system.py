"""System tables: settings, notification log and AI run audit."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Setting(Base, TimestampMixin):
    """Key/value settings store; the value is a JSON document."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NotificationLog(Base, TimestampMixin):
    """Dedupe ledger for outbound notifications."""

    __tablename__ = "notification_log"
    __table_args__ = (
        UniqueConstraint(
            "kind", "ref_id", "channel", "window_key", name="uq_notification_log_dedupe"
        ),
        Index("ix_notification_log_sent_at", "sent_at"),
        Index("ix_notification_log_kind", "kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    ref_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    window_key: Mapped[str] = mapped_column(String(60), default="", nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AIRun(Base, TimestampMixin):
    """Audit trail of every AI provider call."""

    __tablename__ = "ai_runs"
    __table_args__ = (
        Index("ix_ai_runs_feature", "feature"),
        Index("ix_ai_runs_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    feature: Mapped[str] = mapped_column(String(60), nullable=False)
    model: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
