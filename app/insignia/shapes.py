"""The small shapes of the insignia.

Every primitive here is a pure function of numbers: the same numbers
give the same picture, and the tests can count the pearls, the leaves,
the arches and the rays of the picture because they are drawn one by one
and each one carries its own class.
"""

from __future__ import annotations

import math

# The picture of a badge lives in this box.
VIEWBOX = "0 0 100 118"

# The heater shield: flat at the top, straight at the sides, a point at
# the bottom.
SHIELD_PATH = (
    "M 15 34 H 85 V 64 C 85 86 70 100 50 109 C 30 100 15 86 15 64 Z"
)

# The band that every coronet and every crown stands on.
BAND_PATH = "M 26 30 H 74 L 70 22 H 30 Z"

# The strawberry leaf of the peerage.
LEAF_PATH = (
    "M 0 0 C -3.5 -1.5 -4 -6 -1.6 -8 C -1 -9.2 -0.5 -9.2 0 -8.6 "
    "C 0.5 -9.2 1 -9.2 1.6 -8 C 4 -6 3.5 -1.5 0 0 Z"
)

# The cross pattee of the crown of the prince.
CROSS_PATH = (
    "M -1.2 -6 H 1.2 V -3 H 4.2 V -1 H 1.2 V 1 H 4.2 V 3 H 1.2 V 6 "
    "H -1.2 V 3 H -4.2 V 1 H -1.2 V -1 H -4.2 V -3 H -1.2 Z"
)

# The fleur-de-lis of the crown of the prince.
FLEUR_PATH = (
    "M 0 -8 C 1.6 -5 1.6 -2 0 0 C -1.6 -2 -1.6 -5 0 -8 Z "
    "M -4.5 -4 C -2.5 -3 -1.2 -1 0 2 C 1.2 -1 2.5 -3 4.5 -4 "
    "C 3.5 -1 3.5 1 4.5 3 H -4.5 C -3.5 1 -3.5 -1 -4.5 -4 Z"
)

# The small island of the badge of the last title.
ISLAND_PATH = "M 28 80 L 40 66 L 48 73 L 58 62 L 72 80 Z"


def _points(count: int, left: float, right: float) -> list[float]:
    """The x of every element of a row, spread evenly and symmetrically."""
    if count <= 0:
        return []
    if count == 1:
        return [(left + right) / 2]
    step = (right - left) / (count - 1)
    return [left + index * step for index in range(count)]


def shield() -> str:
    """The ground of the badge: a plain heater shield."""
    return f'<path class="insignia-shield" d="{SHIELD_PATH}" />'


def rim(metal: str) -> str:
    """The frame of the shield, in the metal of the title."""
    return (
        f'<path class="insignia-rim" d="{SHIELD_PATH}" '
        f'style="--insignia-metal: var(--insignia-{metal})" />'
    )


def pearls(positions: list[float], y: float, *, raised: bool = False) -> str:
    """The pearls of a coronet, one circle each."""
    body = []
    for x in positions:
        body.append(
            f'<g class="insignia-pearl" transform="translate({x:.2f} {y:.2f})">'
            + ('<line class="insignia-spike" x1="0" y1="0" x2="0" y2="6" />'
               if raised else "")
            + '<circle r="2.2" /></g>'
        )
    return "".join(body)


def leaves(positions: list[float], y: float) -> str:
    """The strawberry leaves of a coronet, one leaf each."""
    body = []
    for x in positions:
        body.append(
            f'<g class="insignia-leaf" transform="translate({x:.2f} {y:.2f}) scale(0.7)">'
            f'<path d="{LEAF_PATH}" /><line x1="0" y1="0" x2="0" y2="3" /></g>'
        )
    return "".join(body)


def crosses(positions: list[float], y: float) -> str:
    """The crosses pattee of the crown of the prince."""
    body = []
    for x in positions:
        body.append(
            f'<g class="insignia-cross-patte" transform="translate({x:.2f} {y:.2f}) scale(0.8)">'
            f'<path d="{CROSS_PATH}" /></g>'
        )
    return "".join(body)


def fleurs(positions: list[float], y: float) -> str:
    """The fleurs-de-lis of the crown of the prince."""
    body = []
    for x in positions:
        body.append(
            f'<g class="insignia-fleur" transform="translate({x:.2f} {y:.2f}) scale(0.8)">'
            f'<path d="{FLEUR_PATH}" /></g>'
        )
    return "".join(body)


def band() -> str:
    """The rim every coronet and every crown stands on."""
    return f'<path class="insignia-band" d="{BAND_PATH}" />'


def crown_points() -> str:
    """The points of the closed crown of the king."""
    return (
        '<path class="insignia-crown-points" d="M 30 22 L 34 11 L 40 20 '
        'L 46 10 L 52 20 L 58 10 L 64 20 L 70 11 L 72 22 Z" />'
    )


def arches(count: int) -> str:
    """The arches of a crown: one for the prince, two for the king."""
    body = []
    if count == 1:
        body.append(
            '<path class="insignia-arch" d="M 28 22 Q 50 4 72 22" />'
        )
    elif count >= 2:
        body.append('<path class="insignia-arch" d="M 32 22 Q 42 8 50 11" />')
        body.append('<path class="insignia-arch" d="M 68 22 Q 58 8 50 11" />')
    return "".join(body)


