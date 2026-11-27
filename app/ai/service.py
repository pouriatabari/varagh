"""The AI features.

Every feature builds its own payload out of the database, asks the provider
for JSON and validates the answer against a strict Pydantic schema. The AI
never invents numbers: every figure it may use is part of the payload.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.ai import charts as chart_service
from app.ai.provider import AIError, AIProvider
from app.ai.schemas import (
    AnswerDraft,
    ClassificationDraft,
    DailyPlanDraft,
    JournalProposal,
    QuickAddDraft,
    ReviewDraft,
    SyllabusDraft,
)
from app.models.system import AIRun

logger = logging.getLogger("varagh.ai.features")

JSON_ONLY = (
    "Answer with a single JSON object and nothing else. "
    "Do not wrap the JSON in Markdown fences. "
    "Only use the numbers given in the payload; never invent a figure."
)

PERSIAN = "Write the human-readable text in Persian (Farsi)."

CHARTS = (
    "You may also return charts: a list of {type (bar|line|doughnut|pie), "
    "series (the name of one of the series of the payload), title_fa (a short "
    "Persian title), basis (measured|estimated|elapsed)}. A series already "
    "carries its labels and its values; never send numbers yourself."
)

SYSTEM_PROMPTS: dict[str, str] = {
    "parse_quick_add": (
        "You parse a short Persian note into a task. "
        "Return JSON with: title, due_at (ISO 8601 or null), priority (0-3), "
        "context (company|personal|learning), origin (self_initiated|assigned), "
        "assigned_by (string or null), effort_minutes_estimate (integer or null), "
        "note_md (string). " + JSON_ONLY
    ),
    "parse_daily_journal": (
        "You parse a free-text Persian journal into structured entries. "
        "Return JSON with: entries (list of {text, minutes (int or null), "
        "kind (work|overtime|study|learning), task_id (int or null)}), "
        "summary_fa (string). Only use task ids that appear in the payload. " + JSON_ONLY
    ),
    "classify_task": (
        "You suggest one to three domains for a task. Prefer the domains that "
        "already exist. Return JSON with: domains (list of strings). " + JSON_ONLY
    ),
    "parse_syllabus": (
        "You split a syllabus into an ordered list of units. "
        "Return JSON with: units (list of strings). " + JSON_ONLY
    ),
    "daily_plan": (
        "You propose a plan for today out of the tasks given in the payload. "
        "Return JSON with: plan (list of {title, task_id (int or null), "
        "minutes (int or null), note_fa (string)}), summary_fa (string). "
        "Only use task ids that appear in the payload. " + CHARTS + " " + JSON_ONLY + " " + PERSIAN
    ),
    "review_draft": (
        "You write the draft of a periodic review out of the statistics given "
        "in the payload. Return JSON with: achievements_technical and "
        "achievements_work (lists of {title, description_fa, task_ids (list of "
        "int), impact_fa, virtue (one of prowess, valor, wisdom, loyalty, "
        "largesse, temperance), domain (the name of the craft), "
        "suggested_tier (bronze, silver or gold), concrete (bool), "
        "confidence (number between 0 and 1)}), comparison (string), "
        "bottlenecks (list of strings), "
        "suggestions (list of strings), narrative_fa (string). Only use task "
        "ids that appear in the payload; never invent a number. "
        + CHARTS
        + " "
        + JSON_ONLY
        + " "
        + PERSIAN
    ),
    "ask_my_data": (
        "You answer a question about the personal data given in the payload. "
        "Return JSON with: answer_fa (string), used_task_ids (list of int), "
        "used_dates (list of strings). Use only the data in the payload. "
        + CHARTS
        + " "
        + JSON_ONLY
        + " "
        + PERSIAN
    ),
}


def _log_run(
    session: Session,
    *,
    feature: str,
    provider: AIProvider,
    ok: bool,
    error: str | None = None,
) -> None:
    """Record the call in ``ai_runs``."""
    run = AIRun(
        feature=feature,
        model=getattr(provider, "model", "") or "",
        ok=ok,
        error=error,
    )
    session.add(run)
    session.flush()


def _call(
    session: Session,
    provider: AIProvider,
    *,
    feature: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Call the provider and log the call."""
    try:
        answer = provider.complete_json(feature, SYSTEM_PROMPTS[feature], payload)
    except AIError as exc:
        _log_run(session, feature=feature, provider=provider, ok=False, error=str(exc))
        raise
    except Exception as exc:  # any provider failure is logged and re-raised
        _log_run(session, feature=feature, provider=provider, ok=False, error=str(exc))
        raise AIError(str(exc)) from exc
    _log_run(session, feature=feature, provider=provider, ok=True)
    return answer


