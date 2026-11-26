"""Page routes for the dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, base_context
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the dashboard page."""
    context = base_context(request, session, active_page="dashboard")
    return templates.TemplateResponse(request, "dashboard.html", context)
