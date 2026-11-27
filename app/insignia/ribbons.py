"""The ribbon rack of the hall.

Six ribbons, one for every virtue. Every ribbon has a colour AND a
stripe pattern, so the rack is never read by the colour alone, and a
pip on the top of the ribbon tells the highest tier that was earned in
that virtue. A virtue with no medal keeps its ribbon locked.
"""

from __future__ import annotations

from collections.abc import Callable

from app.insignia.catalog import load_virtues

# The three tiers of the medals, from the lowest to the highest.
TIERS = ("bronze", "silver", "gold")

# The metal of every tier.
TIER_COLOURS = {
    "bronze": "#b06a3b",
    "silver": "#9aa5b1",
    "gold": "#d4a72c",
}

# The sizes of the rack, in pixels.
SIZES = {
    "sm": (120, 60),
    "md": (240, 120),
    "lg": (360, 180),
}

# The pattern of every ribbon: the stripes that keep the colour from
# being the only sign.
PATTERNS = {
    "solid": None,
    "diagonal": '<path d="M 0 6 L 6 0 M -1 1 L 1 -1 M 5 7 L 7 5" />',
    "dots": '<circle cx="3" cy="3" r="1.1" /><circle cx="9" cy="9" r="1.1" />',
    "horizontal": '<path d="M 0 3 H 12 M 0 9 H 12" />',
    "vertical": '<path d="M 3 0 V 12 M 9 0 V 12" />',
    "chevron": '<path d="M 0 6 L 3 3 L 6 6 L 9 3 L 12 6" />',
}


def highest_tier(counts: dict[str, int]) -> str | None:
    """The best tier of a virtue, when it has any medal at all."""
    for tier in reversed(TIERS):
        if int(counts.get(tier, 0)) > 0:
            return tier
    return None


def _patterns() -> str:
    """The stripes of the ribbons."""
    body = []
    for name, drawing in PATTERNS.items():
        if drawing is None:
            continue
        body.append(
            f'<pattern id="ribbon-{name}" width="12" height="12" '
            f'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<g class="ribbon-stripe">{drawing}</g></pattern>'
        )
    return f'<defs>{"".join(body)}</defs>'


def render_ribbon_rack(
    virtue_stats: dict[str, dict[str, int]],
    theme: str = "night",
    size: str = "md",
    *,
    labels: dict[str, str] | None = None,
    tier_labels: dict[str, str] | None = None,
    label: str | None = None,
    digits: Callable[[int], str] | None = None,
) -> str:
    """Draw the rack of the six ribbons.

    ``virtue_stats`` says, for every virtue, how many medals of every
    tier were earned. The names of the virtues and of the tiers are
    given by the caller, so the words of the interface stay in the
    lexicon pack.
    """
    tier_names = tier_labels or {}
    number = digits or (lambda value: str(value))
    ribbons = load_virtues()
    names = labels or {}
    width, height = SIZES.get(size, SIZES["md"])
    keys = list(ribbons.keys())
    step = 19
    left = 4

    body: list[str] = []
    for index, key in enumerate(keys):
        ribbon = ribbons[key]
        counts = virtue_stats.get(key, {}) or {}
        tier = highest_tier(counts)
        x = left + index * step
        tooltip = names.get(key, key)
        if tier is not None:
            tooltip = f"{tooltip} — " + "، ".join(
                f"{tier_names.get(name, name)}: "
                f"{number(int(counts.get(name, 0)))}"
                for name in TIERS
            )
        classes = "ribbon lit" if tier else "ribbon locked"
        body.append(f'<g class="{classes}" data-virtue="{key}" data-tier="{tier or ""}">')
        body.append(f"<title>{tooltip}</title>")
        # The ribbon itself: a band with a notch at the end.
        colour = ribbon.color_dark if theme == "night" else ribbon.color
        body.append(
            f'<path class="ribbon-band" d="M {x} 18 H {x + 14} V 50 '
            f'L {x + 7} 44 L {x} 50 Z" style="--ribbon-color: {colour}" />'
        )
        if ribbon.pattern != "solid":
            body.append(
                f'<path class="ribbon-pattern" d="M {x} 18 H {x + 14} V 50 '
                f'L {x + 7} 44 L {x} 50 Z" fill="url(#ribbon-{ribbon.pattern})" />'
            )
        # The pip: the best tier of the virtue.
        pip_colour = TIER_COLOURS.get(tier or "", "var(--text-muted)")
        body.append(
            f'<circle class="ribbon-pip" cx="{x + 7}" cy="10" r="6" '
            f'style="--pip-color: {pip_colour}" />'
        )
        body.append("</g>")

    return (
        f'<svg class="ribbon-rack" data-theme="{theme}" '
        f'width="{width}" height="{height}" viewBox="0 0 120 60" role="img" '
        f'aria-label="{label or "ribbon rack"}">'
        f"<title>{label or 'ribbon rack'}</title>"
        f"{_patterns()}{''.join(body)}</svg>"
    )
