"""The insignia of the titles.

The badges of the ranks are drawn by the code: every shape comes from
the catalogue in ``data/insignia.json`` and from the small primitives of
:mod:`app.insignia.shapes`. Nothing is fetched, no picture is copied and
no font is needed: the badge is a shield, a rim, an emblem and a row of
studs, drawn from numbers.

The words of the interface never live here: the renderer takes the name
of the title and the text of the tooltip from the caller, so the same
code serves both lexicons.
"""

from __future__ import annotations

from app.insignia.badge import render_badge
from app.insignia.catalog import (
    Emblem,
    Ribbon,
    Title,
    load_titles,
    load_virtues,
    ordered_titles,
    title_of,
)
from app.insignia.ribbons import render_ribbon_rack
from app.insignia.skill_tree import render_skill_tree

__all__ = [
    "Emblem",
    "Ribbon",
    "Title",
    "load_titles",
    "load_virtues",
    "ordered_titles",
    "render_badge",
    "render_ribbon_rack",
    "render_skill_tree",
    "title_of",
]
