"""A custom provider: any endpoint that speaks JSON over HTTP.

The request shape is chosen with ``AI_CUSTOM_METHOD``:

``json``
    ``{"model": …, "system": …, "messages": [...], "payload": {...}}`` — the
    generic shape; the answer must be a JSON object.
``openai``
    An OpenAI-compatible chat-completions request.
``anthropic``
    An Anthropic messages request.
``prompt``
    ``{"model": …, "prompt": "…"}`` — the plain-text answer is parsed as JSON.

The answer may come back as a bare JSON object, in the OpenAI shape or in the
Anthropic shape; all three are understood.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.ai.provider import AIError, extract_json
from app.config import get_settings

logger = logging.getLogger("varagh.ai")


class CustomProvider:
    """Calls a user-configured endpoint and returns a JSON object."""

    name = "custom"

    def __init__(self) -> None:
        settings = get_settings()
        self._url = settings.ai_custom_url or settings.ai_base_url
        self._model = settings.ai_model
        self._api_key = settings.ai_api_key
        self._timeout = settings.ai_timeout_seconds
        self._method = settings.ai_custom_method
        self._headers = _parse_headers(settings.ai_custom_headers)

    def complete_json(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Ask the endpoint for a JSON object."""
        if not self._url:
            raise AIError("the custom provider has no URL (set AI_CUSTOM_URL)")
        body = self._body(feature, system, payload)
        headers = {"content-type": "application/json", **self._headers}
        try:
            response = httpx.post(self._url, json=body, headers=headers, timeout=self._timeout)
            response.raise_for_status()
            text = response.text
        except (httpx.HTTPError, OSError) as exc:
            raise AIError(f"the custom provider call failed: {exc}") from exc
        return _parse_answer(text)

    def _body(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Build the request body for the configured method."""
        user_text = json.dumps(payload, ensure_ascii=False)
        if self._method == "openai":
            return {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.2,
            }
        if self._method == "anthropic":
            return {
                "model": self._model,
                "max_tokens": 2048,
                "system": system,
                "messages": [{"role": "user", "content": user_text}],
            }
        if self._method == "prompt":
            return {"model": self._model, "prompt": f"{system}\n\n{user_text}"}
        return {
            "model": self._model,
            "system": system,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
            "payload": payload,
        }


def _parse_headers(raw: str) -> dict[str, str]:
    """Parse extra headers given as ``Key: Value`` pairs separated by commas."""
    headers: dict[str, str] = {}
    for part in raw.split(","):
        if ":" not in part:
            continue
        key, _, value = part.partition(":")
        key = key.strip()
        value = value.strip()
        if key:
            headers[key] = value
    return headers


def _parse_answer(text: str) -> dict[str, Any]:
    """Read the JSON object out of an answer of any of the known shapes."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return extract_json(text)
    if not isinstance(data, dict):
        raise AIError("the custom provider did not return a JSON object")
    if "choices" in data:
        return extract_json(_openai_text(data))
    if "content" in data and isinstance(data["content"], list):
        return extract_json(_anthropic_text(data))
    return data


def _openai_text(data: dict[str, Any]) -> str:
    """Return the message text of an OpenAI-style answer."""
    choices = data.get("choices") or []
    if not choices:
        raise AIError("the custom provider returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not isinstance(content, str):
        raise AIError("the custom provider returned no text")
    return content


def _anthropic_text(data: dict[str, Any]) -> str:
    """Return the text of an Anthropic-style answer."""
    for block in data.get("content") or []:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text", ""))
    raise AIError("the custom provider returned no text")
