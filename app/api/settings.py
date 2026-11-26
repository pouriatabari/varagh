"""The settings page: display options, notifications and holidays."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.deps import SessionDep, base_context
from app.api.forms import form_bool, form_int, form_str
from app.services import holidays as holiday_service
from app.services import settings as settings_service
from app.templating import templates

router = APIRouter()


@router.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the settings page."""
    context = base_context(
        request,
        session,
        active_page="settings",
        settings=settings_service.get_all_settings(session),
        notification_config=settings_service.notification_settings(session),
        holidays=holiday_service.list_holidays(),
    )
    return templates.TemplateResponse(request, "settings.html", context)


@router.post("/settings/general")
async def settings_general(request: Request, session: SessionDep) -> JSONResponse:
    """Save the general display settings."""
    form = await request.form()
    weekend = [index for index in range(7) if form_bool(form, f"weekend_{index}")]
    values = {
        "timezone": form_str(form, "timezone") or "Asia/Tehran",
        "calendar_system": form_str(form, "calendar_system") or "jalali",
        "digits": form_str(form, "digits") or "persian",
        "weekly_hour_target": form_int(form, "weekly_hour_target", 40) or 40,
        "weekend_weekdays": weekend or [6],
    }
    settings_service.update_settings(session, values)
    return JSONResponse({"ok": True})


@router.post("/settings/holidays/add")
async def settings_holiday_add(request: Request, session: SessionDep) -> JSONResponse:
    """Add a holiday to the user holiday file."""
    form = await request.form()
    date_text = form_str(form, "date")
    title = form_str(form, "title")
    if not date_text or not title:
        return JSONResponse({"ok": False, "error": "date and title are required"}, status_code=400)
    holiday = holiday_service.add_holiday(date_text, title)
    if holiday is None:
        return JSONResponse({"ok": False, "error": "invalid date"}, status_code=400)
    return JSONResponse({"ok": True, "date": holiday.date, "title": holiday.title})


@router.post("/settings/holidays/remove")
async def settings_holiday_remove(request: Request, session: SessionDep) -> JSONResponse:
    """Remove a holiday from the user holiday file."""
    form = await request.form()
    date_text = form_str(form, "date")
    if not holiday_service.remove_holiday(date_text):
        return JSONResponse({"ok": False, "error": "unknown holiday"}, status_code=404)
    return JSONResponse({"ok": True})


@router.post("/settings/holidays")
async def settings_holidays(request: Request, session: SessionDep) -> JSONResponse:
    """Replace the whole holiday file with the submitted list."""
    form = await request.form()
    raw = form_str(form, "holidays")
    try:
        payload = json.loads(raw) if raw else {"holidays": []}
    except json.JSONDecodeError:
        return JSONResponse({"ok": False, "error": "invalid json"}, status_code=400)
    items = payload.get("holidays", []) if isinstance(payload, dict) else []
    if not isinstance(items, list):
        return JSONResponse({"ok": False, "error": "invalid payload"}, status_code=400)
    holidays = holiday_service.replace_holidays(items)
    return JSONResponse({"ok": True, "holidays": len(holidays)})
