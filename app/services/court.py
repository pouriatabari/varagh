"""The round table of the virtues.

The table is the circle of the six virtues. Each seat lights as far as
the medals of that virtue have carried the user.

The ladder of the titles is drawn by the tree of the ranks
(:mod:`app.insignia.skill_tree`), not from here.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

# The order of the virtues around the table.
VIRTUE_ORDER = ("prowess", "valor", "wisdom", "loyalty", "largesse", "temperance")


@dataclass(frozen=True)
class Seat:
    """One seat of the round table."""

    virtue: str
    count: int
    share: float = 0.0


# The colours of the seats: the six steps of the categorical palette of
# the theme, in a fixed order. The colour tells which virtue a seat is;
# the length of the lit arc tells how far that virtue has carried the
# user.
SEAT_COLOURS = 6


def _wedge(
    middle: float, radius: float, inner: float, start: float, end: float
) -> str:
    """The path of a piece of the table, between two angles."""
    x1 = middle + radius * math.cos(start)
    y1 = middle + radius * math.sin(start)
    x2 = middle + radius * math.cos(end)
    y2 = middle + radius * math.sin(end)
    x3 = middle + inner * math.cos(end)
    y3 = middle + inner * math.sin(end)
    x4 = middle + inner * math.cos(start)
    y4 = middle + inner * math.sin(start)
    return (
        f"M {x1:.1f} {y1:.1f} A {radius} {radius} 0 0 1 {x2:.1f} {y2:.1f} "
        f"L {x3:.1f} {y3:.1f} A {inner} {inner} 0 0 0 {x4:.1f} {y4:.1f} Z"
    )


def round_table_svg(
    seats: Sequence[Seat],
    *,
    size: int = 260,
    labels: dict[str, str] | None = None,
    centre: str = "",
) -> str:
    """The circle of the six virtues.

    Each seat is a piece of the table. The colour of the seat tells which
    virtue it is, and the length of the lit arc tells how far the medals
    of that virtue have carried the user: a seat with no medal stays
    empty.
    """
    count = len(seats)
    middle = size / 2
    radius = size / 2 - 12
    inner = radius * 0.42
    names = labels or {}
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
        gap = 3
        start = math.radians(angle - step / 2 + gap)
        end = math.radians(angle + step / 2 - gap)
        colour = (index % SEAT_COLOURS) + 1
        name = names.get(seat.virtue, seat.virtue)
        classes = "seat lit" if seat.count > 0 else "seat locked"
        body.append(f'<g class="{classes}" style="--seat-color: var(--viz-{colour})">')
        body.append(f"<title>{name}</title>")
        body.append(
            f'<path class="seat-track" d="{_wedge(middle, radius, inner, start, end)}" />'
        )
        if seat.count > 0 and seat.share > 0:
            lit_end = start + (end - start) * min(seat.share, 1.0)
            body.append(
                f'<path class="seat-bar" d="{_wedge(middle, radius, inner, start, lit_end)}" />'
            )
        label_x = middle + (radius + inner) / 2 * math.cos(math.radians(angle))
        label_y = middle + (radius + inner) / 2 * math.sin(math.radians(angle))
        body.append(
            f'<text x="{label_x:.1f}" y="{label_y:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle">{seat.count}</text>'
        )
        body.append("</g>")
    if centre:
        body.append(
            f'<text class="table-centre" x="{middle}" y="{middle}" text-anchor="middle" '
            f'dominant-baseline="middle">{centre}</text>'
        )
    body.append("</svg>")
    return "".join(body)
