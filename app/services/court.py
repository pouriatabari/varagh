"""The court chart and the round table.

The chart is the pyramid of the titles: the page at the bottom, the king
at the top. The tiers that were reached are lit, the others are locked,
and the tier of the user is the one that shines.

The round table is the circle of the six virtues. Each seat lights as
far as the medals of that virtue have carried the user.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# The order of the virtues around the table.
VIRTUE_ORDER = ("prowess", "valor", "wisdom", "loyalty", "largesse", "temperance")


@dataclass(frozen=True)
class CourtTier:
    """One tier of the pyramid."""

    key: str
    reached: bool
    current: bool
    next: bool
    progress: float = 0.0


def court_chart_svg(
    tiers: Sequence[CourtTier],
    *,
    labels: dict[str, str] | None = None,
    width: int = 320,
    row_height: int = 34,
) -> str:
    """The pyramid of the titles, from the page at the bottom to the king.

    The tiers are drawn from the top (the highest title) down, so the
    page is at the bottom of the picture. The labels are the words of
    the interface; they are given from the outside, so the picture stays
    a picture and not a page.
    """
    count = len(tiers)
    height = count * row_height + 16
    names = labels or {}
    top_half = width * 0.17
    bottom_half = width * 0.5
    span = (bottom_half - top_half) / max(count, 1)
    body = [
        f'<svg class="court-chart" viewBox="0 0 {width} {height}" width="{width}" '
        f'height="{height}" role="img" aria-label="court chart" '
        'xmlns="http://www.w3.org/2000/svg">',
    ]
    for index, tier in enumerate(reversed(tiers)):
        # The first drawn row is the highest title.
        level = index
        half_top = top_half + span * level
        half_bottom = half_top + span
        middle = width / 2
        y = 8 + index * row_height
        classes = "court-tier"
        if tier.reached:
            classes += " lit"
        else:
            classes += " locked"
        if tier.current:
            classes += " current"
        if tier.next:
            classes += " next"
        body.append(
            f'<g class="{classes}">'
            f'<path d="M {middle - half_top:.1f} {y} H {middle + half_top:.1f} '
            f'L {middle + half_bottom:.1f} {y + row_height - 3} '
            f'H {middle - half_bottom:.1f} Z" />'
            f'<text x="{middle:.1f}" y="{y + row_height / 2 + 4:.1f}" '
            f'text-anchor="middle">{names.get(tier.key, tier.key)}</text>'
            "</g>"
        )
    body.append("</svg>")
    return "".join(body)


@dataclass(frozen=True)
class Seat:
    """One seat of the round table."""

    virtue: str
    count: int
    share: float = 0.0


def round_table_svg(seats: Sequence[Seat], *, size: int = 260) -> str:
    """The circle of the six virtues.

    Each seat is a wedge of the table that lights as far as the medals of
    that virtue have carried the user.
    """
    count = len(seats)
    middle = size / 2
    radius = size / 2 - 12
    inner = radius * 0.42
    body = [
        f'<svg class="round-table" viewBox="0 0 {size} {size}" width="{size}" '
        f'height="{size}" role="img" aria-label="round table" '
        'xmlns="http://www.w3.org/2000/svg">',
        f'<circle class="table-top" cx="{middle}" cy="{middle}" r="{radius}" />',
        f'<circle class="table-hole" cx="{middle}" cy="{middle}" r="{inner}" />',
    ]
    step = 360 / count if count else 360
    for index, seat in enumerate(seats):
        angle = -90 + index * step
        start = math.radians(angle - step / 2 + 3)
        end = math.radians(angle + step / 2 - 3)
        x1 = middle + radius * math.cos(start)
        y1 = middle + radius * math.sin(start)
        x2 = middle + radius * math.cos(end)
        y2 = middle + radius * math.sin(end)
        x3 = middle + inner * math.cos(end)
        y3 = middle + inner * math.sin(end)
        x4 = middle + inner * math.cos(start)
        y4 = middle + inner * math.sin(start)
        classes = "seat"
        if seat.count > 0:
            classes += " lit"
        else:
            classes += " locked"
        label_x = middle + (radius + inner) / 2 * math.cos(math.radians(angle))
        label_y = middle + (radius + inner) / 2 * math.sin(math.radians(angle))
        body.append(
            f'<g class="{classes}">'
            f'<path d="M {x1:.1f} {y1:.1f} A {radius} {radius} 0 0 1 {x2:.1f} {y2:.1f} '
            f'L {x3:.1f} {y3:.1f} A {inner} {inner} 0 0 0 {x4:.1f} {y4:.1f} Z" '
            f'style="--seat-light: {seat.share * 100:.1f}%" />'
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle">{seat.count}</text>'
            "</g>"
        )
    body.append("</svg>")
    return "".join(body)
