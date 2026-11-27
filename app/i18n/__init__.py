"""Internationalisation — two Persian packs, one plain and one medieval.

The plain pack is the language of the app as it was written. The medieval
pack speaks of missions, musters and night watches. The choice is a
setting of the user; it only touches the presentation layer.

Every term of the medieval pack knows its plain wording, so a page can
show it in a tooltip.
"""

from __future__ import annotations

import contextlib
from typing import Any

from app.i18n import fa_medieval, fa_plain

PACKS: dict[str, dict[str, str]] = {
    "plain": fa_plain.STRINGS,
    "medieval": fa_medieval.STRINGS,
}
DEFAULT_PACK = "plain"
MEDIEVAL_PACK = "medieval"


class Term(str):
    """A translated term that remembers its plain wording."""

    __slots__ = ("plain",)

    def __new__(cls, text: str, plain: str = "") -> Term:
        term = super().__new__(cls, text)
        term.plain = plain or text
        return term


def translate(key: str, pack: str = DEFAULT_PACK, **kwargs: Any) -> Term:
    """Translate a key in a pack, falling back to the key itself."""
    strings = PACKS.get(pack) or PACKS[DEFAULT_PACK]
    template = strings.get(key)
    if template is None:
        template = PACKS[DEFAULT_PACK].get(key)
    if template is None:
        return Term(key)
    if kwargs:
        with contextlib.suppress(KeyError, IndexError):
            template = template.format(**kwargs)
    plain = PACKS[DEFAULT_PACK].get(key, template)
    return Term(template, plain)


def t(key: str, **kwargs: Any) -> str:
    """Translate a key in the plain pack — the language of the exports."""
    return str(translate(key, DEFAULT_PACK, **kwargs))


def tip(value: Any) -> str:
    """The plain wording of a term, for the tooltip of a medieval one."""
    if isinstance(value, Term) and value.plain != str(value):
        return value.plain
    return ""


__all__ = [
    "DEFAULT_PACK",
    "MEDIEVAL_PACK",
    "PACKS",
    "Term",
    "t",
    "tip",
    "translate",
]
