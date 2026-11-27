"""The reward engine — pure domain logic.

Nothing in this module touches the database: every function takes the
facts it needs and returns the result. The rules themselves live in
``config/rewards.yaml`` and are read through
:mod:`app.services.rewards_config`.

The vocabulary of the medals is neutral English (``prowess``, ``silver``);
the words of the interface are the business of the i18n packs.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from app.services.rewards_config import RewardsConfig, TitleRule

TIERS = ("bronze", "silver", "gold")
#: The order the tiers are counted in: the lowest first.
TIER_ORDER = {name: index for index, name in enumerate(TIERS)}


@dataclass(frozen=True)
class MedalAward:
    """A medal that is being awarded, before the value is counted."""

    tier: str
    virtue: str
    month_key: str
    value_raw: int
    domain_key: str | None = None
    #: ``quest``, ``victory`` and ``temperance`` are given by the app.
    kind: str = "earned"


@dataclass(frozen=True)
class MedalRecord:
    """A medal that has already been awarded."""

    tier: str
    virtue: str
    value_counted: int
    month_key: str = ""
    domain_key: str | None = None


@dataclass(frozen=True)
class TitleGate:
    """One gate of a title, and how far the user is from it."""

    key: str
    label: str
    required: int
    current: int
    satisfied: bool

    @property
    def remaining(self) -> int:
        """How much is still missing."""
        return max(0, self.required - self.current)


@dataclass(frozen=True)
class TitleState:
    """Where the user stands with the titles."""

    current: str
    reached: tuple[str, ...]
    next_title: str | None
    next_gates: tuple[TitleGate, ...]
    eligible: bool
    degrees: int
    total_value: int
    progress_to_next_degree: float
    virtues: tuple[str, ...]
    silver: int
    gold: int
    musters: int
    fiefs: int


@dataclass
class CountedAwards:
    """The medals of one month, with the value each one counts for."""

    awards: list[MedalAward] = field(default_factory=list)
    counted: list[int] = field(default_factory=list)

    @property
    def total(self) -> int:
        """The value the month counts for."""
        return sum(self.counted)


def count_awards(
    awards: Sequence[MedalAward], config: RewardsConfig
) -> CountedAwards:
    """Count the value of the medals of a month.

    The order of the awards is the order of the ceremony. The second medal
    of a domain in the same month counts for half, and the month counts
    for no more than the cap: the medals beyond the cap are worth nothing.
    """
    counted: list[int] = []
    used = 0
    month = ""
    seen_in_domain: dict[str, int] = {}
    for award in awards:
        if award.month_key != month:
            # The cap and the diminishing belong to a Jalali month; a new
            # month starts with a full cap and with no medal of the last.
            month = award.month_key
            used = 0
            seen_in_domain = {}
        value = award.value_raw
        if award.domain_key is not None:
            seen = seen_in_domain.get(award.domain_key, 0)
            seen_in_domain[award.domain_key] = seen + 1
            if seen >= 1:
                value = _diminish(value, config)
        room = max(0, config.counting.monthly_cap - used)
        counted_value = min(value, room)
        used += counted_value
        counted.append(counted_value)
    return CountedAwards(awards=list(awards), counted=counted)


def _diminish(value: int, config: RewardsConfig) -> int:
    """The value of a medal that is not the first of its domain."""
    factor = config.counting.diminishing_factor
    return int(value * factor)


def total_value(medals: Iterable[MedalRecord]) -> int:
    """The value of the counted medals."""
    return sum(medal.value_counted for medal in medals)


def degrees(value: int, config: RewardsConfig) -> int:
    """The degrees the counted value makes."""
    return value // config.degree_size


def progress_to_next_degree(value: int, config: RewardsConfig) -> float:
    """The share of the way to the next degree, between 0 and 1."""
    if config.degree_size <= 0:
        return 0.0
    return (value % config.degree_size) / config.degree_size


def counted_medals(medals: Iterable[MedalRecord]) -> list[MedalRecord]:
    """The medals that counted for something."""
    return [medal for medal in medals if medal.value_counted > 0]


def virtues_of(medals: Iterable[MedalRecord]) -> tuple[str, ...]:
    """The virtues that have at least one counted medal."""
    found: list[str] = []
    for medal in counted_medals(medals):
        if medal.virtue not in found:
            found.append(medal.virtue)
    return tuple(sorted(found))


def tier_counts(medals: Iterable[MedalRecord]) -> dict[str, int]:
    """The number of the counted medals of every tier."""
    counts = {name: 0 for name in TIERS}
    for medal in counted_medals(medals):
        if medal.tier in counts:
            counts[medal.tier] += 1
    return counts


def fief_count(medals: Iterable[MedalRecord], config: RewardsConfig) -> int:
    """The number of the domains that became a fief.

    A domain with enough counted medals is a fief. The fiefs of the
    titles are the realms that have been claimed, so the caller gives the
    claimed realms when the titles are asked for.
    """
    per_domain: dict[str, int] = {}
    for medal in counted_medals(medals):
        if medal.domain_key is None:
            continue
        per_domain[medal.domain_key] = per_domain.get(medal.domain_key, 0) + 1
    return sum(
        1 for count in per_domain.values() if count >= config.fiefs.medals_per_fief
    )


def _gates_for(
    rule: TitleRule, *, degrees_held: int, musters: int, counts: dict[str, int],
    virtues: tuple[str, ...], fiefs: int, vigil_done: bool,
) -> list[TitleGate]:
    """The gates of one title, each with the distance that is left."""
    gates: list[TitleGate] = []
    gates.append(
        TitleGate(
            key="degrees",
            label="degrees",
            required=rule.degrees,
            current=degrees_held,
            satisfied=degrees_held >= rule.degrees,
        )
    )
    if rule.musters is not None:
        gates.append(
            TitleGate(
                key="musters",
                label="musters",
                required=rule.musters,
                current=musters,
                satisfied=musters >= rule.musters,
            )
        )
    if rule.silver is not None:
        gates.append(
            TitleGate(
                key="silver",
                label="silver",
                required=rule.silver,
                current=counts["silver"],
                satisfied=counts["silver"] >= rule.silver,
            )
        )
    if rule.gold is not None:
        gates.append(
            TitleGate(
                key="gold",
                label="gold",
                required=rule.gold,
                current=counts["gold"],
                satisfied=counts["gold"] >= rule.gold,
            )
        )
    if rule.virtues is not None:
        gates.append(
            TitleGate(
                key="virtues",
                label="virtues",
                required=rule.virtues,
                current=len(virtues),
                satisfied=len(virtues) >= rule.virtues,
            )
        )
    for name in rule.virtues_must_include:
        gates.append(
            TitleGate(
                key=f"virtue:{name}",
                label=name,
                required=1,
                current=1 if name in virtues else 0,
                satisfied=name in virtues,
            )
        )
    if rule.fiefs is not None:
        gates.append(
            TitleGate(
                key="fiefs",
                label="fiefs",
                required=rule.fiefs,
                current=fiefs,
                satisfied=fiefs >= rule.fiefs,
            )
        )
    if rule.vigil:
        gates.append(
            TitleGate(
                key="vigil",
                label="vigil",
                required=1,
                current=1 if vigil_done else 0,
                satisfied=vigil_done,
            )
        )
    return gates


def title_state(
    *,
    medals: Sequence[MedalRecord],
    musters: int,
    reached_titles: Sequence[str] = (),
    fiefs: int = 0,
    config: RewardsConfig,
) -> TitleState:
    """Where the user stands with the titles.

    ``reached_titles`` are the titles that have been confirmed: a title
    that is only eligible is not reached yet, and no title is ever lost.
    """
    value = total_value(medals)
    degrees_held = degrees(value, config)
    counts = tier_counts(medals)
    virtues = virtues_of(medals)
    reached = tuple(reached_titles)
    # The first title of the ladder is the one everybody starts with.
    base = config.titles[0].key if config.titles else "page"
    reached_set = set(reached) | {base}

    current = base
    for rule in config.titles:
        if rule.key in reached_set:
            current = rule.key

    next_rule = None
    for rule in config.titles:
        if rule.key in reached_set:
            continue
        next_rule = rule
        break

    gates: list[TitleGate] = []
    eligible = False
    if next_rule is not None:
        gates = _gates_for(
            next_rule,
            degrees_held=degrees_held,
            musters=musters,
            counts=counts,
            virtues=virtues,
            fiefs=fiefs,
            vigil_done=next_rule.key in reached_set or _vigil_answered(
                reached_titles, next_rule.key
            ),
        )
        # The vigil is the ceremony itself: the user becomes eligible when
        # every other gate is met, and the vigil comes with the promotion.
        without_vigil = [gate for gate in gates if gate.key != "vigil"]
        eligible = all(gate.satisfied for gate in without_vigil)

    return TitleState(
        current=current,
        reached=reached,
        next_title=next_rule.key if next_rule else None,
        next_gates=tuple(gates),
        eligible=eligible,
        degrees=degrees_held,
        total_value=value,
        progress_to_next_degree=progress_to_next_degree(value, config),
        virtues=virtues,
        silver=counts["silver"],
        gold=counts["gold"],
        musters=musters,
        fiefs=fiefs,
    )


def _vigil_answered(reached_titles: Sequence[str], title_key: str) -> bool:
    """Whether the vigil of a title has been answered.

    The vigil is stored with the title itself, so a title that was reached
    has already answered it.
    """
    return title_key in set(reached_titles)


def highest_reached_title(reached_titles: Sequence[str], config: RewardsConfig) -> str:
    """The title of the list that is the highest of the reached ones."""
    keys = [rule.key for rule in config.titles]
    best = keys[0] if keys else "page"
    for key in reached_titles:
        if key in keys and keys.index(key) > keys.index(best):
            best = key
    return best


def clamped_tier(
    tier: str,
    *,
    task_count: int,
    has_impact_note: bool,
    concrete: bool,
    config: RewardsConfig,
) -> str:
    """The tier the evidence of a medal really earns.

    A tier may be lowered freely; it may not be raised above what the
    evidence proves.
    """
    order = [name for name in TIERS if name in config.medal_tiers]
    for candidate in reversed(order):
        rule = config.rule(candidate)
        if task_count < rule.tasks:
            continue
        if rule.impact_note and not has_impact_note:
            continue
        if rule.concrete and not concrete:
            continue
        return candidate
    return order[0] if order else "bronze"


def tier_order(tier: str) -> int:
    """The rank of a tier: the lowest is 0."""
    return TIER_ORDER.get(tier, 0)