def _validate(model: type, answer: dict[str, Any]) -> Any:
    """Validate the answer of the model against a strict schema."""
    try:
        return model.model_validate(answer)
    except ValidationError as exc:
        raise AIError(f"the model returned an invalid answer: {exc}") from exc


def parse_quick_add(
    session: Session, provider: AIProvider, text: str, *, now: datetime
) -> QuickAddDraft:
    """Turn a quick-add string into a task draft."""
    payload = {"text": text, "now": now.isoformat()}
    answer = _call(session, provider, feature="parse_quick_add", payload=payload)
    return _validate(QuickAddDraft, answer)


def parse_daily_journal(
    session: Session, provider: AIProvider, text: str, *, now: datetime
) -> JournalProposal:
    """Propose the entries of a journal; nothing is written before confirmation."""
    payload = {"text": text, "now": now.isoformat()}
    answer = _call(session, provider, feature="parse_daily_journal", payload=payload)
    return _validate(JournalProposal, answer)


def classify_task(
    session: Session,
    provider: AIProvider,
    *,
    title: str,
    description_md: str = "",
    existing_domains: list[str] | None = None,
) -> ClassificationDraft:
    """Suggest one to three domains for a task."""
    payload = {
        "title": title,
        "description_md": description_md,
        "existing_domains": existing_domains or [],
    }
    answer = _call(session, provider, feature="classify_task", payload=payload)
    return _validate(ClassificationDraft, answer)


def parse_syllabus(session: Session, provider: AIProvider, text: str) -> SyllabusDraft:
    """Split a syllabus into units."""
    payload = {"syllabus": text}
    answer = _call(session, provider, feature="parse_syllabus", payload=payload)
    return _validate(SyllabusDraft, answer)


def daily_plan(session: Session, provider: AIProvider, payload: dict[str, Any]) -> DailyPlanDraft:
    """Propose the plan of the day."""
    answer = _call(session, provider, feature="daily_plan", payload=payload)
    draft = _validate(DailyPlanDraft, answer)
    chart_service.validate_charts(draft.charts, payload)
    return draft


def review_draft(session: Session, provider: AIProvider, stats: dict[str, Any]) -> ReviewDraft:
    """Draft a review out of the statistics of a period.

    The draft is rejected when it cites a task id that is not part of the
    statistics: the AI may not talk about tasks it did not see.
    """
    payload = review_payload(stats)
    answer = _call(session, provider, feature="review_draft", payload=payload)
    draft = _validate(ReviewDraft, answer)
    known_ids = {int(row["id"]) for row in stats.get("tasks", []) if "id" in row}
    for achievement in list(draft.achievements_technical) + list(draft.achievements_work):
        unknown = [task_id for task_id in achievement.task_ids if task_id not in known_ids]
        if unknown:
            raise AIError(f"the draft cites unknown task ids: {sorted(unknown)}")
    chart_service.validate_charts(draft.charts, payload)
    return draft


def ask_my_data(
    session: Session, provider: AIProvider, question: str, data: dict[str, Any]
) -> AnswerDraft:
    """Answer a question about the personal data."""
    payload = ask_payload(question, data)
    answer = _call(session, provider, feature="ask_my_data", payload=payload)
    draft = _validate(AnswerDraft, answer)
    chart_service.validate_charts(draft.charts, payload)
    return draft


def review_payload(stats: dict[str, Any]) -> dict[str, Any]:
    """Build the payload of the review draft."""
    return {"stats": stats, "series": stats.get("series", {})}


def ask_payload(question: str, data: dict[str, Any]) -> dict[str, Any]:
    """Build the payload of the «ask my data» feature."""
    return {"question": question, "data": data, "series": data.get("series", {})}


def draft_to_dict(draft: Any, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Render a draft as plain JSON data.

    When the payload is given, the charts of the draft are resolved against
    it: the labels and the values come from the database, not from the model.
    """
    if hasattr(draft, "model_dump"):
        data = draft.model_dump(mode="json")
    else:
        data = json.loads(json.dumps(draft, default=str))
    if payload is not None:
        charts = getattr(draft, "charts", [])
        data["charts"] = chart_service.resolve_charts(charts, payload)
    return data