def orb_and_cross() -> str:
    """The orb and the cross on the top of a crown."""
    return (
        '<g class="insignia-orb">'
        '<circle cx="50" cy="9" r="4" />'
        '<g class="insignia-cross" transform="translate(50 2)">'
        '<path d="M -1 -4 H 1 V -1.5 H 3.5 V 0.5 H 1 V 4 H -1 V 0.5 '
        'H -3.5 V -1.5 H -1 Z" /></g></g>'
    )


def rays(count: int) -> str:
    """The rays around the crown of the last title."""
    if count <= 0:
        return ""
    body = []
    for index in range(count):
        angle = math.radians(-90 + 360 * index / count)
        x1 = 50 + 20 * math.cos(angle)
        y1 = 16 + 20 * math.sin(angle)
        x2 = 50 + 30 * math.cos(angle)
        y2 = 16 + 30 * math.sin(angle)
        body.append(
            f'<line class="insignia-ray" x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" />'
        )
    return "".join(body)


def spurs(count: int) -> str:
    """The crossed spurs of the squire."""
    body = []
    for index in range(max(count, 0)):
        angle = 40 if index % 2 == 0 else -40
        body.append(
            f'<g class="insignia-spur" transform="translate(50 68) rotate({angle})">'
            '<circle class="insignia-rowel" cx="0" cy="-10" r="5.5" />'
            '<path class="insignia-spur-star" d="M 0 -17 L 1.6 -13 L 5.6 -14 '
            'L 3.2 -10.6 L 4.8 -7 L 1 -7.8 L -2 -5.6 L -2.8 -9.4 L -6.4 -9 '
            'L -3.6 -12.4 L -4 -16 Z" />'
            '<path class="insignia-neck" d="M -1 -5 Q -6 2 -3 10 Q 0 16 4 12" />'
            "</g>"
        )
    return "".join(body)


def sword() -> str:
    """The upright sword of the knight."""
    return (
        '<g class="insignia-sword" transform="translate(50 68)">'
        '<path class="insignia-blade" d="M 0 -22 L 3 -14 L 3 8 L -3 8 L -3 -14 Z" />'
        '<path class="insignia-guard" d="M -14 8 H 14 V 12 H -14 Z" />'
        '<path class="insignia-grip" d="M -2 12 H 2 V 22 H -2 Z" />'
        '<circle class="insignia-pommel" cx="0" cy="24" r="3.2" />'
        "</g>"
    )


def banner() -> str:
    """The square banner of the banneret, on its lance."""
    return (
        '<g class="insignia-banner" transform="translate(50 68)">'
        '<path class="insignia-lance" d="M -8 -26 H -5 V 24 H -8 Z" />'
        '<circle class="insignia-finial" cx="-6.5" cy="-27" r="2.4" />'
        '<path class="insignia-flag" d="M -5 -24 H 20 V -2 H -5 Z" />'
        '<path class="insignia-flag-cross" d="M -5 -18 H 20 V -14 H -5 Z '
        'M 5 -24 H 9 V -2 H 5 Z" />'
        "</g>"
    )


def island() -> str:
    """The small island on the shield of the last title."""
    return (
        '<g class="insignia-island">'
        f'<path d="{ISLAND_PATH}" />'
        '<path class="insignia-wave" d="M 26 84 Q 34 80 42 84 T 58 84 T 74 84" />'
        "</g>"
    )


def studs(filled: int, total: int) -> str:
    """The studs of the degrees: the filled ones and the hollow ones.

    At most twelve studs are drawn; when there are more, the number is
    written by the caller beside them.
    """
    if total <= 0:
        return ""
    drawn = min(total, 12)
    body = []
    rows = [drawn] if drawn <= 6 else [6, drawn - 6]
    index = 0
    for row, count in enumerate(rows):
        y = 86 + row * 11
        for x in _points(count, 27, 73):
            filled_stud = index < filled
            body.append(
                f'<circle class="insignia-stud {"filled" if filled_stud else "hollow"}" '
                f'cx="{x:.2f}" cy="{y}" r="3.2" />'
            )
            index += 1
    return "".join(body)


def lock_glyph() -> str:
    """The little lock that says that the badge is not earned yet."""
    return (
        '<g class="insignia-lock" transform="translate(50 70)">'
        '<path d="M -5 0 H 5 V 10 H -5 Z" />'
        '<path class="insignia-lock-shackle" d="M -3 0 V -4 A 3 3 0 0 1 3 -4 V 0" />'
        "</g>"
    )


def progress_frame(filled: int, total: int) -> str:
    """The frame that shows how far the next title is.

    The frame is drawn as a dash of the rounded rectangle around the
    badge: the length of the dash is the share of the degrees that are
    done, so the progress is told by the picture and not by the colour.
    """
    if total <= 0:
        return ""
    share = max(0.0, min(1.0, filled / total))
    length = 2 * (92 + 114)
    dash = length * share
    return (
        f'<rect class="insignia-progress" x="4" y="2" width="92" height="114" '
        f'rx="10" pathLength="{length:.2f}" stroke-dasharray="{dash:.2f} {length:.2f}" />'
    )
