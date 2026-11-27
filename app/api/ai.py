"""AI routes: every feature is optional and always goes through the provider."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.ai.provider import AIError, get_provider
from app.api.deps import SessionDep, base_context
from app.api.forms import form_str
from app.i18n import translate
from app.models.task import Task
from app.services import achievements as achievement_service
from app.services import dashboard as dashboard_service
from app.services import learning as learning_service
from app.services import reviews as review_service
from app.services import settings as settings_service
from app.services import tasks as task_service
from app.templating import templates
from app.utils.time import utcnow

router = APIRouter()


def _redirect(url: str, flash: str | None = None, error: str | None = None) -> RedirectResponse:
    """Redirect back to a page, optionally carrying a flash message."""
    params = []
    if flash:
        params.append(f"flash={flash}")
    if error:
        params.append(f"error={error}")
    if params:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}{'&'.join(params)}"
    return RedirectResponse(url, status_code=303)


def _failure(
    session: Session, detail: str, status: int, key: str = "error.ai_failed"
) -> JSONResponse:
    """The answer of a call that did not work.

    The sentence is in the lexicon of the user; the detail keeps the
    words of the provider, so the page can show both.
    """
    lexicon = settings_service.lexicon(session)
    return JSONResponse(
        {
            "ok": False,
            "error": detail,
            "message": str(translate(key, lexicon)),
        },
        status_code=status,
    )


def _no_provider(session: Session) -> JSONResponse:
    """The answer when the AI is not configured."""
    return _failure(session, "error.ai_disabled", 503, key="error.ai_disabled")


@router.get("/api/ai/daily-plan")
async def ai_daily_plan(session: SessionDep) -> JSONResponse:
    """The plan the AI proposes for today."""
    provider = get_provider(session)
    if provider is None:
        return _no_provider(session)
    timezone = settings_service.timezone_name(session)
    now = utcnow()
    stats = dashboard_service.collect_stats(
        session, now=now, timezone=timezone, weekly_target_hours=0
    )
    open_tasks = task_service.list_tasks(
        session, task_service.TaskFilters(status="open"), now=now, timezone=timezone
    )
    series = dashboard_service.build_series(session, now=now, timezone=timezone, days=14)
    payload = {
        "today": now.date().isoformat(),
        "measured_minutes_today": stats.weekly_measured_minutes,
        "series": series,
        "open_tasks": [
            {
                "id": task.id,
                "title": task.title,
                "priority": task.priority,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "estimate_minutes": task.effort_minutes_estimate,
            }
            for task in open_tasks[:50]
        ],
    }
    try:
        draft = ai_service.daily_plan(session, provider, payload)
    except AIError as exc:
        return _failure(session, str(exc), 502)
    plan = ai_service.draft_to_dict(draft, payload)
    return JSONResponse({"ok": True, "plan": plan}, status_code=200)


@router.post("/api/ai/parse-quick-add")
async def ai_parse_quick_add(request: Request, session: SessionDep) -> JSONResponse:
    """Parse a quick-add string into a task draft; nothing is created."""
    provider = get_provider(session)
    if provider is None:
        return _no_provider(session)
    form = await request.form()
    text = form_str(form, "text")
    if not text:
        return _failure(session, "error.validation", 400, key="error.validation")
    try:
        draft = ai_service.parse_quick_add(session, provider, text, now=utcnow())
    except AIError as exc:
        return _failure(session, str(exc), 502)
    return JSONResponse({"ok": True, "draft": ai_service.draft_to_dict(draft)})


@router.post("/api/ai/classify-task/{task_id}")
async def ai_classify_task(request: Request, task_id: int, session: SessionDep) -> JSONResponse:
    """Suggest the domains of a task; the user's choice always wins."""
    provider = get_provider(session)
    if provider is None:
        return _no_provider(session)
    task = task_service.get_task(session, task_id)
    if task is None:
        return _failure(session, "error.not_found", 404, key="error.not_found")
    domains = [domain.name for domain in task_service.list_domains(session)]
    try:
        draft = ai_service.classify_task(
            session,
            provider,
            title=task.title,
            description_md=task.description_md,
            existing_domains=domains,
        )
    except AIError as exc:
        return _failure(session, str(exc), 502)
    return JSONResponse({"ok": True, "domains": draft.domains})


@router.post("/api/ai/journal")
async def ai_journal(request: Request, session: SessionDep) -> JSONResponse:
    """Propose the entries of a journal; nothing is written before confirmation."""
    provider = get_provider(session)
    if provider is None:
        return _no_provider(session)
    form = await request.form()
    text = form_str(form, "raw_text")
    if not text:
        return _failure(session, "error.validation", 400, key="error.validation")
    try:
        draft = ai_service.parse_daily_journal(session, provider, text, now=utcnow())
    except AIError as exc:
        return _failure(session, str(exc), 502)
    return JSONResponse({"ok": True, "proposal": ai_service.draft_to_dict(draft)})


