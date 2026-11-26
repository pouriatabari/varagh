"""Markdown rendering with sanitisation.

User text is never trusted: raw HTML is disabled at the parser level and the
result is additionally sanitised with an explicit allow-list.
"""

from __future__ import annotations

import bleach
from markdown_it import MarkdownIt

ALLOWED_TAGS: frozenset[str] = frozenset(
    {
        "p",
        "br",
        "strong",
        "em",
        "del",
        "s",
        "code",
        "pre",
        "blockquote",
        "ul",
        "ol",
        "li",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "a",
        "table",
        "thead",
        "tbody",
        "tr",
        "th",
        "td",
        "span",
    }
)

ALLOWED_ATTRIBUTES: dict[str, list[str]] = {
    "a": ["href", "title"],
    "code": ["class"],
    "span": ["dir"],
    "th": ["align"],
    "td": ["align"],
}

ALLOWED_PROTOCOLS: frozenset[str] = frozenset({"http", "https", "mailto"})

_MARKDOWN = MarkdownIt("commonmark", {"html": False, "linkify": False, "typographer": False})


def render_markdown(text: str | None) -> str:
    """Render Markdown to sanitised HTML."""
    if not text:
        return ""
    html = _MARKDOWN.render(text)
    return bleach.clean(
        html,
        tags=set(ALLOWED_TAGS),
        attributes=ALLOWED_ATTRIBUTES,
        protocols=set(ALLOWED_PROTOCOLS),
        strip=True,
    )


def render_inline(text: str | None) -> str:
    """Render a single-line Markdown fragment to sanitised HTML."""
    if not text:
        return ""
    return render_markdown(text).replace("<p>", "").replace("</p>", "").strip()
