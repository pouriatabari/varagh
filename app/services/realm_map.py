"""The map of the realms, drawn from the state of the database.

The picture is built on the server: every realm is a group with the
state it is in — ``fog``, ``progress``, ``claimed`` or ``hidden`` — and
the styles of the theme do the rest. The ground of the map is a vendored
file of paths; nothing is fetched while the page is drawn.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.services.realms import RealmState

GEOMETRY_PATH = Path(__file__).resolve().parents[1] / "static" / "map" / "geometry.json"

# The three castles of a realm, around the middle of its ground.
CASTLE_OFFSETS = ((-16.0, 4.0), (0.0, 9.0), (16.0, 4.0))

# The shape of a castle: a tower with a gate.
CASTLE_PATH = (
    "M -7 9 V -1 H -5 V -6 H -2 V -1 H 2 V -6 H 5 V -1 H 7 V 9 Z "
    "M -2 9 V 4 H 2 V 9 Z"
)


@lru_cache(maxsize=1)
def geometry() -> dict:
    """The vendored ground of the map."""
    try:
        payload = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"width": 1000.0, "height": 1200.0, "coastline": [], "realms": {}, "anchors": {}}
    if not isinstance(payload, dict):
        return {"width": 1000.0, "height": 1200.0, "coastline": [], "realms": {}, "anchors": {}}
    return payload


def _defs() -> str:
    """The paints of the picture: the light on the sea and the two
    hatches that tell the fog and the hidden realm apart."""
    return (
        "<defs>"
        '<radialGradient id="sea-light" cx="50%" cy="38%" r="72%">'
        '<stop offset="0%" stop-color="var(--viz-sea-2)" />'
        '<stop offset="100%" stop-color="var(--viz-sea-1)" />'
        "</radialGradient>"
        '<pattern id="fog-hatch" width="8" height="8" patternUnits="userSpaceOnUse"'
        ' patternTransform="rotate(45)">'
        '<rect width="8" height="8" fill="var(--bg-sunken)" />'
        '<line x1="0" y1="0" x2="0" y2="8" stroke="var(--viz-axis)" stroke-width="1.4" />'
        "</pattern>"
        '<pattern id="hidden-hatch" width="10" height="10" patternUnits="userSpaceOnUse"'
        ' patternTransform="rotate(-45)">'
        '<line x1="0" y1="0" x2="0" y2="10" stroke="var(--info)" stroke-width="1" />'
        "</pattern>"
        "</defs>"
    )


def _castles(anchor: tuple[float, float], lit: int) -> str:
    """The castles of a realm, the lit ones first."""
    body = []
    for index, (dx, dy) in enumerate(CASTLE_OFFSETS):
        classes = "castle lit" if index < lit else "castle locked"
        body.append(
            f'<g class="{classes}" transform="translate({dx:.1f} {dy:.1f})">'
            f'<path d="{CASTLE_PATH}" /></g>'
        )
    return "".join(body)


def map_svg(states: list[RealmState], route: list[str]) -> str:
    """Draw the map of the realms.

    Every realm is a group whose id is the key of the realm and whose
    ``data-state`` is the state it is in, so the styles of the theme and
    the tests both know where they stand.
    """
    ground = geometry()
    width = float(ground.get("width", 1000))
    # A little room below, so the name of the southernmost realm and the
    # castles of the coast are not cut off.
    height = float(ground.get("height", 1200)) + 64
    realms = ground.get("realms", {})
    anchors = ground.get("anchors", {})
    body = [
        f'<svg class="realm-map" viewBox="0 0 {width:.0f} {height:.0f}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'aria-label="realm map" xmlns="http://www.w3.org/2000/svg">',
        _defs(),
        f'<rect class="map-sea" x="0" y="0" width="{width:.0f}" height="{height:.0f}" />',
        '<g class="map-coast">',
    ]
    for path in ground.get("coastline", []):
        body.append(f'<path d="{path}" />')
    body.append("</g>")
    body.append('<g class="map-realms">')
    for state in states:
        key = state.key
        paths = realms.get(key, [])
        if not paths:
            continue
        anchor = anchors.get(key, [0, 0])
        body.append(
            f'<g id="realm-{key}" data-state="{state.state}" class="realm" '
            f'data-name="{state.realm.name_fa}" '
            f'data-castles="{state.castles_lit}" '
            f'data-coverage="{state.realm.coverage_fa}" '
            f'data-legend="{state.realm.legend_fa}" '
            f'data-domain="{state.domain_name or ""}">'
            f"<title>{state.realm.name_fa} — {state.realm.coverage_fa}</title>"
        )
        body.append('<g class="realm-ground">')
        for path in paths:
            body.append(f'<path d="{path}" />')
        body.append("</g>")
        body.append(
            f'<g class="realm-castles" transform="translate({anchor[0]:.1f} {anchor[1]:.1f})">'
            f"{_castles((anchor[0], anchor[1]), state.castles_lit)}</g>"
        )
        body.append(
            f'<text class="realm-label" x="{anchor[0]:.1f}" y="{anchor[1] + 30:.1f}" '
            f'text-anchor="middle">{state.realm.name_fa}</text>'
        )
        body.append("</g>")
    body.append("</g>")
    route_points = [
        anchors.get(key) for key in route if key in anchors
    ]
    if len(route_points) > 1:
        route_d = " ".join(
            f"{'M' if index == 0 else 'L'} {point[0]:.1f} {point[1]:.1f}"
            for index, point in enumerate(route_points)
        )
        body.append(f'<path class="campaign-route" d="{route_d}" />')
    for point in route_points:
        body.append(
            f'<circle class="route-node" cx="{point[0]:.1f}" cy="{point[1]:.1f}" r="4" />'
        )
    body.append("</svg>")
    return "".join(body)
