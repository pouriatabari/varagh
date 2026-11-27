"""The drawing of the tree of the ranks.

The tree is drawn by the code: the ranks are the shields of the badges
that the app already draws, the gates are the small medallions that hang
under them, and the paths between them are the gold of the road that has
been walked and the grey of the road that has not.

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

GATE_RADIUS = 17.0
RANK_RADIUS = 58.0
BADGE_SCALE = 0.72
BADGE_HALF_W = 26.6
BADGE_HALF_H = 31.3


def _gate_glyph(key: str, virtue_colour: str) -> str:
    """The mark of a gate: a small sign that tells what it asks for."""
    if key == "degrees":
        # the chevrons of a rank
        return (
            '<path d="M -8 -6 L 0 -9 L 8 -6" /><path d="M -8 1 L 0 -2 L 8 1" />'
            '<path d="M -8 8 L 0 5 L 8 8" />'
        )
    if key == "musters":
        # the roll call: a ring of dots
        dots = []
        for index in range(7):
            angle = math.radians(-90 + 360 * index / 7)
            dots.append(
                f'<circle cx="{9 * math.cos(angle):.1f}" '
                f'cy="{9 * math.sin(angle):.1f}" r="2" />'
            )
        return "".join(dots)
    if key == "silver":
        # the crescent
        return '<path d="M 4 -9 A 9.5 9.5 0 1 0 4 9 A 7 7 0 1 1 4 -9 Z" />'
    if key == "gold":
        # the sun
        rays = []
        for index in range(8):
            angle = math.radians(22.5 + 45 * index)
            rays.append(
                f'<line x1="{11 * math.cos(angle):.1f}" y1="{11 * math.sin(angle):.1f}" '
                f'x2="{8 * math.cos(angle):.1f}" y2="{8 * math.sin(angle):.1f}" />'
            )
        return '<circle cx="0" cy="0" r="5" />' + "".join(rays)
    if key == "virtues":
        # two rings, tied
        return '<circle cx="-5" cy="0" r="5.5" /><circle cx="5" cy="0" r="5.5" />'
    if key.startswith("virtue:"):
        # the ribbon of the virtue
        return (
            '<path d="M -4.5 -9 H 4.5 V 5 L 0 10 L -4.5 5 Z" '
            f'fill="{virtue_colour}" stroke="none" />'
        )
    if key == "fiefs":
        # a tower
        return '<path d="M -7 9 V -4 H -3.5 V -8 H 0 V -4 H 3.5 V -8 H 7 V 9 Z" />'
    # the vigil: the flame of the night watch
    return (
        '<path d="M 0 -10 C 5 -4 7 0 7 4 A 7 7 0 0 1 -7 4 C -7 0 -4 -3 0 -10 Z" />'
    )


def _rivets(radius: float, count: int, dot: float) -> str:
    """The rivets that hold the rim of a medallion."""
    return "".join(
        f'<circle class="skill-rivet" cx="{(radius - dot) * math.cos(angle):.1f}" '
        f'cy="{(radius - dot) * math.sin(angle):.1f}" r="{dot * 0.42:.1f}" />'
        for angle in (
            math.radians(360 / count * index) for index in range(count)
        )
    )


def _frame(radius: float, count: int = 12) -> str:
    """The rim around a node: the gold ring of a medallion."""
    return (
        f'<circle class="skill-frame" r="{radius:.1f}" />'
        f'<circle class="skill-frame-inner" r="{radius - 7:.1f}" />'
        + _rivets(radius, count, 6.0)
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
            colour, cls, width, dash = GOLD, "skill-path open", 5, ""
        elif edge.state == READY:
            colour, cls, width, dash = GOLD_BRIGHT, "skill-path ready", 5, ""
        else:
            colour, cls, width, dash = GREY, "skill-path locked", 3, "9 8"
        if source.kind == "rank" and target.kind == "rank":
            # The road of the ladder runs from the right of a rank to the
            # left of the next one.
            x1 = source.x + RANK_RADIUS - 6
            x2 = target.x - RANK_RADIUS + 6
            y1 = y2 = source.y
            middle = (x1 + x2) / 2
            road = (
                f"M {x1:.1f} {y1:.1f} C {middle:.1f} {y1 - 14:.1f} "
                f"{middle:.1f} {y2 + 14:.1f} {x2:.1f} {y2:.1f}"
            )
        else:
            # The stem of a gate: it hangs straight under its rank.
            x1 = x2 = source.x
            y1 = source.y - GATE_RADIUS - 3
            y2 = target.y + RANK_RADIUS - 6
            road = f"M {x1:.1f} {y1:.1f} L {x2:.1f} {y2:.1f}"
        body.append(
            f'<path class="{cls} skill-edge" d="{road}" stroke="{DARK}" '
            f'stroke-width="{width + 4}" fill="none" stroke-linecap="round" />'
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
                f'<path class="skill-knot" d="M {middle_x:.1f} {middle_y - 5:.1f} '
                f"L {middle_x + 4:.1f} {middle_y:.1f} L {middle_x:.1f} {middle_y + 5:.1f} "
                f'L {middle_x - 4:.1f} {middle_y:.1f} Z" fill="{colour}" />'
            )

    # The gates: the small medallions that hang under the ranks.
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
            f'hx-target="#tree-detail" hx-swap="innerHTML show:#tree-detail">'
        )
        body.append(f"<title>{node.label}</title>")
        body.append(f'<circle class="skill-disc" r="{GATE_RADIUS + 2:.1f}" />')
        body.append(
            f'<circle class="skill-medallion" r="{GATE_RADIUS - 2:.1f}" />'
        )
        body.append(_rivets(GATE_RADIUS, 8, 4.0))
        body.append(
            f'<g class="skill-glyph" fill="{GOLD if node.satisfied else GREY}" '
            f'stroke="{GOLD if node.satisfied else GREY}" stroke-width="1.6">'
            f"{_gate_glyph(node.gate_key, colours.get(node.gate_key, GOLD))}</g>"
        )
        body.append(
            f'<text class="skill-label skill-label-small" x="0" '
            f'y="{GATE_RADIUS + 16:.1f}" text-anchor="middle">{node.label}</text>'
        )
        body.append(
            f'<text class="skill-count" x="0" y="{GATE_RADIUS + 30:.1f}" '
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
            f'hx-target="#tree-detail" hx-swap="innerHTML show:#tree-detail">'
        )
        body.append(f"<title>{node.label}</title>")
        if node.state == CURRENT:
            body.append(f'<circle class="skill-halo" r="{RANK_RADIUS + 8:.1f}" />')
        body.append(f'<circle class="skill-disc" r="{RANK_RADIUS - 2:.1f}" />')
        body.append(_frame(RANK_RADIUS))
        badge_state = "locked" if node.state == LOCKED else "lit"
        drawn = badge_for(node.title_key, badge_state)
        body.append(
            f'<g class="skill-badge" transform="translate(-{BADGE_HALF_W} '
            f'-{BADGE_HALF_H}) scale({BADGE_SCALE})">{drawn}</g>'
        )
        # The name of the rank rides above it, the way a name rides on
        # the banner of a lord.
        body.append(
            f'<text class="skill-label skill-label-banner" x="0" '
            f'y="{-RANK_RADIUS - 14:.1f}" text-anchor="middle">{node.label}</text>'
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
