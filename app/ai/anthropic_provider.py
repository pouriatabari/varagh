"""The Anthropic provider, called over plain HTTP (no vendor SDK)."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.ai.config import AIConfig
from app.ai.provider import AIError, extract_json

logger = logging.getLogger("varagh.ai")

DEFAULT_BASE_URL = "https://api.anthropic.com"
API_VERSION = "2023-06-01"


class AnthropicProvider:
    """Calls the Anthropic messages API and returns a JSON object."""

    name = "anthropic"

    def __init__(self, config: AIConfig) -> None:
        self._api_key = config.api_key
        self.model = config.model
        self._base_url = (config.base_url or DEFAULT_BASE_URL).rstrip("/")
        self._timeout = config.timeout_seconds
        self._max_tokens = config.max_output_tokens
        self._auth_header = config.auth_header

    def complete_json(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Ask the model for a JSON object."""
        body = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": _as_text(payload)}],
        }
        headers = {
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
            **_auth_headers(self._api_key, self._auth_header),
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


def _auth_headers(api_key: str, mode: str) -> dict[str, str]:
    """Build the authentication headers of the configured mode.

    The official API wants ``x-api-key``; a Claude Code compatible proxy wants
    ``Authorization: Bearer``; ``both`` satisfies either of them.
    """
    headers: dict[str, str] = {}
    if not api_key:
        return headers
    if mode in {"x-api-key", "both"}:
        headers["x-api-key"] = api_key
    if mode in {"bearer", "both"}:
        headers["authorization"] = f"Bearer {api_key}"
    return headers


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
