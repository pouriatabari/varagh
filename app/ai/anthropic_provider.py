"""The Anthropic provider, called over plain HTTP (no vendor SDK)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ai.provider import AIError, extract_json
from app.config import get_settings

logger = logging.getLogger("varagh.ai")

DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"


class AnthropicProvider:
    """Calls the Anthropic messages API and returns a JSON object."""

    name = "anthropic"

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.ai_api_key
        self._model = settings.ai_model
        self._base_url = (settings.ai_base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = settings.ai_timeout_seconds

    def complete_json(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Ask the model for a JSON object."""
        body = {
            "model": self._model,
            "max_tokens": 2048,
            "system": system,
            "messages": [{"role": "user", "content": _as_text(payload)}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        }
        try:
            response = httpx.post(
                f"{self._base_url}/v1/messages",
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AIError(f"the Anthropic call failed: {exc}") from exc
        return extract_json(_first_text(data))


def _as_text(payload: dict[str, Any]) -> str:
    """Render the payload as the user message."""
    import json

    return json.dumps(payload, ensure_ascii=False)


def _first_text(data: dict[str, Any]) -> str:
    """Return the text of the first content block of the answer."""
    blocks = data.get("content") or []
    for block in blocks:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text", ""))
    raise AIError("the model returned no text")
