"""Review routes: the wizard, the saved reviews and the Markdown export."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from app.api.deps import SessionDep, base_context
from app.api.forms import form_int, form_str
from app.services import achievements as achievement_service
from app.services import reviews as review_service
from app.services import settings as settings_service
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


def _period_from_request(request: Request) -> review_service.PeriodSelection:
    """Build the period selection from the query string."""
    calendar_system = settings_service.calendar_system(request.app.state.session)
    return review_service.resolve_period(
        request.app.state.session,
        request.query_params.get("period_type", "month"),
        utcnow().date(),
        calendar_system,
    )


@router.get("/reviews", response_class=HTMLResponse)
async def review_list(request: Request, session: SessionDep) -> HTMLResponse:
    """List the saved reviews."""
    context = base_context(
        request,
        session,
        active_page="reviews",
        reviews=review_service.list_reviews(session),
    )
    return templates.TemplateResponse(request, "reviews.html", context)


@router.get("/reviews/new", response_class=HTMLResponse)
async def review_new(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the first step of the review wizard: the statistics."""
    timezone = settings_service.timezone_name(session)
    calendar_system = settings_service.calendar_system(session)
    period_type = request.query_params.get("period_type", "month")
    period = review_service.resolve_period(session, period_type, utcnow().date(), calendar_system)
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone=timezone
    )
    context = base_context(
        request,
        session,
        active_page="reviews",
        period=period,
        stats=stats,
        period_types=review_service.PERIOD_TYPES,
        ai_enabled=False,
    )
    return templates.TemplateResponse(request, "review_new.html", context)


@router.get("/reviews/stats", response_class=HTMLResponse)
async def review_stats(request: Request, session: SessionDep) -> HTMLResponse:
    """Return the statistics of a period as an HTMX partial."""
    timezone = settings_service.timezone_name(session)
    calendar_system = settings_service.calendar_system(session)
    period_type = request.query_params.get("period_type", "month")
    period = review_service.resolve_period(session, period_type, utcnow().date(), calendar_system)
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone=timezone
    )
    context = base_context(request, session, period=period, stats=stats, ai_enabled=False)
    return templates.TemplateResponse(request, "partials/review_stats.html", context)


@router.post("/reviews")
async def review_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Save a review with its statistics snapshot."""
    timezone = settings_service.timezone_name(session)
    calendar_system = settings_service.calendar_system(session)
    form = await request.form()
    period_type = form_str(form, "period_type") or "month"
    custom_start = _parse_date(form_str(form, "custom_start"))
    custom_end = _parse_date(form_str(form, "custom_end"))
    period = review_service.resolve_period(
        session,
        period_type,
        utcnow().date(),
        calendar_system,
        custom_start=custom_start,
        custom_end=custom_end,
    )
    stats = review_service.compute_stats(
        session, start=period.start, end=period.end, timezone=timezone
    )
    review = review_service.create_review(
        session,
        period=period,
        stats=stats,
        user_final_md=form_str(form, "user_final_md"),
        rating=form_int(form, "rating"),
    )
    return _redirect(f"/reviews/{review.id}", flash="flash.review_created")


@router.get("/reviews/{review_id}", response_class=HTMLResponse)
async def review_detail(request: Request, review_id: int, session: SessionDep) -> HTMLResponse:
    """Show a review with the comparison against the previous period."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    calendar_system = settings_service.calendar_system(session)
    previous = review_service.find_previous_review(session, review, calendar_system)
    comparison = review_service.compare_stats(
        review.stats or {}, previous.stats if previous else None
    )
    context = base_context(
        request,
        session,
        active_page="reviews",
        review=review,
        previous=previous,
        comparison=comparison,
    )
    return templates.TemplateResponse(request, "review_detail.html", context)


@router.post("/reviews/{review_id}")
async def review_update(request: Request, review_id: int, session: SessionDep) -> RedirectResponse:
    """Update the text and the rating of a review."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    form = await request.form()
    review_service.update_review(
        session,
        review,
        user_final_md=form_str(form, "user_final_md"),
        rating=form_int(form, "rating"),
    )
    return _redirect(f"/reviews/{review.id}", flash="flash.review_updated")


@router.post("/reviews/{review_id}/ai-draft")
async def review_ai_draft(request: Request, review_id: int, session: SessionDep) -> Response:
    """Ask the AI provider for a draft; without a provider the user writes it."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    from app.ai.provider import get_provider

    provider = get_provider()
    if provider is None:
        return _redirect(f"/reviews/{review.id}", error="error.ai_disabled")
    draft = provider.review_draft(review.stats or {})
    review_service.update_review(session, review, ai_draft=draft)
    return _redirect(f"/reviews/{review.id}", flash="flash.review_updated")


@router.get("/reviews/{review_id}/export.md", response_class=PlainTextResponse)
async def review_export(request: Request, review_id: int, session: SessionDep) -> PlainTextResponse:
    """Export a review as Markdown."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return PlainTextResponse("", status_code=404)
    markdown = review_service.export_markdown(review)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="review-{review.id}.md"'},
    )


@router.get("/achievements", response_class=HTMLResponse)
async def achievement_list(request: Request, session: SessionDep) -> HTMLResponse:
    """List the achievements."""
    rows = achievement_service.list_achievements(session)
    context = base_context(
        request,
        session,
        active_page="achievements",
        achievements=rows,
        linked_tasks={row.id: achievement_service.linked_task_ids(session, row) for row in rows},
    )
    return templates.TemplateResponse(request, "achievements.html", context)


@router.post("/achievements")
async def achievement_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Create an achievement, grounded in the tasks the user cites."""
    form = await request.form()
    title = form_str(form, "title")
    if not title:
        return _redirect("/achievements", error="error.validation")
    today = utcnow().date()
    task_ids = [int(value) for value in form.getlist("task_ids") if str(value).isdigit()]
    achievement_service.create_achievement(
        session,
        title=title,
        description_md=form_str(form, "description_md"),
        kind=form_str(form, "kind") or "technical",
        period_start=_parse_date(form_str(form, "period_start")) or today,
        period_end=_parse_date(form_str(form, "period_end")) or today,
        impact_note=form_str(form, "impact_note") or None,
        task_ids=task_ids,
    )
    return _redirect("/achievements", flash="flash.achievement_created")


@router.post("/achievements/{achievement_id}/confirm")
async def achievement_confirm(
    request: Request, achievement_id: int, session: SessionDep
) -> RedirectResponse:
    """Confirm an achievement."""
    achievement = achievement_service.get_achievement(session, achievement_id)
    if achievement is None:
        return _redirect("/achievements", error="error.not_found")
    achievement_service.confirm(session, achievement)
    return _redirect("/achievements", flash="flash.achievement_created")


@router.get("/achievements/{achievement_id}/export.md", response_class=PlainTextResponse)
async def achievement_export(
    request: Request, achievement_id: int, session: SessionDep
) -> PlainTextResponse:
    """Export an achievement as Markdown."""
    achievement = achievement_service.get_achievement(session, achievement_id)
    if achievement is None:
        return PlainTextResponse("", status_code=404)
    markdown = achievement_service.export_markdown(session, achievement)
    return PlainTextResponse(
        markdown,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="achievement-{achievement.id}.md"'},
    )


def _parse_date(value: str) -> date | None:
    """Parse an ISO date; returns ``None`` when the value is not a date."""
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
