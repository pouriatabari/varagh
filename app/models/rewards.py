"""The tables of the reward engine.

The medals, the evidence that backs them, the titles that were reached,
the orders, the quests and the claims of the realms. The honours of the
hall are written here by the muster, never by hand.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, utcnow

MEDAL_TIERS = ("bronze", "silver", "gold")
MEDAL_VIRTUES = ("prowess", "valor", "wisdom", "loyalty", "largesse", "temperance")
MEDAL_KINDS = ("earned", "quest", "victory", "temperance")
ORDER_KEYS = ("quill", "scholar", "round_table")
QUEST_STATUSES = ("proposed", "accepted", "done", "dropped")
TITLE_KEYS = (
    "page",
    "squire",
    "knight",
    "banneret",
    "baron",
    "viscount",
    "earl",
    "marquess",
    "duke",
    "prince",
    "king",
    "bretwalda",
)


class Medal(Base, TimestampMixin):
    """A medal that was awarded by a muster."""

    __tablename__ = "medals"
    __table_args__ = (
        Index("ix_medals_month_key", "month_key"),
        Index("ix_medals_virtue", "virtue"),
        Index("ix_medals_domain_id", "domain_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    muster_id: Mapped[int | None] = mapped_column(
        ForeignKey("reviews.id", ondelete="SET NULL")
    )
    achievement_id: Mapped[int | None] = mapped_column(
        ForeignKey("achievements.id", ondelete="SET NULL")
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    virtue: Mapped[str] = mapped_column(String(20), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="earned", nullable=False)
    domain_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id", ondelete="SET NULL"))
    month_key: Mapped[str] = mapped_column(String(10), nullable=False)
    value_raw: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    value_counted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    awarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    evidence: Mapped[list[MedalEvidence]] = relationship(
        back_populates="medal", cascade="all, delete-orphan"
    )


class MedalEvidence(Base):
    """A task that backs a medal. A task backs one medal at most."""

    __tablename__ = "medal_evidence"
    __table_args__ = (UniqueConstraint("task_id", name="uq_medal_evidence_task"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    medal_id: Mapped[int] = mapped_column(
        ForeignKey("medals.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[int] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
    )

    medal: Mapped[Medal] = relationship(back_populates="evidence")


class TitleHistory(Base):
    """A title that was reached, with the vigil that came with it."""

    __tablename__ = "title_history"
    __table_args__ = (Index("ix_title_history_title_key", "title_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    title_key: Mapped[str] = mapped_column(String(30), nullable=False)
    reached_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    vigil: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=dict)


class Order(Base):
    """A badge without value."""

    __tablename__ = "orders"
    __table_args__ = (UniqueConstraint("order_key", name="uq_orders_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    order_key: Mapped[str] = mapped_column(String(30), nullable=False)
    earned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class Quest(Base):
    """An optional quest the app proposes every month."""

    __tablename__ = "quests"
    __table_args__ = (Index("ix_quests_month_key", "month_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    month_key: Mapped[str] = mapped_column(String(10), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="proposed", nullable=False)
    medal_id: Mapped[int | None] = mapped_column(
        ForeignKey("medals.id", ondelete="SET NULL")
    )


class RealmClaim(Base):
    """A realm of the map: assigned to a domain, lit and claimed."""

    __tablename__ = "realm_claims"
    __table_args__ = (UniqueConstraint("realm_key", name="uq_realm_claims_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    realm_key: Mapped[str] = mapped_column(String(40), nullable=False)
    domain_id: Mapped[int | None] = mapped_column(ForeignKey("domains.id", ondelete="SET NULL"))
    castles_lit: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SagaChapter(Base):
    """A chapter of the saga, written for one muster."""

    __tablename__ = "saga_chapters"
    __table_args__ = (Index("ix_saga_chapters_volume_key", "volume_key"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    review_id: Mapped[int | None] = mapped_column(
        ForeignKey("reviews.id", ondelete="CASCADE")
    )
    volume_key: Mapped[str] = mapped_column(String(40), nullable=False)
    body_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    facts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    edited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
