"""The catalogue of the insignia.

Two files hold the data: ``data/insignia.json`` (the titles and their
emblems) and ``data/virtues.json`` (the six ribbons). The counts of the
pearls, of the leaves, of the arches and of the rays are written down in
the file, so the drawing can always be checked against the description of
the title.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config import get_settings


@dataclass(frozen=True)
class Emblem:
    """What is drawn on (or above) the shield of one title."""

    kind: str
    pearls_total: int = 0
    pearls_drawn: int = 0
    leaves_total: int = 0
    leaves_drawn: int = 0
    crosses_drawn: int = 0
    fleurs_drawn: int = 0
    pearls_raised: bool = False
    arches: int = 0
    orb_cross: bool = False
    rays: int = 0
    island: bool = False
    count: int = 1


@dataclass(frozen=True)
class Title:
    """One title of the ladder and the badge that stands for it."""

    key: str
    level: int
    family: str
    metal: str
    field: str
    emblem: Emblem
    note_fa: str


@dataclass(frozen=True)
class Ribbon:
    """One ribbon of the rack: a virtue, a colour and a pattern.

    The two colours are the steps of the palette for the two themes:
    the light one for the parchment and the dark one for the night.
    """

    key: str
    color: str
    color_dark: str
    pattern: str


def _paths() -> list[Path]:
    """Where the data of the insignia may be found."""
    paths = [Path(get_settings().data_dir) / "insignia.json"]
    paths.append(Path(__file__).resolve().parents[2] / "data" / "insignia.json")
    return paths


def _virtue_paths() -> list[Path]:
    """Where the data of the ribbons may be found."""
    paths = [Path(get_settings().data_dir) / "virtues.json"]
    paths.append(Path(__file__).resolve().parents[2] / "data" / "virtues.json")
    return paths


def _read(paths: list[Path]) -> dict[str, Any]:
    """Read the first file that is there."""
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _emblem(raw: dict[str, Any]) -> Emblem:
    """Build the emblem of a title out of its description."""
    return Emblem(
        kind=str(raw.get("kind", "plain_shield")),
        pearls_total=int(raw.get("pearls_total", 0)),
        pearls_drawn=int(raw.get("pearls_drawn", 0)),
        leaves_total=int(raw.get("leaves_total", 0)),
        leaves_drawn=int(raw.get("leaves_drawn", 0)),
        crosses_drawn=int(raw.get("crosses_drawn", 0)),
        fleurs_drawn=int(raw.get("fleurs_drawn", 0)),
        pearls_raised=bool(raw.get("pearls_raised", False)),
        arches=int(raw.get("arches", 0)),
        orb_cross=bool(raw.get("orb_cross", False)),
        rays=int(raw.get("rays", 0)),
        island=bool(raw.get("island", False)),
        count=int(raw.get("count", 1)),
    )


@lru_cache(maxsize=1)
def load_titles() -> dict[str, Title]:
    """The titles of the ladder and their badges."""
    payload = _read(_paths())
    titles: dict[str, Title] = {}
    for raw in payload.get("titles", []):
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key", ""))
        if not key:
            continue
        titles[key] = Title(
            key=key,
            level=int(raw.get("level", 0)),
            family=str(raw.get("family", "service")),
            metal=str(raw.get("metal", "iron")),
            field=str(raw.get("field", "sable")),
            emblem=_emblem(raw.get("emblem", {}) or {}),
            note_fa=str(raw.get("note_fa", "")),
        )
    return titles


@lru_cache(maxsize=1)
def load_virtues() -> dict[str, Ribbon]:
    """The six ribbons of the rack."""
    payload = _read(_virtue_paths())
    ribbons: dict[str, Ribbon] = {}
    for raw in payload.get("virtues", []):
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("key", ""))
        if not key:
            continue
        ribbons[key] = Ribbon(
            key=key,
            color=str(raw.get("color", "#257de0")),
            color_dark=str(raw.get("color_dark", raw.get("color", "#338ced"))),
            pattern=str(raw.get("pattern", "solid")),
        )
    return ribbons


def title_of(key: str) -> Title | None:
    """The badge of one title, when the ladder knows it."""
    return load_titles().get(key)


def ordered_titles() -> list[Title]:
    """The titles of the ladder, from the lowest to the highest."""
    return sorted(load_titles().values(), key=lambda title: (title.level, title.key))
