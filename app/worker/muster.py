"""The muster of the month: the draft the worker prepares.

At the end of every Jalali month the worker writes the draft of the
muster of that month: an immutable snapshot of the statistics and the
proposals of the AI. Nothing is given before the user confirms the
muster, so a draft never carries a medal.
"""

from __future__ import annotations

import datetime as dt
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.review import Review
from app.services import reviews as review_service
from app.utils.jalali import jalali_of, previous_period

logger = logging.getLogger("varagh.worker.muster")


def ensure_monthly_muster(session: Session, now: dt.datetime) -> Review | None:
    """Write the draft of the muster of the month that just ended.

    The draft is written once: a second tick of the worker in the same
    month finds it and leaves it alone.
    """
    today = now.date()
    jalali = jalali_of(today)
    if jalali.day > 3:
        # The month is still running; the muster comes at its end.
        return None
    start, end = previous_period("month", today, today)
    existing = session.scalars(
        select(Review).where(
            Review.period_type == "month",
            Review.period_start == start,
            Review.period_end == end,
        )
    ).first()
    if existing is not None:
        return existing
    stats = review_service.compute_stats(session, start=start, end=end)
    review = review_service.create_review(
        session,
        period=review_service.PeriodSelection("month", start, end),
        stats=stats,
    )
    session.flush()
    logger.info("muster draft of %s is ready", end)
    return review
