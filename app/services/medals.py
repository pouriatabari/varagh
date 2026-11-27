"""The medals of the user.

A medal is never stored: it is computed out of the database every time the
page is built. The progress that earned it may disappear — a task is undone,
a learning item is deleted, a review is removed — and the medal goes away
with it. The user cannot collect a medal that the work no longer supports.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.review import Achievement, Review
from app.models.task import Task
from app.models.timing import TimeEntry
from app.services import learning as learning_service

TIERS = ("bronze", "silver", "gold")


@dataclass(frozen=True)
class Medal:
    """One medal and the progress towards it."""

    key: str
    title_fa: str
    icon: str
    unit: str
    value: float
    bronze: float
    silver: float
    gold: float

    @property
    def tier(self) -> str | None:
        """The tier the progress earned, or ``None`` when there is none yet."""
        if self.value >= self.gold:
            return "gold"
        if self.value >= self.silver:
            return "silver"
        if self.value >= self.bronze:
            return "bronze"
        return None

    @property
    def earned(self) -> bool:
        """Whether the medal was earned."""
        return self.tier is not None

    @property
    def next_threshold(self) -> float:
        """The threshold of the next tier."""
        if self.value >= self.gold:
            return self.gold
        if self.value >= self.silver:
            return self.gold
        if self.value >= self.bronze:
            return self.silver
        return self.bronze

    @property
    def percent(self) -> int:
        """How far the progress is towards the next tier, in percent."""
        if self.value >= self.gold:
            return 100
        start = self.value
        if self.value >= self.silver:
            start = self.silver
        elif self.value >= self.bronze:
            start = self.bronze
        else:
            start = 0
        span = self.next_threshold - start
        if span <= 0:
            return 100
        return int(min(100, max(0, round((self.value - start) / span * 100))))


def _completed_tasks(session: Session) -> int:
    """Return the number of the tasks that are done."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(Task)
            .where(Task.status == "done", Task.deleted_at.is_(None))
        )
        or 0
    )


def _measured_hours(session: Session) -> float:
    """Return the measured hours of every time entry."""
    minutes = session.scalar(
        select(func.coalesce(func.sum(TimeEntry.duration_minutes), 0))
    )
    return round(float(minutes or 0) / 60, 1)


def _confirmed_achievements(session: Session) -> int:
    """Return the number of the confirmed achievements."""
    return int(
        session.scalar(
            select(func.count())
            .select_from(Achievement)
            .where(Achievement.confirmed.is_(True))
        )
        or 0
    )


def _finished_learning_items(session: Session) -> int:
    """Return the number of the learning items that are fully read."""
    items = learning_service.list_items(session)
    finished = 0
    for item in items:
        item_progress = learning_service.progress(session, item)
        if item_progress.total_units > 0 and item_progress.percent >= 100:
            finished += 1
    return finished


def _finished_reviews(session: Session) -> int:
    """Return the number of the reviews that carry a rating."""
    return int(
        session.scalar(
            select(func.count()).select_from(Review).where(Review.rating.isnot(None))
        )
        or 0
    )


def compute_medals(
    session: Session, *, now: datetime, streak_days: int = 0
) -> list[Medal]:
    """Return the medals of the user, computed out of the database."""
    return [
        Medal(
            key="tasks_done",
            title_fa="تسک‌های انجام‌شده",
            icon="medal",
            unit="tasks",
            value=float(_completed_tasks(session)),
            bronze=10,
            silver=50,
            gold=100,
        ),
        Medal(
            key="measured_hours",
            title_fa="ساعت کار اندازه‌گیری‌شده",
            icon="medal",
            unit="hours",
            value=_measured_hours(session),
            bronze=10,
            silver=50,
            gold=100,
        ),
        Medal(
            key="achievements",
            title_fa="دستاوردهای تأییدشده",
            icon="trophy",
            unit="count",
            value=float(_confirmed_achievements(session)),
            bronze=1,
            silver=5,
            gold=10,
        ),
        Medal(
            key="learning_done",
            title_fa="موارد یادگیری تمام‌شده",
            icon="learning",
            unit="count",
            value=float(_finished_learning_items(session)),
            bronze=1,
            silver=3,
            gold=5,
        ),
        Medal(
            key="reviews",
            title_fa="ارزیابی‌های امتیازدار",
            icon="muster",
            unit="count",
            value=float(_finished_reviews(session)),
            bronze=1,
            silver=3,
            gold=5,
        ),
        Medal(
            key="streak",
            title_fa="روزهای پیوستهٔ کار",
            icon="dashboard",
            unit="days",
            value=float(streak_days),
            bronze=3,
            silver=7,
            gold=30,
        ),
    ]


def _value_text(value: float) -> str:
    """Return the value of a medal as text: a count has no decimal."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


def medal_context(medals: list[Medal]) -> list[dict[str, Any]]:
    """Turn the medals into the values the template renders."""
    return [
        {
            "key": medal.key,
            "title": medal.title_fa,
            "icon": f"medal_{medal.tier}" if medal.tier else "medal",
            "tier": medal.tier,
            "earned": medal.earned,
            "value": medal.value,
            "value_text": _value_text(medal.value),
            "percent": medal.percent,
            "next": medal.next_threshold,
            "unit": medal.unit,
        }
        for medal in medals
    ]
