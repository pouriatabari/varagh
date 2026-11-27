"""The badge of a title.

The badge is drawn from the numbers of the catalogue: the shield, the
rim in the metal of the title, the emblem above or on the shield and the
studs of the degrees. The state of the badge is told three times: by
the words in the ``<title>``, by the lock of the locked badges and by
the progress frame of the next one, so the colour never carries the
meaning alone.
"""

from __future__ import annotations

from app.insignia import shapes
from app.insignia.catalog import Emblem, Title, title_of

# The three sizes of a badge, in pixels.
SIZES = {
    "sm": (40, 47),
    "md": (74, 87),
    "lg": (124, 146),
}

STATES = ("lit", "locked", "next")


def describe_emblem(emblem: Emblem) -> str:
    """A plain description of the emblem, when the caller gives none."""
    parts = ["a heater shield"]
    if emblem.kind == "spurs":
        parts.append(f"{emblem.count} crossed spurs")
    elif emblem.kind == "sword":
        parts.append("an upright sword")
    elif emblem.kind == "banner":
        parts.append("a square banner on a lance")
    elif emblem.kind == "coronet":
        if emblem.leaves_drawn:
            parts.append(f"a coronet with {emblem.leaves_drawn} leaves")
        if emblem.pearls_drawn:
            parts.append(f"{emblem.pearls_drawn} pearls")
        if emblem.crosses_drawn:
            parts.append(f"{emblem.crosses_drawn} crosses pattee")
        if emblem.fleurs_drawn:
            parts.append(f"{emblem.fleurs_drawn} fleurs-de-lis")
        if emblem.arches:
            parts.append(f"{emblem.arches} arch")
    elif emblem.kind == "crown":
        parts.append("a closed crown")
        parts.append(f"{emblem.arches} arches")
    if emblem.rays:
        parts.append(f"{emblem.rays} rays")
    if emblem.island:
        parts.append("a small island")
    return ", ".join(parts)


def _alternating(first: str, first_count: int, second: str, second_count: int) -> list[str]:
    """Two kinds of element that take turns, one after the other."""
    elements: list[str] = []
    for index in range(max(first_count, second_count)):
        if index < first_count:
            elements.append(first)
        if index < second_count:
            elements.append(second)
    return elements


def _coronet(emblem: Emblem) -> str:
    """The coronet or the crown that stands above the shield."""
    body = [shapes.band()]
    if emblem.kind == "crown":
        body.append(shapes.crown_points())
    else:
        # The elements of the rim, in the order of the title: the leaves
        # and the pearls alternate, and the pearls of an earl stand on
        # their spikes.
        elements: list[str] = []
        if emblem.leaves_drawn and emblem.pearls_drawn:
            elements = _alternating(
                "leaf", emblem.leaves_drawn, "pearl", emblem.pearls_drawn
            )
        elif emblem.leaves_drawn:
            elements = ["leaf"] * emblem.leaves_drawn
        elif emblem.pearls_drawn:
            elements = ["pearl"] * emblem.pearls_drawn
        if emblem.crosses_drawn or emblem.fleurs_drawn:
            elements = _alternating(
                "cross", emblem.crosses_drawn, "fleur", emblem.fleurs_drawn
            )
        positions = shapes._points(len(elements), 28, 72)
        leaf_positions: list[float] = []
        pearl_positions: list[float] = []
        cross_positions: list[float] = []
        fleur_positions: list[float] = []
        for kind in elements:
            x = positions.pop(0)
            if kind == "leaf":
                leaf_positions.append(x)
            elif kind == "pearl":
                pearl_positions.append(x)
            elif kind == "cross":
                cross_positions.append(x)
            else:
                fleur_positions.append(x)
        # The pearls of a peerage stand at the level of the leaves, and
        # the pearls of an earl are raised on their spikes.
        pearl_y = 12 if emblem.pearls_raised or emblem.leaves_drawn else 19
        body.append(shapes.leaves(leaf_positions, 12))
        body.append(shapes.pearls(pearl_positions, pearl_y, raised=emblem.pearls_raised))
        body.append(shapes.crosses(cross_positions, 12))
        body.append(shapes.fleurs(fleur_positions, 12))
    body.append(shapes.arches(emblem.arches))
    if emblem.orb_cross:
        body.append(shapes.orb_and_cross())
    return "".join(body)


def render_badge(
    title_key: str,
    studs_filled: int = 0,
    studs_total: int = 0,
    state: str = "lit",
    theme: str = "night",
    size: str = "md",
    *,
    name: str | None = None,
    desc: str | None = None,
) -> str:
    """Draw the badge of a title.

    The name and the description are given by the caller, so the words
    of the interface stay in the lexicon pack and never in the drawing.
    """
    title: Title | None = title_of(title_key)
    emblem = title.emblem if title is not None else Emblem(kind="plain_shield")
    metal = title.metal if title is not None else "iron"
    tincture = title.field if title is not None else "sable"
    width, height = SIZES.get(size, SIZES["md"])
    if state not in STATES:
        state = "lit"
    label = name if name is not None else title_key
    description = desc if desc is not None else describe_emblem(emblem)

    body: list[str] = []
    if emblem.rays:
        body.append(f'<g class="insignia-rays">{shapes.rays(emblem.rays)}</g>')
    body.append(f'<g class="insignia-crest">{_coronet(emblem)}</g>')

    ground = [shapes.shield(metal), shapes.field(tincture)]
    if emblem.kind == "spurs":
        ground.append(f'<g class="insignia-charge">{shapes.spurs(emblem.count)}</g>')
    elif emblem.kind == "sword":
        ground.append(f'<g class="insignia-charge">{shapes.sword()}</g>')
    elif emblem.kind == "banner":
        ground.append(f'<g class="insignia-charge">{shapes.banner()}</g>')
    if emblem.island:
        ground.append(shapes.island())
    body.append(f'<g class="insignia-ground">{"".join(ground)}</g>')

    body.append(f'<g class="insignia-studs">{shapes.studs(studs_filled, studs_total)}</g>')
    if studs_total > 12:
        # More than twelve studs would not fit on the shield: the twelve
        # that fit are drawn and the numbers stand beside them.
        body.append(
            f'<text class="insignia-stud-count" x="50" y="78" text-anchor="middle">'
            f"{studs_filled}/{studs_total}</text>"
        )
    if state == "locked":
        body.append(shapes.lock_glyph())
    if state == "next":
        frame = shapes.progress_frame(studs_filled, studs_total)
        body.append(f'<g class="insignia-progress">{frame}</g>')

    return (
        f'<svg class="insignia-badge insignia-{state}" data-theme="{theme}" '
        f'data-title="{title_key}" data-state="{state}" data-size="{size}" '
        f'width="{width}" height="{height}" viewBox="{shapes.VIEWBOX}" role="img" '
        f'aria-label="{label}">'
        f"<title>{label}</title><desc>{description}</desc>"
        f"{''.join(body)}</svg>"
    )
