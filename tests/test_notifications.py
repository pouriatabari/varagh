"""Notification rules, de-duplication and the browser channel."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.system import NotificationLog
from app.notify import rules as rule_module
from app.services import settings as settings_service
from app.services import tasks as task_service
from app.utils.time import utcnow

NOW = dt.datetime(2024, 8, 5, 12, 0, tzinfo=dt.UTC)
TIMEZONE = "Asia/Tehran"


def _config(**overrides: object) -> dict[str, object]:
    """Return a notification configuration for the tests."""
    config: dict[str, object] = {
        "due_soon_minutes": 30,
        "overdue_enabled": True,
        "digest_enabled": False,
        "journal_nudge_enabled": False,
        "review_reminder_enabled": False,
        "stale_learning_enabled": False,
        "channels": {"browser": True, "email": False, "webhook": False},
    }
    config.update(overrides)
    return config


def test_due_soon_rule_only_fires_inside_the_window(session: Session) -> None:
    """A task is only notified when its deadline is close."""
    soon = task_service.create_task(
        session, title="نزدیک", now=NOW, due_at=NOW + dt.timedelta(minutes=10)
    )
    far = task_service.create_task(
        session, title="دور", now=NOW, due_at=NOW + dt.timedelta(minutes=200)
    )
    notifications = rule_module.collect_notifications(
        session, now=NOW, timezone=TIMEZONE, config=_config()
    )
    kinds = {(item.kind, item.ref_id) for item in notifications}
    assert ("due_soon", soon.id) in kinds
    assert ("due_soon", far.id) not in kinds


def test_overdue_rule(session: Session) -> None:
    """A task past its deadline is notified."""
    task = task_service.create_task(
        session, title="تأخیردار", now=NOW, due_at=NOW - dt.timedelta(hours=2)
    )
    notifications = rule_module.collect_notifications(
        session, now=NOW, timezone=TIMEZONE, config=_config()
    )
    assert any(item.kind == "overdue" and item.ref_id == task.id for item in notifications)


def test_dispatch_is_deduplicated_by_window(session: Session) -> None:
    """The same window never produces a second delivery."""
    task_service.create_task(session, title="نزدیک", now=NOW, due_at=NOW + dt.timedelta(minutes=10))
    config = _config()
    first = rule_module.dispatch(session, now=NOW, timezone=TIMEZONE, config=config)
    second = rule_module.dispatch(session, now=NOW, timezone=TIMEZONE, config=config)
    assert first == 1
    assert second == 0
    rows = session.scalars(select(NotificationLog)).all()
    assert len(rows) == 1
    assert rows[0].channel == "browser"


def test_daily_digest_fires_once_per_day(session: Session) -> None:
    """The digest is raised after the configured time and only once a day."""
    evening = dt.datetime(2024, 8, 5, 17, 0, tzinfo=dt.UTC)  # 20:30 in Tehran
    morning = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)  # 12:30 in Tehran
    config = _config(digest_enabled=True, digest_time="20:00")
    assert not rule_module.collect_notifications(
        session, now=morning, timezone=TIMEZONE, config=config
    )
    evening_notifications = rule_module.collect_notifications(
        session, now=evening, timezone=TIMEZONE, config=config
    )
    assert any(item.kind == "daily_digest" for item in evening_notifications)


def test_journal_nudge_skipped_when_a_journal_exists(session: Session) -> None:
    """The nudge is not raised when the day already has a journal entry."""
    from app.models.timing import DailyJournal

    evening = dt.datetime(2024, 8, 5, 17, 0, tzinfo=dt.UTC)
    config = _config(journal_nudge_enabled=True, journal_nudge_time="20:00")
    assert any(
        item.kind == "journal_nudge"
        for item in rule_module.collect_notifications(
            session, now=evening, timezone=TIMEZONE, config=config
        )
    )
    session.add(
        DailyJournal(date=dt.date(2024, 8, 5), raw_text="یادداشت", parsed=None, confirmed=True)
    )
    session.flush()
    assert not any(
        item.kind == "journal_nudge"
        for item in rule_module.collect_notifications(
            session, now=evening, timezone=TIMEZONE, config=config
        )
    )


def test_browser_endpoint_returns_and_marks_notifications(
    session: Session, client: TestClient
) -> None:
    """The browser polls the endpoint and can acknowledge a notification."""
    task_service.create_task(session, title="نزدیک", now=NOW, due_at=NOW + dt.timedelta(minutes=10))
    rule_module.dispatch(session, now=NOW, timezone=TIMEZONE, config=_config())

    response = client.get("/api/notifications/due")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["notifications"]) == 1
    assert payload["notifications"][0]["kind"] == "due_soon"

    notification_id = payload["notifications"][0]["id"]
    assert client.post(f"/api/notifications/{notification_id}/read").status_code == 200
    assert client.get("/api/notifications/due").json()["notifications"] == []


def test_dispatch_uses_the_stored_settings(session: Session) -> None:
    """The dispatch reads the notification block from the settings."""
    settings_service.update_settings(session, {"notifications": _config()})
    task_service.create_task(session, title="نزدیک", now=NOW, due_at=NOW + dt.timedelta(minutes=10))
    config = settings_service.notification_settings(session)
    sent = rule_module.dispatch(session, now=NOW, timezone=TIMEZONE, config=config)
    assert sent == 1


def test_email_channel_without_configuration_does_not_send(session: Session) -> None:
    """A misconfigured email channel fails quietly."""
    from app.notify.channels import EmailChannel
    from app.notify.messages import Notification

    channel = EmailChannel(session, utcnow(), {"to": ""})
    notification = Notification(
        kind="test", ref_id=0, title="t", body="b", window_key="test-window"
    )
    assert channel.send(notification) is False
