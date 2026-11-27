"""The drawing of the tree of the ranks.

The tree is drawn by the code: the ranks are the shields of the badges
that the app already draws, the gates are the medallions beside them,
and the paths between them are the gold of the road that has been walked
and the grey of the road that has not.

The state of a node is told three times over: by the words in the
``<title>``, by the shape of the frame, and by the colour — never by the
colour alone.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from urllib.parse import quote

from app.services.skill_tree import (
    CURRENT,
    LOCKED,
    MET,
    OPEN,
    READY,
    UNMET,
    SkillTree,
)

# The metals of the theme: the gold of the road that is open, the grey
# of the road that is not.
GOLD = "#d4a72c"
GOLD_BRIGHT = "#e6c05a"
GREY = "#4a5262"
STEEL = "#7d8798"
INK = "#e8ecf4"
DARK = "#080c13"

GATE_RADIUS = 30.0
RANK_RADIUS = 58.0


def _gate_glyph(key: str, virtue_colour: str) -> str:
    """The mark of a gate: a small sign that tells what it asks for."""
    if key == "degrees":
        # the chevrons of a rank
        return (
            '<path d="M -11 -8 L 0 -13 L 11 -8" /><path d="M -11 1 L 0 -4 L 11 1" />'
            '<path d="M -11 10 L 0 5 L 11 10" />'
        )
    if key == "musters":
        # the roll call: a ring of dots
        dots = []
        for index in range(7):
            angle = math.radians(-90 + 360 * index / 7)
            dots.append(
                f'<circle cx="{14 * math.cos(angle):.1f}" '
                f'cy="{14 * math.sin(angle):.1f}" r="3" />'
            )
        return "".join(dots)
    if key == "silver":
        # the crescent
        return '<path d="M 5 -12 A 13 13 0 1 0 5 12 A 9.5 9.5 0 1 1 5 -12 Z" />'
    if key == "gold":
        # the sun
        rays = []
        for index in range(8):
            angle = math.radians(22.5 + 45 * index)
            rays.append(
                f'<line x1="{15 * math.cos(angle):.1f}" y1="{15 * math.sin(angle):.1f}" '
                f'x2="{11 * math.cos(angle):.1f}" y2="{11 * math.sin(angle):.1f}" />'
            )
        return '<circle cx="0" cy="0" r="7" />' + "".join(rays)
    if key == "virtues":
        # two rings, tied
        return '<circle cx="-6" cy="0" r="8" /><circle cx="6" cy="0" r="8" />'
    if key.startswith("virtue:"):
        # the ribbon of the virtue
        return (
            '<path d="M -6 -12 H 6 V 7 L 0 13 L -6 7 Z" '
            f'fill="{virtue_colour}" stroke="none" />'
        )
    if key == "fiefs":
        # a tower
        return '<path d="M -9 12 V -5 H -4.5 V -10 H 0 V -5 H 4.5 V -10 H 9 V 12 Z" />'
    # the vigil: the flame of the night watch
    return (
        '<path d="M 0 -13 C 7 -5 9 0 9 5 A 9 9 0 0 1 -9 5 C -9 0 -5 -4 0 -13 Z" />'
    )


def _tick_points(radius: float, tick: float) -> list[tuple[float, float, float, float]]:
    """The twelve notches of a frame."""
    points = []
    for index in range(12):
        angle = math.radians(30 * index)
        points.append(
            (
                (radius - tick) * math.cos(angle),
                (radius - tick) * math.sin(angle),
                radius * math.cos(angle),
                radius * math.sin(angle),
            )
        )
    return points


def _frame(radius: float, tick: float = 9.0) -> str:
    """The ring around a node: the notched frame of the game."""
    return (
        f'<circle class="skill-frame" r="{radius:.1f}" />'
        + "".join(
            f'<line class="skill-tick" x1="{x1:.1f}" y1="{y1:.1f}" '
            f'x2="{x2:.1f}" y2="{y2:.1f}" />'
            for x1, y1, x2, y2 in _tick_points(radius, tick)
        )
    )


def _arrow(x: float, y: float, colour: str) -> str:
    """The head of a path: the road shows where it goes."""
    return (
        f'<path class="skill-arrow" d="M {x - 8:.1f} {y - 11:.1f} '
        f"L {x + 9:.1f} {y:.1f} L {x - 8:.1f} {y + 11:.1f} Z\" fill=\"{colour}\" />"
    )


def _curve(x1: float, y1: float, x2: float, y2: float) -> str:
    """The path between two nodes: a soft curve, never a hard line."""
    middle = (y1 + y2) / 2
    return (
        f"M {x1:.1f} {y1:.1f} C {x1:.1f} {middle:.1f} "
        f"{x2:.1f} {middle:.1f} {x2:.1f} {y2:.1f}"
    )


def _defs() -> str:
    """The filters and the marks of the tree."""
    return (
        "<defs>"
        '<filter id="skill-glow" x="-70%" y="-70%" width="240%" height="240%">'
        '<feGaussianBlur stdDeviation="4" result="blur" />'
        '<feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>'
        "</filter>"
        '<radialGradient id="skill-floor" cx="50%" cy="30%" r="75%">'
        '<stop offset="0%" style="stop-color: var(--skill-floor-1)" />'
        '<stop offset="60%" style="stop-color: var(--skill-floor-2)" />'
        '<stop offset="100%" style="stop-color: var(--skill-floor-3)" />'
        "</radialGradient>"
        '<pattern id="skill-rings" width="220" height="220" '
        'patternUnits="userSpaceOnUse">'
        '<circle cx="110" cy="110" r="96" fill="none" stroke="#d4a72c" '
        'stroke-opacity="0.05" stroke-width="1" />'
        '<circle cx="110" cy="110" r="66" fill="none" stroke="#d4a72c" '
        'stroke-opacity="0.04" stroke-width="1" />'
        "</pattern>"
        "</defs>"
    )


def render_skill_tree(
    tree: SkillTree,
    *,
    badge_for: Callable[[str, str], str],
    virtue_colours: dict[str, str] | None = None,
    labels: dict[str, str] | None = None,
    detail_url: str = "/tree/node/{id}",
) -> str:
    """Draw the tree of the ranks.

    ``badge_for`` draws the badge of a rank in a state, the same way the
    hall of the honours draws it.
    """
    names = labels or {}
    colours = virtue_colours or {}
    places = {node.id: node for node in tree.nodes}
    body: list[str] = []

    body.append(
        f'<svg class="skill-tree" viewBox="0 0 {tree.width:.0f} {tree.height:.0f}" '
        f'width="{tree.width:.0f}" height="{tree.height:.0f}" '
        f'role="img" aria-label="{names.get("tree", "skill tree")}" '
        'xmlns="http://www.w3.org/2000/svg">'
    )
    body.append(_defs())
    body.append(
        f'<rect class="skill-floor" x="0" y="0" width="{tree.width:.0f}" '
        f'height="{tree.height:.0f}" fill="url(#skill-floor)" />'
    )
    body.append(
        f'<rect class="skill-rings" x="0" y="0" width="{tree.width:.0f}" '
        f'height="{tree.height:.0f}" fill="url(#skill-rings)" />'
    )

    # The paths: every road is drawn twice, a dark edge and a bright
    # core, so it reads as a road and not as a line.
    for edge in tree.edges:
        source = places.get(edge.source)
        target = places.get(edge.target)
        if source is None or target is None:
            continue
        if edge.state == OPEN:
            colour, cls, width, dash = GOLD, "skill-path open", 9, ""
        elif edge.state == READY:
            colour, cls, width, dash = GOLD_BRIGHT, "skill-path ready", 9, ""
        else:
            colour, cls, width, dash = GREY, "skill-path locked", 6, "12 11"
        if source.kind == "rank" and target.kind == "rank":
            x1, y1 = source.x, source.y - RANK_RADIUS + 4
            x2, y2 = target.x, target.y + RANK_RADIUS - 4
        else:
            x1, y1 = source.x, source.y
            x2, y2 = target.x, target.y
        road = _curve(x1, y1, x2, y2)
        body.append(
            f'<path class="{cls} skill-edge" d="{road}" stroke="{DARK}" '
            f'stroke-width="{width + 5}" fill="none" stroke-linecap="round" />'
        )
        body.append(
            f'<path class="{cls}" d="{road}" stroke="{colour}" '
            f'stroke-width="{width}" fill="none" stroke-linecap="round" '
            f'{f"stroke-dasharray=\"{dash}\"" if dash else ""} />'
        )
        if edge.state in (OPEN, READY):
            middle_x = (x1 + x2) / 2
            middle_y = (y1 + y2) / 2
            body.append(
                f'<path class="skill-knot" d="M {middle_x:.1f} {middle_y - 7:.1f} '
                f"L {middle_x + 6:.1f} {middle_y:.1f} L {middle_x:.1f} {middle_y + 7:.1f} "
                f'L {middle_x - 6:.1f} {middle_y:.1f} Z" fill="{colour}" />'
            )
        if source.kind == "rank" and target.kind == "rank":
            body.append(_arrow(target.x, target.y + RANK_RADIUS + 4, colour))

    # The gates: the medallions beside the ranks.
    for node in tree.nodes:
        if node.kind != "gate":
            continue
        state = MET if node.satisfied else UNMET
        body.append(
            f'<g class="skill-node skill-gate {state}" '
            f'transform="translate({node.x:.1f} {node.y:.1f})" '
            f'data-node="{node.id}" data-state="{state}" data-x="{node.x:.1f}" '
            f'data-y="{node.y:.1f}" tabindex="0" role="button" '
            f'hx-get="{detail_url.format(id=quote(node.id, safe=""))}" '
            f'hx-target="#tree-detail" hx-swap="innerHTML">'
        )
        body.append(f"<title>{node.label}</title>")
        body.append(
            f'<circle class="skill-disc" r="{GATE_RADIUS:.1f}" />'
        )
        body.append(
            f'<circle class="skill-medallion" r="{GATE_RADIUS - 4:.1f}" />'
        )
        rivets = []
        for index in range(8):
            angle = math.radians(22.5 + 45 * index)
            rivets.append(
                f'<circle class="skill-rivet" cx="{(GATE_RADIUS - 8) * math.cos(angle):.1f}" '
                f'cy="{(GATE_RADIUS - 8) * math.sin(angle):.1f}" r="1.5" />'
            )
        body.append("".join(rivets))
        body.append(
            f'<g class="skill-glyph" fill="{GOLD if node.satisfied else GREY}" '
            f'stroke="{GOLD if node.satisfied else GREY}" stroke-width="1.8">'
            f"{_gate_glyph(node.gate_key, colours.get(node.gate_key, GOLD))}</g>"
        )
        body.append(
            f'<text class="skill-label skill-label-small" x="0" '
            f'y="{GATE_RADIUS + 17:.1f}" text-anchor="middle">{node.label}</text>'
        )
        body.append(
            f'<text class="skill-count" x="0" y="{GATE_RADIUS + 33:.1f}" '
            f'text-anchor="middle">{node.current}/{node.required}</text>'
        )
        body.append("</g>")

    # The ranks: the shield of the badge, inside a frame of notches.
    for node in tree.nodes:
        if node.kind != "rank":
            continue
        body.append(
            f'<g class="skill-node skill-rank {node.state}" '
            f'transform="translate({node.x:.1f} {node.y:.1f})" '
            f'data-node="{node.id}" data-state="{node.state}" data-x="{node.x:.1f}" '
            f'data-y="{node.y:.1f}" tabindex="0" role="button" '
            f'hx-get="{detail_url.format(id=quote(node.id, safe=""))}" '
            f'hx-target="#tree-detail" hx-swap="innerHTML">'
        )
        body.append(f"<title>{node.label}</title>")
        if node.state == CURRENT:
            body.append('<circle class="skill-halo" r="66" />')
        body.append(f'<circle class="skill-disc" r="{RANK_RADIUS - 2:.1f}" />')
        body.append(_frame(RANK_RADIUS))
        badge_state = "locked" if node.state == LOCKED else "lit"
        drawn = badge_for(node.title_key, badge_state)
        body.append(
            f'<g class="skill-badge" transform="translate(-42 -50) scale(0.88)">{drawn}</g>'
        )
        # The name of the rank rides on a ribbon, the way a name rides on
        # a banner.
        banner_y = RANK_RADIUS + 12
        body.append(
            f'<g class="skill-banner" transform="translate(0 {banner_y:.1f})">'
            '<path class="skill-banner-band" d="M -46 0 H 46 V 22 H -46 Z" />'
            '<path class="skill-banner-tail" d="M -46 0 L -58 11 L -46 22 Z" />'
            '<path class="skill-banner-tail" d="M 46 0 L 58 11 L 46 22 Z" />'
            "</g>"
        )
        body.append(
            f'<text class="skill-label skill-label-banner" x="0" '
            f'y="{banner_y + 16:.1f}" text-anchor="middle">{node.label}</text>'
        )
        if node.state == CURRENT:
            body.append(
                '<g class="skill-here" transform="translate(0 -74)">'
                '<path d="M -13 6 L -13 -4 L -6.5 1 L 0 -7 L 6.5 1 L 13 -4 L 13 6 Z" />'
                "</g>"
            )
        body.append("</g>")

    body.append("</svg>")
    return "".join(body)
