"""The reward engine — pure domain logic, table-driven."""

from __future__ import annotations

import pytest

from app.services import rewards
from app.services.rewards_config import ConfigError, load_config, merged_config

CONFIG = load_config()


def award(tier: str, domain: str | None = None, virtue: str = "prowess", month: str = "1404/01"):
    """A medal that is being awarded."""
    return rewards.MedalAward(
        tier=tier,
        virtue=virtue,
        month_key=month,
        value_raw=CONFIG.tier_value(tier),
        domain_key=domain,
    )


def record(tier: str, virtue: str = "prowess", value: int | None = None, domain: str | None = None):
    """A medal that has already been awarded."""
    if value is None:
        value = CONFIG.tier_value(tier)
    return rewards.MedalRecord(
        tier=tier, virtue=virtue, value_counted=value, domain_key=domain
    )


# --- the tiers and the degrees ---


def test_the_tiers_have_their_value() -> None:
    """Bronze counts one, silver two and gold four."""
    assert CONFIG.tier_value("bronze") == 1
    assert CONFIG.tier_value("silver") == 2
    assert CONFIG.tier_value("gold") == 4


def test_the_degrees_come_from_the_counted_value() -> None:
    """Six points of value make one degree."""
    assert rewards.degrees(0, CONFIG) == 0
    assert rewards.degrees(5, CONFIG) == 0
    assert rewards.degrees(6, CONFIG) == 1
    assert rewards.degrees(11, CONFIG) == 1
    assert rewards.degrees(12, CONFIG) == 2


def test_the_progress_to_the_next_degree_is_a_share() -> None:
    """The progress is between zero and one."""
    assert rewards.progress_to_next_degree(0, CONFIG) == 0.0
    assert rewards.progress_to_next_degree(3, CONFIG) == pytest.approx(0.5)
    assert rewards.progress_to_next_degree(6, CONFIG) == pytest.approx(0.0)


# --- the cap and the diminishing ---


def test_the_month_counts_at_most_the_cap() -> None:
    """The medals beyond the cap are worth nothing."""
    awards = [award("gold", f"domain-{index}") for index in range(5)]
    counted = rewards.count_awards(awards, CONFIG)
    assert counted.counted == [4, 4, 2, 0, 0]
    assert counted.total == 10


def test_the_second_medal_of_a_domain_counts_for_half() -> None:
    """The diminishing returns apply in the order of the ceremony."""
    awards = [
        award("silver", "one", virtue="prowess"),
        award("silver", "one", virtue="valor"),
        award("silver", "two", virtue="wisdom"),
    ]
    counted = rewards.count_awards(awards, CONFIG)
    assert counted.counted == [2, 1, 2]


def test_a_medal_without_a_domain_is_never_diminished() -> None:
    """The medal of temperance has no domain of its own."""
    awards = [
        award("bronze", None, virtue="temperance"),
        award("bronze", None, virtue="temperance"),
    ]
    counted = rewards.count_awards(awards, CONFIG)
    assert counted.counted == [1, 1]


def test_the_cap_starts_again_in_the_next_month() -> None:
    """The cap is the cap of a Jalali month, not of the year."""
    awards = [award("gold", f"d{index}", month="1404/01") for index in range(4)]
    awards += [award("gold", f"e{index}", month="1404/02") for index in range(4)]
    counted = rewards.count_awards(awards, CONFIG)
    assert counted.counted[:4] == [4, 4, 2, 0]
    assert counted.counted[4:] == [4, 4, 2, 0]


@pytest.mark.parametrize(
    ("month", "next_month"),
    [
        ("1403/12", "1404/01"),
        ("1404/01", "1404/02"),
        ("1404/06", "1404/07"),
        ("1404/11", "1404/12"),
        ("1403/09", "1403/10"),
    ],
)
def test_the_cap_is_kept_across_the_months(month: str, next_month: str) -> None:
    """The cap of a month does not touch the cap of the next one."""
    awards = [award("gold", f"a{index}", month=month) for index in range(4)]
    awards += [award("gold", f"b{index}", month=next_month) for index in range(4)]
    counted = rewards.count_awards(awards, CONFIG)
    assert sum(counted.counted[:4]) == CONFIG.counting.monthly_cap
    assert sum(counted.counted[4:]) == CONFIG.counting.monthly_cap


def test_the_leap_year_does_not_change_the_cap() -> None:
    """The months of a leap year count like the months of any other year."""
    awards = [award("gold", f"a{index}", month="1403/12") for index in range(4)]
    counted = rewards.count_awards(awards, CONFIG)
    assert sum(counted.counted) == CONFIG.counting.monthly_cap


# --- the overtime ---


def test_the_overtime_never_gives_value() -> None:
    """A medal that is backed by overtime alone is worth nothing.

    The engine never awards a medal for the overtime: the value of the
    overtime is zero, so it can never reach a medal.
    """
    overtime_value = 0
    counted = rewards.count_awards(
        [
            rewards.MedalAward(
                tier="gold",
                virtue="valor",
                month_key="1404/01",
                value_raw=overtime_value,
            )
        ],
        CONFIG,
    )
    assert counted.counted == [0]


# --- the titles ---


