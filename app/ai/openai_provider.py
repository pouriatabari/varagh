"""A provider for any OpenAI-compatible chat-completions endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.provider import AIError, extract_json
from app.config import get_settings

logger = logging.getLogger("varagh.ai")

DEFAULT_BASE_URL = "https://api.openai.com/v1"


class OpenAICompatibleProvider:
    """Calls an OpenAI-compatible endpoint and returns a JSON object."""

    name = "openai-compatible"

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
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        headers = {"content-type": "application/json"}
        if self._api_key:
            headers["authorization"] = f"Bearer {self._api_key}"
        try:
            response = httpx.post(
                f"{self._base_url}/chat/completions",
                json=body,
                headers=headers,
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise AIError(f"the model call failed: {exc}") from exc
        return extract_json(_first_text(data))


def _first_text(data: dict[str, Any]) -> str:
    """Return the text of the first choice of the answer."""
    choices = data.get("choices") or []
    if not choices:
        raise AIError("the model returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise AIError("the model returned no text")
    return content
