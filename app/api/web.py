"""Page routes for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, base_context
from app.config import get_settings
from app.i18n import t
from app.services import dashboard as dashboard_service
from app.services import settings as settings_service
from app.templating import templates
from app.utils.time import utcnow

router = APIRouter()

KIND_LABELS = {
    "work": "time.kind.work",
    "overtime": "time.kind.overtime",
    "study": "time.kind.study",
    "learning": "time.kind.learning",
}


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
    context = base_context(
        request,
        session,
        active_page="dashboard",
        stats=stats,
        chart_labels=[t(KIND_LABELS[kind]) for kind in kinds],
        chart_values=[stats.hours_by_kind[kind] for kind in kinds],
        ai_enabled=get_settings().ai_enabled,
    )
    return templates.TemplateResponse(request, "dashboard.html", context)
