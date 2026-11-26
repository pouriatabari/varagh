"""The AI provider configured in the settings page."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai.config import load_config
from app.ai.provider import get_provider
from app.services import settings as settings_service

AI_VALUES = {
    "enabled": True,
    "provider": "anthropic",
    "api_key": "sk-secret-value",
    "model": "minimax/MiniMax-M2.5",
    "base_url": "https://ai.snapp.tech/anthropic",
    "timeout_seconds": 120,
    "max_output_tokens": 100000,
    "auth_header": "both",
    "custom_url": "",
    "custom_method": "json",
    "custom_headers": "",
}


def test_the_environment_is_the_fallback(session: Session) -> None:
    """Without a stored configuration the environment decides."""
    config = load_config(session)
    assert config.provider == ""
    assert config.usable is False
    assert get_provider(session) is None


def test_the_stored_configuration_wins(session: Session) -> None:
    """The configuration of the settings page is used as soon as it is stored."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    config = load_config(session)
    assert config.provider == "anthropic"
    assert config.model == "minimax/MiniMax-M2.5"
    assert config.base_url == "https://ai.snapp.tech/anthropic"
    assert config.timeout_seconds == 120
    assert config.max_output_tokens == 100000
    assert config.usable is True


def test_the_provider_is_built_out_of_the_stored_configuration(session: Session) -> None:
    """The provider carries the model of the configuration."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    provider = get_provider(session)
    assert provider is not None
    assert provider.name == "anthropic"
    assert provider.model == "minimax/MiniMax-M2.5"


def test_the_settings_page_saves_the_configuration(client: TestClient, session: Session) -> None:
    """The form of the settings page writes the configuration."""
    response = client.post(
        "/settings/ai",
        data={
            "enabled": "1",
            "provider": "anthropic",
            "model": "minimax/MiniMax-M2.5",
            "api_key": "sk-secret-value",
            "base_url": "https://ai.snapp.tech/anthropic",
            "timeout_seconds": "120",
            "max_output_tokens": "100000",
            "auth_header": "both",
        },
    )
    assert response.status_code == 200
    config = load_config(session)
    assert config.usable is True
    assert config.api_key == "sk-secret-value"


def test_the_page_never_shows_the_api_key(client: TestClient, session: Session) -> None:
    """The stored key is not sent back to the browser."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    response = client.get("/settings")
    assert response.status_code == 200
    assert "sk-secret-value" not in response.text


def test_an_empty_key_keeps_the_stored_one(client: TestClient, session: Session) -> None:
    """Saving the form without a key does not throw the stored key away."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    client.post(
        "/settings/ai",
        data={"enabled": "1", "provider": "anthropic", "model": "minimax/MiniMax-M2.5"},
    )
    assert load_config(session).api_key == "sk-secret-value"


def test_the_key_can_be_cleared(client: TestClient, session: Session) -> None:
    """The stored key is removed on purpose."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    client.post(
        "/settings/ai",
        data={
            "enabled": "1",
            "provider": "anthropic",
            "model": "minimax/MiniMax-M2.5",
            "clear_api_key": "1",
        },
    )
    assert load_config(session).api_key == ""


def test_an_unknown_provider_is_refused(client: TestClient, session: Session) -> None:
    """Only the known providers are stored."""
    response = client.post(
        "/settings/ai",
        data={"enabled": "1", "provider": "telepathy", "model": "x"},
    )
    assert response.status_code == 400


def test_the_export_never_leaks_the_key(client: TestClient, session: Session) -> None:
    """The JSON export redacts the secrets."""
    settings_service.update_settings(session, {"ai": AI_VALUES})
    response = client.get("/export.json")
    assert response.status_code == 200
    assert "sk-secret-value" not in response.text
    assert response.json()["settings"]["ai"]["api_key"] == "***"
