"""The AI configuration.

The settings page writes the configuration into the database; the environment
variables stay the fallback of a fresh installation. As soon as the user saves
the AI form, the stored configuration wins as a whole — that way a field can
also be cleared on purpose.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config import get_settings
from app.services import settings as settings_service

PROVIDERS = ("anthropic", "openai", "custom")
CUSTOM_METHODS = ("json", "openai", "anthropic", "prompt")
AUTH_HEADERS = ("x-api-key", "bearer", "both")

DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_OUTPUT_TOKENS = 2048


@dataclass(frozen=True)
class AIConfig:
    """Everything a provider needs to make a call."""

    enabled: bool = False
    provider: str = ""
    api_key: str = ""
    model: str = ""
    base_url: str = ""
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    auth_header: str = "both"
    custom_url: str = ""
    custom_method: str = "json"
    custom_headers: str = ""

    @property
    def usable(self) -> bool:
        """Whether a call can be made at all."""
        if not self.enabled or not self.provider:
            return False
        if self.provider == "custom":
            return bool(self.custom_url or self.base_url)
        return bool(self.api_key and self.model)


def config_from_env() -> AIConfig:
    """Build the configuration out of the environment variables."""
    env = get_settings()
    provider = env.ai_provider.strip().lower()
    return AIConfig(
        enabled=bool(provider and env.ai_api_key and env.ai_model),
        provider=provider,
        api_key=env.ai_api_key,
        model=env.ai_model,
        base_url=env.ai_base_url,
        timeout_seconds=env.ai_timeout_seconds,
        max_output_tokens=env.ai_max_output_tokens,
        auth_header=env.ai_auth_header,
        custom_url=env.ai_custom_url,
        custom_method=env.ai_custom_method,
        custom_headers=env.ai_custom_headers,
    )


def config_from_values(values: dict[str, Any]) -> AIConfig:
    """Build the configuration out of a stored document."""
    return AIConfig(
        enabled=bool(values.get("enabled")),
        provider=str(values.get("provider") or "").strip().lower(),
        api_key=str(values.get("api_key") or ""),
        model=str(values.get("model") or ""),
        base_url=str(values.get("base_url") or ""),
        timeout_seconds=_number(values.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS),
        max_output_tokens=int(_number(values.get("max_output_tokens"), DEFAULT_MAX_OUTPUT_TOKENS)),
        auth_header=str(values.get("auth_header") or "both"),
        custom_url=str(values.get("custom_url") or ""),
        custom_method=str(values.get("custom_method") or "json"),
        custom_headers=str(values.get("custom_headers") or ""),
    )


def load_config(session: Session | None = None) -> AIConfig:
    """Return the effective configuration: the database first, the environment second."""
    if session is not None:
        stored = settings_service.get_stored_setting(session, "ai")
        if isinstance(stored, dict):
            return config_from_values(stored)
    return config_from_env()


def config_source(session: Session | None = None) -> str:
    """Return where the effective configuration comes from."""
    if session is not None:
        stored = settings_service.get_stored_setting(session, "ai")
        if isinstance(stored, dict):
            return "database"
    return "environment"


def _number(value: Any, default: float) -> float:
    """Read a number out of a stored value, falling back to the default."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
