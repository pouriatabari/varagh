"""Review routes: the wizard, the saved reviews and the Markdown export."""

from __future__ import annotations

from collections.abc import Callable
from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import SessionDep, base_context
from app.api.forms import form_bool, form_int, form_str
from app.i18n import t, translate
from app.security import validate_csrf
from app.services import achievements as achievement_service
from app.services import charts as chart_service
from app.services import court, heraldry, honours, rewards, rewards_config
from app.services import reviews as review_service
from app.services import settings as settings_service
from app.services.rewards_config import VIRTUES, RewardsConfig
from app.templating import templates
from app.utils.time import utcnow

router = APIRouter(dependencies=[Depends(validate_csrf)])


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
    rows = review_service.list_reviews(session)
    charts = chart_service.build_charts(
        [
            {
                "type": "bar",
                "series": "rating_by_review",
                "title_fa": t("reviews.rating_chart"),
                "basis": "measured",
            }
        ],
        {
            "rating_by_review": {
                "labels": [f"{review.period_start} → {review.period_end}" for review in rows],
                "values": [float(review.rating or 0) for review in rows],
                "unit": "units.rating",
            }
        },
        id_prefix="reviews",
    )
    context = base_context(
        request,
        session,
        active_page="reviews",
        reviews=rows,
        review_ids=[review.id for review in rows],
        charts=charts,
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
    charts = chart_service.build_charts(
        [
            {
                "type": "doughnut",
                "series": "measured_minutes_by_kind",
                "title_fa": t("reviews.hours_by_kind"),
                "basis": "measured",
            },
            {
                "type": "bar",
                "series": "measured_minutes_by_day",
                "title_fa": t("reviews.minutes_by_day"),
                "basis": "measured",
            },
        ],
        (review.stats or {}).get("series") or {},
        id_prefix="review",
    )
    context = base_context(
        request,
        session,
        active_page="reviews",
        review=review,
        previous=previous,
        comparison=comparison,
        charts=charts,
        readonly=request.query_params.get("view") == "1",
    )
    return templates.TemplateResponse(request, "review_detail.html", context)


@router.post("/reviews/{review_id}/delete")
async def review_delete(request: Request, review_id: int, session: SessionDep) -> RedirectResponse:
    """Delete a review."""
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    review_service.delete_review(session, review)
    return _redirect("/reviews", flash="flash.review_deleted")


@router.post("/reviews/delete")
async def reviews_delete(request: Request, session: SessionDep) -> RedirectResponse:
    """Delete every review of the selection."""
    form = await request.form()
    ids = [int(value) for value in form.getlist("review_ids") if str(value).isdigit()]
    if not ids:
        return _redirect("/reviews", error="error.validation")
    deleted = 0
    for review_id in ids:
        review = review_service.get_review(session, review_id)
        if review is None:
            continue
        review_service.delete_review(session, review)
        deleted += 1
    if not deleted:
        return _redirect("/reviews", error="error.not_found")
    return _redirect(f"/reviews?flash=flash.reviews_deleted&count={deleted}")


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


@router.post("/reviews/{review_id}/confirm", response_class=HTMLResponse)
async def review_confirm(
    request: Request, review_id: int, session: SessionDep
) -> HTMLResponse:
    """Confirm a muster and give the medals it earned.

    Nothing is given before this moment: the proposals of the AI wait as
    a draft, the user may lower a tier, and the server checks the tier
    against the evidence before the medal is written.
    """
    review = review_service.get_review(session, review_id)
    if review is None:
        return _redirect("/reviews", error="error.not_found")
    if review.status == "finished":
        return _redirect(f"/reviews/{review.id}")
    form = await request.form()
    config = rewards_config.load_config()
    proposals = []
    raw = (review.ai_draft or {}).get("medal_proposals") or []
    for index, item in enumerate(raw):
        tier = form_str(form, f"tier_{index}") or item.get("tier") or "bronze"
        concrete = form_bool(form, f"concrete_{index}") or bool(item.get("concrete"))
        proposals.append(
            honours.MedalProposal(
                title=str(item.get("title") or ""),
                virtue=str(item.get("virtue") or "prowess"),
                tier=tier if tier in rewards.TIERS else "bronze",
                domain_name=str(item.get("domain") or "") or None,
                evidence_task_ids=tuple(item.get("evidence_task_ids") or ()),
                impact_note=str(item.get("impact_note") or "") or None,
                concrete=concrete,
                confidence=float(item.get("confidence") or 0.0),
                description_md=str(item.get("description") or ""),
            )
        )
    result = honours.award_medals(session, review=review, proposals=proposals, config=config)
    for medal, proposal in zip(result.created, proposals, strict=False):
        achievement_id = (raw[proposals.index(proposal)] or {}).get("achievement_id")
        if achievement_id:
            medal.achievement_id = int(achievement_id)
    session.flush()
    review.status = "finished"
    session.flush()
    # The ceremony of the title: when every gate of the next title is
    # met, the app writes the title down by itself.
    honours.promote_if_ready(session, config)
    # The muster is given: the map shows the ceremony of the new realm.
    return _redirect("/realms?ceremony=1", flash="flash.review_updated")


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


def _badge_of(
    state: rewards.TitleState, config: RewardsConfig, lexicon: str, theme: str
) -> str:
    """The badge of the title of the user, with the studs of its degrees."""
    from app.insignia import render_badge

    filled, total = honours.title_studs(config, state)
    name = str(translate(f"title_{state.current}", lexicon))
    return render_badge(
        state.current,
        filled,
        total,
        "lit",
        theme,
        "lg",
        name=name,
        desc=str(translate(f"honours.title.{state.current}", lexicon)),
    )


def _badge_for_title(lexicon: str, theme: str) -> Callable[[str, str], str]:
    """Draw the badge of a title in a state, for the pyramid of the court."""
    from app.insignia import render_badge

    def draw(key: str, state: str) -> str:
        name = str(translate(f"honours.title.{key}", lexicon))
        return render_badge(
            key,
            state=state,
            theme=theme,
            size="sm",
            name=name,
            desc=str(translate(f"title_{key}", lexicon)),
        )

    return draw


def _ribbon_rack(session: Session, lexicon: str, theme: str) -> str:
    """The rack of the six ribbons of the virtues."""
    from app.insignia import render_ribbon_rack

    labels = {
        virtue: str(translate(f"honours.virtue.{virtue}", lexicon))
        for virtue in VIRTUES
    }
    return render_ribbon_rack(
        honours.virtue_tier_counts(session),
        theme,
        "md",
        labels=labels,
    )


@router.get("/achievements", response_class=HTMLResponse)
async def achievement_list(request: Request, session: SessionDep) -> HTMLResponse:
    """The hall of the honours.

    The honours are given by the musters; nothing is registered by hand.
    The page shows the medals, the degrees, the title of the user and the
    gates of the next one.
    """
    rows = achievement_service.list_achievements(session)
    config = rewards_config.load_config()
    lexicon = settings_service.lexicon(session)
    theme = settings_service.theme(session)
    state = honours.title_state(session, config)
    medals = honours.list_medals(session)
    context = base_context(
        request,
        session,
        active_page="achievements",
        achievements=rows,
        achievement_ids=[row.id for row in rows],
        linked_tasks={row.id: achievement_service.linked_task_ids(session, row) for row in rows},
        earned_medals=sum(1 for medal in medals if medal.value_counted > 0),
        honours=state,
        honours_medals=medals,
        honours_config=config,
        court_chart=court.court_chart_svg(
            honours.court_tiers(session, config),
            labels={
                rule.key: str(translate(f"honours.title.{rule.key}", lexicon))
                for rule in config.titles
            },
            badge_for=_badge_for_title(lexicon, theme),
        ),
        round_table=court.round_table_svg(
            honours.seats(session),
            labels={
                seat.virtue: str(translate(f"honours.virtue.{seat.virtue}", lexicon))
                for seat in honours.seats(session)
            },
            centre=str(sum(1 for medal in medals if medal.value_counted > 0)),
        ),
        honours_seats=honours.seats(session),
        heraldry=heraldry.heraldry_svg(
            title_key=state.current,
            domains=honours.top_domains(session),
            virtues=list(state.virtues),
        ),
        insignia_badge=_badge_of(state, config, lexicon, theme),
        insignia_studs=honours.title_studs(config, state),
        insignia_reign=honours.reign_years(session, state.current),
        insignia_rack=_ribbon_rack(session, lexicon, theme),
    )
    return templates.TemplateResponse(request, "achievements.html", context)


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


@router.post("/achievements/{achievement_id}/delete")
async def achievement_delete(
    request: Request, achievement_id: int, session: SessionDep
) -> RedirectResponse:
    """Delete an achievement."""
    achievement = achievement_service.get_achievement(session, achievement_id)
    if achievement is None:
        return _redirect("/achievements", error="error.not_found")
    achievement_service.delete_achievement(session, achievement)
    return _redirect("/achievements", flash="flash.achievement_deleted")


@router.post("/achievements/delete")
async def achievements_delete(request: Request, session: SessionDep) -> RedirectResponse:
    """Delete every achievement of the selection."""
    form = await request.form()
    ids = [int(value) for value in form.getlist("achievement_ids") if str(value).isdigit()]
    if not ids:
        return _redirect("/achievements", error="error.validation")
    deleted = 0
    for achievement_id in ids:
        achievement = achievement_service.get_achievement(session, achievement_id)
        if achievement is None:
            continue
        achievement_service.delete_achievement(session, achievement)
        deleted += 1
    if not deleted:
        return _redirect("/achievements", error="error.not_found")
    return _redirect(f"/achievements?flash=flash.achievements_deleted&count={deleted}")


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
