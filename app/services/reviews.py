"""Periodic reviews: the statistics snapshot, the comparison and the export.

The snapshot stored in ``review.stats`` is immutable: it is written once when
the review is created and never recomputed, so a review always describes the
period as it looked at the time of writing.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.i18n import t
from app.models.review import Review
from app.models.task import Task
from app.services import learning as learning_service
from app.services import tasks as task_service
from app.services import time_entries as time_service
from app.utils.jalali import jalali_short, period_bounds, previous_period
from app.utils.text import format_minutes
from app.utils.time import to_local

PERIOD_TYPES = ("month", "quarter", "half", "year", "custom")


@dataclass(slots=True)
class PeriodSelection:
    """The period a review covers."""

    period_type: str
    start: date
    end: date

    @property
    def label(self) -> str:
        """A short label of the period."""
        return f"{self.period_type} {self.start.isoformat()} → {self.end.isoformat()}"


def resolve_period(
    session: Session,
    period_type: str,
    reference: date,
    calendar_system: str = "jalali",
    custom_start: date | None = None,
    custom_end: date | None = None,
) -> PeriodSelection:
    """Return the bounds of the requested period."""
    if period_type == "custom" and custom_start and custom_end:
        return PeriodSelection("custom", custom_start, custom_end)
    kind = period_type if period_type in PERIOD_TYPES else "month"
    start, end = period_bounds(kind, reference, calendar_system)
    return PeriodSelection(kind, start, end)


def _median_lead_time(tasks: list[Task]) -> int | None:
    """Median number of minutes between the start and the completion."""
    spans = []
    for task in tasks:
        if task.started_at and task.completed_at:
            delta = task.completed_at - task.started_at
            spans.append(max(0, int(delta.total_seconds() // 60)))
    if not spans:
        return None
    return int(statistics.median(spans))


def compute_stats(
    session: Session,
    *,
    start: date,
    end: date,
    timezone: str = "Asia/Tehran",
) -> dict[str, Any]:
    """Compute the statistics of a period.

    Every number states its basis: measured minutes come from the time
    entries, estimated minutes from the estimates and elapsed minutes from
    the task timestamps.
    """
    start_dt = datetime.combine(start, time.min, tzinfo=UTC)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=UTC)

    all_tasks = session.scalars(
        select(Task).where(Task.deleted_at.is_(None)).order_by(Task.id.asc())
    ).all()
    created = [
        task
        for task in all_tasks
        if task.created_at and start <= to_local(task.created_at, timezone).date() <= end
    ]
    completed = [
        task
        for task in all_tasks
        if task.completed_at and start <= to_local(task.completed_at, timezone).date() <= end
    ]
    open_tasks = [task for task in all_tasks if task.status in ("todo", "doing")]

    entries = time_service.list_entries(session, start=start_dt, end=end_dt)
    minutes_by_kind: dict[str, int] = {}
    off_day_minutes = 0
    regular_day_minutes = 0
    overtime_reasons: dict[str, int] = {}
    policy = time_service.policy_from_settings(session)
    for entry in entries:
        minutes = entry.duration_minutes or 0
        minutes_by_kind[entry.kind] = minutes_by_kind.get(entry.kind, 0) + minutes
        if entry.kind == "overtime":
            local_day = to_local(entry.started_at, timezone).date()
            if time_service.compute_is_off_day(local_day, policy):
                off_day_minutes += minutes
            else:
                regular_day_minutes += minutes
            reason = (entry.reason or "").strip() or "—"
            overtime_reasons[reason] = overtime_reasons.get(reason, 0) + minutes

    measured_total = sum(minutes_by_kind.values())
    estimated_total = sum(task.effort_minutes_estimate or 0 for task in created)
    elapsed_total = 0
    for task in completed:
        if task.started_at and task.completed_at:
            elapsed_total += max(
                0, int((task.completed_at - task.started_at).total_seconds() // 60)
            )

    counts_by_origin: dict[str, int] = {}
    for task in all_tasks:
        counts_by_origin[task.origin] = counts_by_origin.get(task.origin, 0) + 1
    counts_by_context: dict[str, int] = {}
    for task in all_tasks:
        counts_by_context[task.context] = counts_by_context.get(task.context, 0) + 1

    domain_names = task_service.domain_names_for_tasks(session, [task.id for task in all_tasks])
    counts_by_domain: dict[str, int] = {}
    for names in domain_names.values():
        for name in names:
            counts_by_domain[name] = counts_by_domain.get(name, 0) + 1

    learning = learning_service.learning_report(session, now=datetime.now(UTC))
    study_minutes = minutes_by_kind.get("study", 0) + minutes_by_kind.get("learning", 0)

    task_rows = []
    for task in completed:
        task_rows.append(
            {
                "id": task.id,
                "title": task.title,
                "measured_minutes": time_service.measured_minutes_for_task(session, task.id),
                "estimate_minutes": task.effort_minutes_estimate,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            }
        )

    completion_rate = round(len(completed) / len(created) * 100, 1) if created else 0.0
    return {
        "period": {"start": start.isoformat(), "end": end.isoformat()},
        "generated_at": datetime.now(UTC).isoformat(),
        "counts": {
            "created": len(created),
            "completed": len(completed),
            "open": len(open_tasks),
            "total": len(all_tasks),
            "completion_rate": completion_rate,
        },
        "counts_by_origin": counts_by_origin,
        "counts_by_context": counts_by_context,
        "counts_by_domain": counts_by_domain,
        "top_domains": sorted(counts_by_domain.items(), key=lambda item: item[1], reverse=True)[:5],
        "measured_minutes_by_kind": minutes_by_kind,
        "measured_minutes_total": measured_total,
        "estimated_minutes_total": estimated_total,
        "elapsed_minutes_total": elapsed_total,
        "lead_time_median_minutes": _median_lead_time(completed),
        "overtime": {
            "off_day_minutes": off_day_minutes,
            "regular_day_minutes": regular_day_minutes,
            "reasons": overtime_reasons,
        },
        "study_minutes": study_minutes,
        "learning": {
            "total_items": learning["total_items"],
            "finished": learning["finished"],
            "in_progress": learning["in_progress"],
            "total_minutes": learning["total_minutes"],
        },
        "tasks": task_rows,
        "series": _series(minutes_by_kind, counts_by_context, counts_by_origin, entries, timezone),
        "basis": {
            "measured": "time_entries",
            "estimated": "tasks.effort_minutes_estimate",
            "elapsed": "completed_at - started_at",
        },
    }


def _series(
    minutes_by_kind: dict[str, int],
    counts_by_context: dict[str, int],
    counts_by_origin: dict[str, int],
    entries: list[Any],
    timezone: str,
) -> dict[str, Any]:
    """Return the series the AI may chart out of the statistics of the period."""
    kinds = [kind for kind in ("work", "overtime", "study", "learning") if kind in minutes_by_kind]
    by_kind = {
        "measured_minutes_by_kind": {
            "labels": [t(f"time.kind.{kind}") for kind in kinds],
            "values": [minutes_by_kind[kind] for kind in kinds],
            "unit": "units.minutes",
        }
    }
    contexts = [
        context for context in ("company", "personal", "learning") if context in counts_by_context
    ]
    by_context = {
        "counts_by_context": {
            "labels": [t(f"tasks.context.{context}") for context in contexts],
            "values": [counts_by_context[context] for context in contexts],
            "unit": "units.count",
        }
    }
    origins = [origin for origin in ("self_initiated", "assigned") if origin in counts_by_origin]
    by_origin = {
        "counts_by_origin": {
            "labels": [t(f"tasks.origin.{origin}") for origin in origins],
            "values": [counts_by_origin[origin] for origin in origins],
            "unit": "units.count",
        }
    }
    overtime = {
        "overtime_by_day": {
            "labels": _day_labels(entries, timezone, kind="overtime"),
            "values": _day_values(entries, timezone, kind="overtime"),
            "unit": "units.minutes",
        }
    }
    daily = {
        "measured_minutes_by_day": {
            "labels": _day_labels(entries, timezone),
            "values": _day_values(entries, timezone),
            "unit": "units.minutes",
        }
    }
    return {**by_kind, **by_context, **by_origin, **daily, **overtime}


def _day_labels(entries: list[Any], timezone: str, kind: str | None = None) -> list[str]:
    """Return the Jalali labels of the days that have entries."""
    days = _days_with_entries(entries, timezone, kind)
    return [jalali_short(day) for day in days]


def _day_values(entries: list[Any], timezone: str, kind: str | None = None) -> list[int]:
    """Return the measured minutes of every day that has entries."""
    days = _days_with_entries(entries, timezone, kind)
    totals = {day: 0 for day in days}
    for entry in entries:
        if kind and entry.kind != kind:
            continue
        day = to_local(entry.started_at, timezone).date()
        if day in totals:
            totals[day] += entry.duration_minutes or 0
    return [totals[day] for day in days]


def _days_with_entries(entries: list[Any], timezone: str, kind: str | None = None) -> list[date]:
    """Return the sorted days that have entries."""
    days = {
        to_local(entry.started_at, timezone).date()
        for entry in entries
        if not kind or entry.kind == kind
    }
    return sorted(days)


def delete_review(session: Session, review: Review) -> None:
    """Delete a review with its statistics snapshot."""
    session.delete(review)
    session.flush()


def list_reviews(session: Session) -> list[Review]:
    """Return every review, newest period first."""
    query = select(Review).order_by(Review.period_end.desc(), Review.id.desc())
    return list(session.scalars(query).all())


def get_review(session: Session, review_id: int) -> Review | None:
    """Return a review by id."""
    return session.get(Review, review_id)


def create_review(
    session: Session,
    *,
    period: PeriodSelection,
    stats: dict[str, Any],
    user_final_md: str = "",
    rating: int | None = None,
    ai_draft: dict[str, Any] | None = None,
) -> Review:
    """Store a review with its immutable statistics snapshot."""
    review = Review(
        period_type=period.period_type,
        period_start=period.start,
        period_end=period.end,
        stats=stats,
        ai_draft=ai_draft,
        user_final_md=user_final_md,
        rating=rating if rating is not None and 1 <= rating <= 5 else None,
    )
    session.add(review)
    session.flush()
    return review


def update_review(
    session: Session,
    review: Review,
    *,
    user_final_md: str | None = None,
    rating: int | None = None,
    ai_draft: dict[str, Any] | None = None,
) -> Review:
    """Update the editable parts of a review; the snapshot stays untouched."""
    if user_final_md is not None:
        review.user_final_md = user_final_md
    if rating is not None and 1 <= rating <= 5:
        review.rating = rating
    if ai_draft is not None:
        review.ai_draft = ai_draft
    session.flush()
    return review


def find_previous_review(
    session: Session, review: Review, calendar_system: str = "jalali"
) -> Review | None:
    """Return the review of the previous period of the same type."""
    start, end = previous_period(
        review.period_type, review.period_start, review.period_end, calendar_system
    )
    query = select(Review).where(
        Review.period_type == review.period_type,
        Review.period_start == start,
        Review.period_end == end,
    )
    return session.scalars(query).first()


def compare_stats(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    """Compare two snapshots; the deltas are relative to the previous period."""
    if not previous:
        return {"has_previous": False, "rows": []}
    rows: list[dict[str, Any]] = []

    def add(label: str, key: str, current_value: Any, previous_value: Any, unit: str = "") -> None:
        delta: Any = None
        if isinstance(current_value, (int, float)) and isinstance(previous_value, (int, float)):
            delta = round(current_value - previous_value, 1)
        rows.append(
            {
                "label": label,
                "current": current_value,
                "previous": previous_value,
                "delta": delta,
                "unit": unit,
            }
        )

    current_counts = current.get("counts", {})
    previous_counts = previous.get("counts", {})
    add(
        "تعداد انجام‌شده",
        "completed",
        current_counts.get("completed", 0),
        previous_counts.get("completed", 0),
    )
    add(
        "نرخ تکمیل",
        "completion_rate",
        current_counts.get("completion_rate", 0),
        previous_counts.get("completion_rate", 0),
        "٪",
    )
    add(
        "زمان اندازه‌گیری‌شده",
        "measured",
        current.get("measured_minutes_total", 0),
        previous.get("measured_minutes_total", 0),
        "دقیقه",
    )
    add(
        "زمان سپری‌شده",
        "elapsed",
        current.get("elapsed_minutes_total", 0),
        previous.get("elapsed_minutes_total", 0),
        "دقیقه",
    )
    add(
        "اضافه‌کاری روز تعطیل",
        "overtime_off",
        current.get("overtime", {}).get("off_day_minutes", 0),
        previous.get("overtime", {}).get("off_day_minutes", 0),
        "دقیقه",
    )
    add(
        "اضافه‌کاری روز کاری",
        "overtime_regular",
        current.get("overtime", {}).get("regular_day_minutes", 0),
        previous.get("overtime", {}).get("regular_day_minutes", 0),
        "دقیقه",
    )
    add(
        "میانه زمان سپری‌شده",
        "lead_time",
        current.get("lead_time_median_minutes"),
        previous.get("lead_time_median_minutes"),
        "دقیقه",
    )
    add(
        "مطالعه",
        "study",
        current.get("study_minutes", 0),
        previous.get("study_minutes", 0),
        "دقیقه",
    )
    return {"has_previous": True, "rows": rows}


def export_markdown(review: Review) -> str:
    """Render the review as Markdown."""
    stats = review.stats or {}
    counts = stats.get("counts", {})
    lines: list[str] = [
        f"# ارزیابی {review.period_type} — {review.period_start} تا {review.period_end}",
        "",
        "## آمار",
        "",
        f"- انجام‌شده: {counts.get('completed', 0)}",
        f"- نرخ تکمیل: {counts.get('completion_rate', 0)}٪",
        f"- زمان اندازه‌گیری‌شده: {format_minutes(stats.get('measured_minutes_total', 0))}",
        f"- زمان تخمینی: {format_minutes(stats.get('estimated_minutes_total', 0))}",
        f"- زمان سپری‌شده: {format_minutes(stats.get('elapsed_minutes_total', 0))}",
        "",
        "### زمان اندازه‌گیری‌شده بر اساس نوع",
        "",
    ]
    for kind, minutes in sorted((stats.get("measured_minutes_by_kind") or {}).items()):
        lines.append(f"- {kind}: {format_minutes(minutes)}")
    overtime = stats.get("overtime", {})
    lines += [
        "",
        "## اضافه‌کاری",
        "",
        f"- روز تعطیل: {format_minutes(overtime.get('off_day_minutes', 0))}",
        f"- روز کاری: {format_minutes(overtime.get('regular_day_minutes', 0))}",
        "",
        "## دلایل",
        "",
    ]
    for reason, minutes in sorted((overtime.get("reasons") or {}).items()):
        lines.append(f"- {reason}: {format_minutes(minutes)}")
    if review.rating is not None:
        lines += ["", f"**امتیاز: {review.rating} از ۵**"]
    if review.user_final_md.strip():
        lines += ["", "## متن نهایی", "", review.user_final_md.strip()]
    return "\n".join(lines) + "\n"