@router.post("/learning/{item_id}/syllabus")
async def ai_parse_syllabus(
    request: Request, item_id: int, session: SessionDep
) -> RedirectResponse:
    """Parse a syllabus into units with the AI."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    provider = get_provider(session)
    if provider is None:
        return _redirect(f"/learning/{item.id}", error="error.ai_disabled")
    form = await request.form()
    syllabus = form_str(form, "syllabus")
    if not syllabus:
        return _redirect(f"/learning/{item.id}", error="error.validation")
    try:
        draft = ai_service.parse_syllabus(session, provider, syllabus)
    except AIError:
        return _redirect(f"/learning/{item.id}", error="error.ai_failed")
    learning_service.set_units(session, item, draft.units)
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")


@router.post("/reviews/{review_id}/ai-draft")
async def ai_review_draft(
    request: Request, review_id: int, session: SessionDep
) -> RedirectResponse:
    """Draft a review out of its statistics snapshot."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    provider = get_provider(session)
    if provider is None:
        return _redirect(f"/reviews/{review.id}", error="error.ai_disabled")
    stats = review.stats or {}
    payload = ai_service.review_payload(stats)
    try:
        draft = ai_service.review_draft(session, provider, stats)
    except AIError:
        return _redirect(f"/reviews/{review.id}", error="error.ai_failed")
    draft_data = ai_service.draft_to_dict(draft, payload)
    proposals = []
    for kind, items in (
        ("technical", draft.achievements_technical),
        ("work", draft.achievements_work),
    ):
        for item in items:
            achievement = _create_achievement(session, review, item, kind)
            proposals.append(
                {
                    "title": item.title,
                    "description": item.description_fa,
                    "virtue": item.virtue,
                    "domain": item.domain,
                    "tier": item.suggested_tier,
                    "evidence_task_ids": list(item.task_ids),
                    "impact_note": item.impact_fa,
                    "concrete": item.concrete,
                    "confidence": item.confidence,
                    "achievement_id": achievement.id,
                }
            )
    # The proposals of the medals travel with the draft: the user may
    # lower a tier before the muster is confirmed, and the server checks
    # the tier against the evidence when it gives the medal.
    draft_data["medal_proposals"] = proposals
    review_service.update_review(session, review, ai_draft=draft_data)
    return _redirect(f"/reviews/{review.id}", flash="flash.review_updated")


def _create_achievement(session: Session, review: Any, item: Any, kind: str) -> Any:
    """Store one achievement proposed by the AI.

    The achievement is the record of what the muster saw; the medal that
    goes with it is given when the muster is confirmed.
    """
    return achievement_service.create_achievement(
        session,
        title=item.title,
        description_md=item.description_fa,
        kind=kind,
        period_start=review.period_start,
        period_end=review.period_end,
        impact_note=item.impact_fa or None,
        task_ids=item.task_ids,
    )


@router.get("/ask", response_class=HTMLResponse)
async def ask_page(request: Request, session: SessionDep) -> HTMLResponse:
    """The «ask my data» page."""
    context = base_context(
        request, session, active_page="", ai_enabled=get_provider() is not None, answer=None
    )
    return templates.TemplateResponse(request, "ask.html", context)


@router.post("/ask", response_class=HTMLResponse)
async def ask_submit(request: Request, session: SessionDep) -> HTMLResponse:
    """Answer a question about the personal data."""
    provider = get_provider(session)
    form = await request.form()
    question = form_str(form, "question")
    answer: dict[str, Any] | None = None
    error: str | None = None
    if provider is None:
        error = "error.ai_disabled"
    elif not question:
        error = "error.validation"
    else:
        try:
            data = _data_payload(session)
            draft = ai_service.ask_my_data(session, provider, question, data)
            answer = ai_service.draft_to_dict(draft, ai_service.ask_payload(question, data))
        except AIError:
            error = "error.ai_failed"
    context = base_context(
        request,
        session,
        active_page="",
        ai_enabled=provider is not None,
        answer=answer,
        error=error,
        question=question,
    )
    return templates.TemplateResponse(request, "ask.html", context)


def _data_payload(session: Session) -> dict[str, Any]:
    """Build the data the AI may look at."""
    tasks = session.scalars(
        select(Task).where(Task.deleted_at.is_(None)).order_by(Task.created_at.desc()).limit(200)
    ).all()
    items = learning_service.list_items(session)
    now = utcnow()
    timezone = settings_service.timezone_name(session)
    return {
        "today": date.today().isoformat(),
        "series": dashboard_service.build_series(session, now=now, timezone=timezone, days=30),
        "tasks": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "context": task.context,
                "origin": task.origin,
                "priority": task.priority,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "estimate_minutes": task.effort_minutes_estimate,
            }
            for task in tasks
        ],
        "learning_items": [
            {
                "id": item.id,
                "title": item.title,
                "kind": item.kind,
                "status": item.status,
            }
            for item in items
        ],
    }