def test_the_title_needs_its_gates() -> None:
    """The gates block the promotion even when the degrees are there."""
    medals = [record("gold", virtue="prowess") for _ in range(20)]
    state = rewards.title_state(
        medals=medals,
        musters=0,
        reached_titles=(),
        fiefs=0,
        config=CONFIG,
    )
    assert state.next_title == "squire"
    assert not state.eligible
    assert any(gate.key == "musters" and not gate.satisfied for gate in state.next_gates)


def test_the_virtues_are_the_ones_of_the_counted_medals() -> None:
    """A virtue with a medal that counted for nothing is no virtue."""
    medals = [
        record("gold", virtue="prowess"),
        record("gold", virtue="valor", value=0),
    ]
    assert rewards.virtues_of(medals) == ("prowess",)


def test_the_silver_and_gold_counts_only_hold_the_counted_medals() -> None:
    """A medal that counted for nothing is not a silver medal."""
    medals = [record("silver", value=2), record("silver", value=0)]
    counts = rewards.tier_counts(medals)
    assert counts["silver"] == 1


def test_a_reached_title_is_never_lost() -> None:
    """No demotion, ever."""
    medals = [record("gold", virtue="prowess")]
    state = rewards.title_state(
        medals=medals,
        musters=5,
        reached_titles=("knight",),
        fiefs=0,
        config=CONFIG,
    )
    assert state.current == "knight"


def test_the_progress_to_the_next_title_is_written_down() -> None:
    """The checklist of the next title is given with the numbers."""
    state = rewards.title_state(
        medals=[record("silver", virtue="prowess")],
        musters=1,
        reached_titles=(),
        fiefs=0,
        config=CONFIG,
    )
    gates = {gate.key: gate for gate in state.next_gates}
    assert gates["degrees"].required == 2
    assert gates["degrees"].current == 0
    assert gates["musters"].required == 2
    assert gates["musters"].current == 1


# --- the acceptance of the milestone ---


def test_the_king_is_not_reachable_before_the_thirty_ninth_month() -> None:
    """At the cap of the month the king needs thirty-nine months."""
    months = 38
    value = months * CONFIG.counting.monthly_cap
    assert value < 65 * CONFIG.degree_size

    months = 39
    value = months * CONFIG.counting.monthly_cap
    assert value >= 65 * CONFIG.degree_size


def test_the_king_needs_the_gold_and_the_virtues_and_the_fiefs() -> None:
    """The degrees alone do not make a king."""
    medals = [record("gold", virtue="prowess") for _ in range(20)]
    state = rewards.title_state(
        medals=medals,
        musters=20,
        reached_titles=("squire",),
        fiefs=0,
        config=CONFIG,
    )
    # Many degrees, but only one virtue and no silver: the knight waits.
    assert state.next_title == "knight"
    assert not state.eligible
    gates = {gate.key: gate for gate in state.next_gates}
    assert not gates["silver"].satisfied
    assert not gates["virtues"].satisfied


def test_a_task_cannot_back_two_medals() -> None:
    """The evidence of a medal is a task, and a task is used once.

    The rule lives in the database: the task id is unique in the table of
    the evidence. The test checks the model itself.
    """
    from app.models.rewards import MedalEvidence

    constraints = {
        constraint.name for constraint in MedalEvidence.__table__.constraints
    }
    assert "uq_medal_evidence_task" in constraints
    columns = {column.name for column in MedalEvidence.__table__.columns}
    assert "task_id" in columns


# --- the tier of a proposal ---


@pytest.mark.parametrize(
    ("tasks", "impact", "concrete", "expected"),
    [
        (0, False, False, "bronze"),
        (1, False, False, "bronze"),
        (2, True, False, "silver"),
        (2, False, False, "bronze"),
        (3, True, True, "gold"),
        (3, True, False, "silver"),
    ],
)
def test_the_tier_is_clamped_to_the_evidence(
    tasks: int, impact: bool, concrete: bool, expected: str
) -> None:
    """A proposal may not claim more than its evidence proves."""
    assert (
        rewards.clamped_tier(
            "gold",
            task_count=tasks,
            has_impact_note=impact,
            concrete=concrete,
            config=CONFIG,
        )
        == expected
    )


def test_the_fiefs_come_from_the_medals_of_a_domain() -> None:
    """A domain with enough counted medals is a fief."""
    medals = [
        record("bronze", domain="one"),
        record("bronze", domain="one"),
        record("bronze", domain="one"),
        record("bronze", domain="two"),
    ]
    assert rewards.fief_count(medals, CONFIG) == 1


# --- the configuration ---


def test_the_configuration_file_is_valid() -> None:
    """The numbers of the file are read and validated."""
    config = load_config()
    assert config.degree_size == 6
    assert config.counting.monthly_cap == 10
    assert len(config.titles) == 11


def test_a_wrong_number_is_refused(tmp_path) -> None:
    """A file that does not make sense is reported, not used."""
    bad = tmp_path / "rewards.yaml"
    bad.write_text("medal_tiers:\n  bronze: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(bad)


def test_the_user_may_change_the_numbers() -> None:
    """The settings of the user are merged with the file."""
    config = merged_config({"counting": {"monthly_cap": 4}})
    assert config.counting.monthly_cap == 4
    assert config.degree_size == CONFIG.degree_size


def test_a_wrong_setting_is_refused() -> None:
    """A setting that does not make sense is refused."""
    with pytest.raises(ConfigError):
        merged_config({"counting": {"monthly_cap": -3}})
