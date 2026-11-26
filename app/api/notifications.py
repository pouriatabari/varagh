"""Notification endpoints used by the browser and the settings page."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.deps import SessionDep
from app.api.forms import form_bool, form_int, form_str
from app.config import get_settings
from app.i18n import t
from app.models.system import NotificationLog
from app.notify import channels as channel_module
from app.notify.messages import Notification
from app.services import settings as settings_service
from app.utils.time import utcnow

router = APIRouter()


def _form_config(form: Any) -> dict[str, Any]:
    """Build the notification configuration from a submitted form."""
    return {
        "due_soon_minutes": form_int(form, "due_soon_minutes", 0) or 0,
        "overdue_enabled": form_bool(form, "overdue_enabled"),
        "digest_enabled": form_bool(form, "digest_enabled"),
        "digest_time": form_str(form, "digest_time") or "20:00",
        "journal_nudge_enabled": form_bool(form, "journal_nudge_enabled"),
        "journal_nudge_time": form_str(form, "journal_nudge_time") or "21:30",
        "review_reminder_enabled": form_bool(form, "review_reminder_enabled"),
        "stale_learning_enabled": form_bool(form, "stale_learning_enabled"),
        "stale_learning_days": form_int(form, "stale_learning_days", 30) or 30,
        "channels": {
            "browser": form_bool(form, "channel_browser"),
            "email": form_bool(form, "channel_email"),
            "webhook": form_bool(form, "channel_webhook"),
        },
        "email": {
            "to": form_str(form, "email_to"),
            "host": form_str(form, "email_host"),
            "port": form_int(form, "email_port", 587) or 587,
            "user": form_str(form, "email_user"),
            "password": form_str(form, "email_password"),
            "use_tls": form_bool(form, "email_use_tls"),
            "from": form_str(form, "email_from"),
        },
        "webhook": {
            "url": form_str(form, "webhook_url"),
            "format": form_str(form, "webhook_format") or "slack",
        },
    }


@router.get("/api/notifications/due")
async def notifications_due(session: SessionDep) -> JSONResponse:
    """Return the notifications the browser has not seen yet."""
    rows = session.scalars(
        select(NotificationLog)
        .where(
            NotificationLog.channel == "browser",
            NotificationLog.delivered_at.is_(None),
        )
        .order_by(NotificationLog.sent_at.asc())
    ).all()
    payload = []
    for row in rows:
        body = row.payload or {}
        payload.append(
            {
                "id": row.id,
                "kind": row.kind,
                "title": str(body.get("title", row.kind)),
                "body": str(body.get("body", "")),
                "url": str(body.get("url", "/")),
            }
        )
    return JSONResponse({"notifications": payload})


@router.post("/api/notifications/{notification_id}/read")
async def notifications_read(notification_id: int, session: SessionDep) -> JSONResponse:
    """Mark a notification as seen by the browser."""
    row = session.get(NotificationLog, notification_id)
    if row is not None and row.delivered_at is None:
        row.delivered_at = utcnow()
        session.flush()
    return JSONResponse({"ok": True})


@router.post("/api/notifications/test/{channel}")
async def notifications_test(channel: str, session: SessionDep) -> JSONResponse:
    """Send a test notification on the given channel."""
    now = utcnow()
    notification = Notification(
        kind="test",
        ref_id=0,
        title=t("notify.test.title"),
        body=t("notify.test.body"),
        window_key=f"test-{now.isoformat()}",
        url="/settings",
    )
    config = settings_service.notification_settings(session)
    if channel == "email":
        email_config = config.get("email", {}) or {}
        sender: channel_module.Channel = channel_module.EmailChannel(session, now, email_config)
    elif channel == "webhook":
        webhook_config = config.get("webhook", {}) or {}
        env = get_settings()
        sender = channel_module.WebhookChannel(
            session,
            now,
            str(webhook_config.get("url") or env.webhook_url),
            str(webhook_config.get("format") or env.webhook_format),
        )
    else:
        return JSONResponse({"ok": False, "error": "unknown channel"}, status_code=400)
    ok = sender.send(notification)
    return JSONResponse({"ok": ok}, status_code=200 if ok else 502)


@router.post("/settings/notifications")
async def settings_notifications(request: Request, session: SessionDep) -> JSONResponse:
    """Save the notification settings."""
    form = await request.form()
    config = _form_config(form)
    settings_service.update_settings(session, {"notifications": config})
    return JSONResponse({"ok": True})
