"""The provider-agnostic AI interface.

Every AI feature goes through this interface, so the application never talks
to a vendor SDK directly. The provider is selected with the environment
(``AI_PROVIDER``, ``AI_API_KEY``, ``AI_MODEL``, ``AI_BASE_URL``) and the whole
layer stays optional: without a provider every non-AI feature keeps working.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Protocol

from app.config import get_settings

logger = logging.getLogger("varagh.ai")

FEATURES = (
    "parse_quick_add",
    "parse_daily_journal",
    "classify_task",
    "parse_syllabus",
    "daily_plan",
    "review_draft",
    "ask_my_data",
)


class AIProvider(Protocol):
    """The interface every provider implements."""

    name: str

    def complete_json(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return a JSON object for the given feature and payload."""


class AIError(RuntimeError):
    """Raised when a provider call fails."""


def extract_json(text: str) -> dict[str, Any]:
    """Parse the JSON object out of a model answer."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("```")[1]
        if cleaned.lstrip().lower().startswith("json"):
            cleaned = cleaned.lstrip()[4:]
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise AIError("the model did not return a JSON object")
    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise AIError(f"invalid JSON from the model: {exc}") from exc
    if not isinstance(parsed, dict):
        raise AIError("the model did not return a JSON object")
    return parsed


def get_provider() -> AIProvider | None:
    """Return the configured provider, or ``None`` when the AI is disabled."""
    from app.ai.anthropic_provider import AnthropicProvider
    from app.ai.custom_provider import CustomProvider
    from app.ai.openai_provider import OpenAICompatibleProvider

    settings = get_settings()
    if not settings.ai_enabled:
        return None
    provider_name = settings.ai_provider.lower()
    if provider_name == "anthropic":
        return AnthropicProvider()
    if provider_name in {"openai", "openai-compatible", "compatible"}:
        return OpenAICompatibleProvider()
    if provider_name == "custom":
        return CustomProvider()
    logger.warning("unknown AI provider %r; the AI stays disabled", settings.ai_provider)
    return None
