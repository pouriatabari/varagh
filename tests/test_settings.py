"""The settings page."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import settings as settings_service


def test_the_weekend_days_are_saved(client: TestClient, session: Session) -> None:
    """The checkboxes of the weekend days reach the settings."""
    response = client.post(
        "/settings/general",
        data={
            "timezone": "Asia/Tehran",
            "calendar_system": "jalali",
            "digits": "persian",
            "weekly_hour_target": "40",
            "weekend_0": "on",
            "weekend_6": "on",
        },
    )
    assert response.status_code == 200
    assert settings_service.weekend_weekdays(session) == frozenset({0, 6})


def test_the_save_is_confirmed(client: TestClient) -> None:
    """The page answers with a confirmation instead of resetting the form."""
    response = client.post(
        "/settings/general",
        data={
            "timezone": "Asia/Tehran",
            "calendar_system": "jalali",
            "digits": "persian",
            "weekly_hour_target": "40",
            "weekend_6": "on",
        },
    )
    assert response.status_code == 200
    assert "ذخیره شد" in response.text


def test_the_settings_page_keeps_the_chosen_days(client: TestClient, session: Session) -> None:
    """The page shows the weekend days of the settings."""
    settings_service.update_settings(session, {"weekend_weekdays": [0, 5, 6]})
    response = client.get("/settings")
    assert response.status_code == 200
    assert 'name="weekend_0"' in response.text
