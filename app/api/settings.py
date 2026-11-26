"""The settings page: display options, the AI provider, notifications and holidays."""

from __future__ import annotations

import json
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from markupsafe import escape
from sqlalchemy.orm import Session

from app.ai import config as ai_config
from app.ai.provider import AIError, build_provider
from app.api.deps import SessionDep, base_context
from app.api.forms import form_bool, form_float, form_int, form_str
from app.i18n import t
from app.services import export as export_service
from app.services import holidays as holiday_service
from app.services import settings as settings_service
from app.templating import templates

router = APIRouter()

TEST_SYSTEM_PROMPT = 'Answer with a single JSON object: {"ok": true}.'


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
        ai_config=_ai_view(session),
    )
    return templates.TemplateResponse(request, "settings.html", context)


def _ai_view(session: Session) -> dict[str, Any]:
    """Return the AI configuration for the page; the key itself is never sent."""
    config = ai_config.load_config(session)
    return {
        "enabled": config.enabled,
        "provider": config.provider,
        "model": config.model,
        "base_url": config.base_url,
        "timeout_seconds": config.timeout_seconds,
        "max_output_tokens": config.max_output_tokens,
        "auth_header": config.auth_header,
        "custom_url": config.custom_url,
        "custom_method": config.custom_method,
        "custom_headers": config.custom_headers,
        "has_api_key": bool(config.api_key),
        "source": ai_config.config_source(session),
    }


def _ai_values(form: Any, session: Session) -> dict[str, Any]:
    """Read the AI configuration out of a submitted form."""
    current = ai_config.load_config(session)
    api_key = form_str(form, "api_key")
    if not api_key and not form_bool(form, "clear_api_key"):
        api_key = current.api_key
    timeout = form_float(form, "timeout_seconds", ai_config.DEFAULT_TIMEOUT_SECONDS)
    tokens = form_int(form, "max_output_tokens", ai_config.DEFAULT_MAX_OUTPUT_TOKENS)
    return {
        "enabled": form_bool(form, "enabled"),
        "provider": form_str(form, "provider") or "anthropic",
        "api_key": api_key,
        "model": form_str(form, "model"),
        "base_url": form_str(form, "base_url"),
        "timeout_seconds": int(timeout) if timeout else ai_config.DEFAULT_TIMEOUT_SECONDS,
        "max_output_tokens": tokens or ai_config.DEFAULT_MAX_OUTPUT_TOKENS,
        "auth_header": form_str(form, "auth_header") or "both",
        "custom_url": form_str(form, "custom_url"),
        "custom_method": form_str(form, "custom_method") or "json",
        "custom_headers": form_str(form, "custom_headers"),
    }


def _valid_ai_values(values: dict[str, Any]) -> str | None:
    """Return the name of the first invalid field."""
    if values["provider"] not in ai_config.PROVIDERS:
        return "provider"
    if values["custom_method"] not in ai_config.CUSTOM_METHODS:
        return "custom_method"
    if values["auth_header"] not in ai_config.AUTH_HEADERS:
        return "auth_header"
    return None


@router.post("/settings/ai", response_class=HTMLResponse)
async def settings_ai(request: Request, session: SessionDep) -> HTMLResponse:
    """Save the AI provider configuration."""
    form = await request.form()
    values = _ai_values(form, session)
    invalid = _valid_ai_values(values)
    if invalid:
        return HTMLResponse(f'<p class="muted">{escape(t("ai.invalid"))}</p>', status_code=400)
    settings_service.update_settings(session, {"ai": values})
    return HTMLResponse(f'<p class="muted">{escape(t("ai.saved"))}</p>')


@router.post("/settings/ai/test", response_class=HTMLResponse)
async def settings_ai_test(request: Request, session: SessionDep) -> HTMLResponse:
    """Try a call with the configuration of the form."""
    form = await request.form()
    values = _ai_values(form, session)
    if _valid_ai_values(values):
        return HTMLResponse(f'<p class="muted">{escape(t("ai.invalid"))}</p>', status_code=400)
    config = ai_config.config_from_values(values)
    provider = build_provider(config)
    if provider is None:
        return HTMLResponse(
            f'<p class="muted">{escape(t("ai.test_incomplete"))}</p>',
            status_code=400,
        )
    try:
        provider.complete_json("test", TEST_SYSTEM_PROMPT, {"ping": "pong"})
    except AIError as exc:
        return HTMLResponse(
            f'<p class="muted">{escape(t("ai.test_failed"))} {escape(str(exc))}</p>',
            status_code=502,
        )
    return HTMLResponse(f'<p class="muted">{escape(t("ai.test_ok"))}</p>')


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


@router.get("/export.json")
async def export_json(session: SessionDep) -> JSONResponse:
    """Export the whole database as JSON."""
    payload = export_service.export_all(session)
    return JSONResponse(
        payload,
        headers={"Content-Disposition": 'attachment; filename="varagh-export.json"'},
    )
