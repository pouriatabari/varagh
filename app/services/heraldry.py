"""The heraldry of the hall: a coat of arms, drawn from the work.

The generator is deterministic: the same title, the same domains and the
same virtues always give the same SVG. Nothing here asks the AI for
anything; the arms are a reading of the database, not a picture of it.

The colours come from the domains the user works in (a stable colour per
domain) and the charges come from the strongest virtues.
"""

from __future__ import annotations

import math
import zlib
from collections.abc import Sequence

# The field colours of the arms, in the order they are handed out.
FIELD_COLOURS = (
    "#8c2f39",  # the crimson of the deep winter
    "#2f4f8c",  # the blue of the sea
    "#2f6f4f",  # the green of the wood
    "#8c6a2f",  # the gold of the harvest
    "#5a2f8c",  # the purple of the hills
    "#8c4a2f",  # the brown of the road
)

# The charges of the six virtues.
VIRTUE_CHARGES = {
    "prowess": "cross",
    "valor": "chevron",
    "wisdom": "star",
    "loyalty": "bend",
    "largesse": "crescent",
    "temperance": "saltire",
}

# The crown of every title, from the lowest to the highest.
TITLE_CROWNS = {
    "page": "none",
    "squire": "none",
    "knight": "helmet",
    "banneret": "banner",
    "baron": "coronet",
    "viscount": "coronet",
    "earl": "coronet",
    "marquess": "coronet",
    "duke": "crown",
    "prince": "crown",
    "king": "great-crown",
    "bretwalda": "great-crown",
}

# The tinctures of the charges, in the order they are handed out.
CHARGE_COLOURS = ("#e8c96a", "#f0e6d0", "#d9b45a", "#f5efe0")


def domain_colour(domain: str) -> str:
    """The colour of a domain, always the same for the same name."""
    if not domain:
        return FIELD_COLOURS[0]
    index = zlib.crc32(domain.encode("utf-8")) % len(FIELD_COLOURS)
    return FIELD_COLOURS[index]


def charge_colour(virtue: str) -> str:
    """The colour of the charge of a virtue, always the same."""
    index = zlib.crc32(virtue.encode("utf-8")) % len(CHARGE_COLOURS)
    return CHARGE_COLOURS[index]


def _shield_path(width: float = 132.0, height: float = 152.0) -> str:
    """The path of the shield: a heater shield with a rounded point."""
    left = 8.0
    right = left + width
    middle = (left + right) / 2
    top = 10.0
    bottom = top + height
    shoulder = top + height * 0.18
    return (
        f"M {left} {top} "
        f"H {right} "
        f"V {shoulder} "
        f"C {right} {bottom - height * 0.28}, {middle + width * 0.22} {bottom - height * 0.08}, "
        f"{middle} {bottom} "
        f"C {middle - width * 0.22} {bottom - height * 0.08}, {left} {bottom - height * 0.28}, "
        f"{left} {shoulder} "
        "Z"
    )


def _charge_path(kind: str, size: float = 44.0) -> str:
    """The path of a charge, drawn around the middle of the shield."""
    half = size / 2
    if kind == "cross":
        arm = size * 0.22
        return (
            f"M {arm} 0 H {size - arm} V {arm} H {size} V {size - arm} H {size - arm} "
            f"V {size} H {arm} V {size - arm} H 0 V {arm} H {arm} Z"
        )
    if kind == "chevron":
        return f"M 0 0 L {size} 0 L {size} {size * 0.34} L {half} {size * 0.72} L 0 {size * 0.34} Z"
    if kind == "bend":
        return f"M 0 0 L {size * 0.34} 0 L {size} {size} L {size * 0.66} {size} Z"
    if kind == "saltire":
        arm = size * 0.14
        long = size * 0.42
        return (
            f"M {half - arm} {half - long} L {half + long} {half + long} "
            f"L {half + arm} {half + long} L {half - long} {half - long} Z "
            f"M {half - long} {half + long} L {half + long} {half - long} "
            f"L {half + arm} {half - long} L {half - arm} {half + long} Z"
        )
    if kind == "crescent":
        return (
            f"M {half} {half - size * 0.44} "
            f"A {size * 0.44} {size * 0.44} 0 1 0 0 {size * 0.88} "
            f"A {size * 0.32} {size * 0.32} 0 1 1 0 {-size * 0.88} Z"
        )
    if kind == "star":
        points = []
        for index in range(10):
            radius = size * 0.46 if index % 2 == 0 else size * 0.19
            angle = -1.5708 + index * 0.6283
            points.append(
                f"{half + radius * math.cos(angle):.2f} "
                f"{half + radius * math.sin(angle):.2f}"
            )
        return "M " + " L ".join(points) + " Z"
    return ""


