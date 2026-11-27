"""Page routes for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.ai.config import load_config
from app.api.deps import SessionDep, base_context
from app.i18n import t
from app.services import charts as chart_service
from app.services import dashboard as dashboard_service
from app.services import settings as settings_service
from app.templating import read_manifest, templates
from app.utils.time import utcnow

router = APIRouter()

CHART_DAYS = 30

KIND_LABELS = {
    "work": "time.kind.work",
    "overtime": "time.kind.overtime",
    "study": "time.kind.study",
    "learning": "time.kind.learning",
}


@router.get("/about/credits", response_class=HTMLResponse)
async def credits(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the page that names the sources of the vendored assets."""
    context = base_context(request, session, active_page="credits", icons=read_manifest())
    return templates.TemplateResponse(request, "credits.html", context)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the dashboard page."""
    timezone = settings_service.timezone_name(session)
    now = utcnow()
    stats = dashboard_service.collect_stats(
        session,
        now=now,
        timezone=timezone,
        weekly_target_hours=settings_service.weekly_hour_target(session),
    )
    kinds = sorted(stats.hours_by_kind)
    series = dashboard_service.build_series(
        session, now=now, timezone=timezone, days=CHART_DAYS
    )
    charts = chart_service.build_charts(
        [
            {
                "type": "bar",
                "series": "measured_minutes_by_day",
                "title_fa": t("dashboard.minutes_by_day"),
                "basis": "measured",
            },
            {
                "type": "doughnut",
                "series": "counts_by_context",
                "title_fa": t("dashboard.tasks_by_context"),
                "basis": "measured",
            },
        ],
        series,
        id_prefix="dashboard",
    )
    context = base_context(
        request,
        session,
        active_page="dashboard",
        stats=stats,
        chart_labels=[t(KIND_LABELS[kind]) for kind in kinds],
        chart_values=[stats.hours_by_kind[kind] for kind in kinds],
        charts=charts,
        ai_enabled=load_config(session).usable,
    )
    return templates.TemplateResponse(request, "dashboard.html", context)
