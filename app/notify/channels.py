"""Notification channels.

The browser channel only writes to ``notification_log``; the open page polls
it and raises the real OS notification. That is deliberate: a Docker container
cannot notify the host operating system.
"""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage
from typing import Any, Protocol

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.system import NotificationLog
from app.notify.messages import Notification

logger = logging.getLogger("varagh.notify")

BROWSER = "browser"
EMAIL = "email"
WEBHOOK = "webhook"


class Channel(Protocol):
    """A channel that can deliver a notification."""

    name: str

    def send(self, notification: Notification) -> bool:
        """Deliver the notification; return True when it was delivered."""


def already_sent(session: Session, kind: str, ref_id: int, channel: str, window_key: str) -> bool:
    """True when this exact notification was already delivered on this channel."""
    query = select(NotificationLog).where(
        NotificationLog.kind == kind,
        NotificationLog.ref_id == ref_id,
        NotificationLog.channel == channel,
        NotificationLog.window_key == window_key,
    )
    return session.scalars(query).first() is not None


def record_sent(
    session: Session,
    notification: Notification,
    channel: str,
    now: Any,
) -> NotificationLog | None:
    """Record a delivery; returns ``None`` when it was a duplicate."""
    if already_sent(
        session, notification.kind, notification.ref_id, channel, notification.window_key
    ):
        return None
    row = NotificationLog(
        kind=notification.kind,
        ref_id=notification.ref_id,
        channel=channel,
        window_key=notification.window_key,
        sent_at=now,
        payload={
            "title": notification.title,
            "body": notification.body,
            "url": notification.url,
        },
    )
    session.add(row)
    session.flush()
    return row


class BrowserChannel:
    """Queues the notification for the browser to pick up."""

    name = BROWSER

    def __init__(self, session: Session, now: Any) -> None:
        self._session = session
        self._now = now

    def send(self, notification: Notification) -> bool:
        """Queue the notification for the browser."""
        row = record_sent(self._session, notification, self.name, self._now)
        return row is not None


class EmailChannel:
    """Sends the notification over SMTP."""

    name = EMAIL

    def __init__(self, session: Session, now: Any, config: dict[str, Any] | None = None) -> None:
        self._session = session
        self._now = now
        env = get_settings()
        config = config or {}
        self._recipient = str(config.get("to") or "")
        self._host = str(config.get("host") or env.smtp_host)
        self._port = int(config.get("port") or env.smtp_port)
        self._user = str(config.get("user") or env.smtp_user)
        self._password = str(config.get("password") or env.smtp_password)
        self._from = str(config.get("from") or env.smtp_from)
        self._use_tls = bool(config.get("use_tls", env.smtp_use_tls))

    def send(self, notification: Notification) -> bool:
        """Send the notification by email."""
        if not self._recipient:
            logger.warning("email channel enabled but no recipient configured")
            return False
        if not self._host:
            logger.warning("email channel enabled but no SMTP host configured")
            return False
        message = EmailMessage()
        message["Subject"] = notification.title
        message["From"] = self._from or f"varagh@{self._host}"
        message["To"] = self._recipient
        message.set_content(f"{notification.title}\n\n{notification.body}")
        try:
            with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
                if self._use_tls:
                    smtp.starttls()
                if self._user:
                    smtp.login(self._user, self._password)
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as exc:
            logger.warning("email delivery failed: %s", exc)
            return False
        record_sent(self._session, notification, self.name, self._now)
        return True


class WebhookChannel:
    """Posts the notification to a generic webhook."""

    name = WEBHOOK

    def __init__(self, session: Session, now: Any, url: str, payload_format: str) -> None:
        self._session = session
        self._now = now
        self._url = url
        self._format = payload_format

    def send(self, notification: Notification) -> bool:
        """Post the notification to the configured webhook."""
        if not self._url:
            logger.warning("webhook channel enabled but WEBHOOK_URL is empty")
            return False
        payload = self._payload(notification)
        try:
            response = httpx.post(self._url, json=payload, timeout=15)
            response.raise_for_status()
        except (httpx.HTTPError, OSError) as exc:
            logger.warning("webhook delivery failed: %s", exc)
            return False
        record_sent(self._session, notification, self.name, self._now)
        return True

    def _payload(self, notification: Notification) -> dict[str, Any]:
        """Build the webhook payload in the configured format."""
        if self._format == "json":
            return {
                "kind": notification.kind,
                "ref_id": notification.ref_id,
                "title": notification.title,
                "body": notification.body,
                "window_key": notification.window_key,
                "url": notification.url,
            }
        return {
            "text": f"*{notification.title}*\n{notification.body}",
            "attachments": [
                {"title": notification.title, "text": notification.body, "color": "#2f6f5e"}
            ],
        }


def build_channels(session: Session, now: Any, config: dict[str, Any]) -> list[Channel]:
    """Build the channels that are enabled in the settings."""
    channels: list[Channel] = []
    channel_config = config.get("channels", {}) or {}
    if channel_config.get(BROWSER, True):
        channels.append(BrowserChannel(session, now))
    if channel_config.get(EMAIL, False):
        channels.append(EmailChannel(session, now, config.get("email", {}) or {}))
    if channel_config.get(WEBHOOK, False):
        webhook = config.get("webhook", {}) or {}
        url = webhook.get("url") or get_settings().webhook_url
        payload_format = webhook.get("format") or get_settings().webhook_format
        channels.append(WebhookChannel(session, now, url, payload_format))
    return channels