def _crown_svg(kind: str) -> str:
    """The crown of a title, above the shield."""
    if kind == "none":
        return ""
    left = 8.0
    if kind == "helmet":
        return (
            f'<path d="M {left + 22} 12 C {left + 30} -4, {left + 102} -4, {left + 110} 12 '
            f'L {left + 104} 16 L {left + 28} 16 Z" fill="var(--accent-2)" '
            'stroke="var(--accent)" stroke-width="2" />'
        )
    if kind == "banner":
        return (
            f'<path d="M {left + 30} 14 L {left + 102} 14 L {left + 102} 2 L {left + 66} 8 '
            f'L {left + 30} 2 Z" fill="var(--accent-2)" stroke="var(--accent)" stroke-width="2" />'
        )
    if kind == "coronet":
        return (
            f'<path d="M {left + 26} 16 L {left + 26} 2 L {left + 48} 12 L {left + 66} 0 '
            f'L {left + 84} 12 L {left + 106} 2 L {left + 106} 16 Z" fill="var(--accent)" '
            'stroke="var(--accent)" stroke-width="2" />'
        )
    if kind == "crown":
        return (
            f'<path d="M {left + 24} 16 L {left + 24} 0 L {left + 46} 10 L {left + 66} -2 '
            f'L {left + 86} 10 L {left + 108} 0 L {left + 108} 16 Z" fill="var(--accent)" '
            'stroke="var(--accent)" stroke-width="2" />'
        )
    if kind == "great-crown":
        return (
            f'<path d="M {left + 20} 16 L {left + 20} -4 L {left + 44} 8 L {left + 66} -6 '
            f'L {left + 88} 8 L {left + 112} -4 L {left + 112} 16 Z" fill="var(--accent)" '
            'stroke="var(--accent)" stroke-width="2" />'
            f'<circle cx="{left + 66}" cy="-12" r="4" fill="var(--accent-2)" />'
        )
    return ""


def heraldry_svg(
    *,
    title_key: str = "page",
    domains: Sequence[str] = (),
    virtues: Sequence[str] = (),
    size: int = 160,
) -> str:
    """The coat of arms of the user.

    The field is the colour of the domain the user works in most, the
    charges are the virtues the medals stand for, and the crown is the
    crown of the title. The same inputs always give the same arms.
    """
    field = domain_colour(domains[0] if domains else "")
    charges = [virtue for virtue in VIRTUE_CHARGES if virtue in virtues][:2]
    crown = TITLE_CROWNS.get(title_key, "none")
    width = 148
    height = 178
    body = [
        f'<svg class="heraldry" viewBox="0 0 {width} {height}" width="{size}" '
        f'height="{int(size * height / width)}" role="img" '
        f'aria-label="heraldry" xmlns="http://www.w3.org/2000/svg">',
        _crown_svg(crown),
        f'<path d="{_shield_path()}" fill="{field}" stroke="var(--accent)" stroke-width="3" />',
    ]
    for index, virtue in enumerate(charges):
        kind = VIRTUE_CHARGES[virtue]
        offset = 0 if index == 0 else 10
        transform = f"translate(52 {74 + offset}) scale(0.72)"
        body.append(
            f'<g transform="{transform}" fill="{charge_colour(virtue)}" '
            f'stroke="var(--text)" stroke-width="1.5" opacity="0.92">'
            f'<path d="{_charge_path(kind)}" /></g>'
        )
    body.append("</svg>")
    return "".join(body)
