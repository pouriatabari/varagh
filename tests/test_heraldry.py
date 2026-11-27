"""The arms, the chart and the table: the pictures of the hall.

The heraldry is deterministic, so it can be tested against a snapshot:
the same title, the same domains and the same virtues must always give
the same SVG. When a picture changes on purpose, the snapshot file is
rewritten and the change is read in the diff.
"""

from __future__ import annotations

from pathlib import Path

from app.services import court, heraldry

SNAPSHOTS = Path(__file__).parent / "snapshots"


def check_snapshot(name: str, actual: str) -> None:
    """Compare a picture with the one that was stored.

    A missing snapshot is a failure, not a silent pass: the file is
    written on the machine of the developer and committed with the code.
    """
    path = SNAPSHOTS / name
    assert path.exists(), (
        f"the snapshot {name} is missing; write it on the host and commit it"
    )
    expected = path.read_text(encoding="utf-8")
    assert actual == expected, f"the picture {name} has changed"


# --- the heraldry ---


def test_the_arms_are_always_the_same() -> None:
    """The same inputs give the same arms, every time."""
    first = heraldry.heraldry_svg(
        title_key="knight", domains=["شبکه", "پژوهش"], virtues=["prowess", "wisdom"]
    )
    second = heraldry.heraldry_svg(
        title_key="knight", domains=["شبکه", "پژوهش"], virtues=["prowess", "wisdom"]
    )
    assert first == second


def test_the_colour_of_a_domain_is_stable() -> None:
    """A domain always keeps the same colour."""
    assert heraldry.domain_colour("شبکه") == heraldry.domain_colour("شبکه")
    assert heraldry.domain_colour("شبکه") in heraldry.FIELD_COLOURS


def test_the_crown_follows_the_title() -> None:
    """The higher the title, the richer the crown."""
    page = heraldry.heraldry_svg(title_key="page")
    knight = heraldry.heraldry_svg(title_key="knight")
    king = heraldry.heraldry_svg(title_key="king")
    assert len(page) < len(knight) < len(king)


def test_the_charges_follow_the_virtues() -> None:
    """The charges of the arms are the virtues of the medals."""
    arms = heraldry.heraldry_svg(title_key="king", virtues=["wisdom", "valor"])
    assert "wisdom" not in arms
    assert len(arms) > len(heraldry.heraldry_svg(title_key="king"))


def test_the_arms_of_a_knight_are_stable() -> None:
    """The picture of the arms does not move without a reason."""
    arms = heraldry.heraldry_svg(
        title_key="knight",
        domains=["شبکه"],
        virtues=["prowess", "loyalty"],
    )
    check_snapshot("heraldry_knight.svg", arms)


# --- the round table ---


def seats() -> list[court.Seat]:
    """A table of six seats."""
    return [
        court.Seat(virtue="prowess", count=4, share=1.0),
        court.Seat(virtue="valor", count=2, share=0.5),
        court.Seat(virtue="wisdom", count=0, share=0.0),
        court.Seat(virtue="loyalty", count=1, share=0.25),
        court.Seat(virtue="largesse", count=0, share=0.0),
        court.Seat(virtue="temperance", count=0, share=0.0),
    ]


def test_the_table_lights_the_seats_with_medals() -> None:
    """A seat with a medal is lit, an empty seat is locked."""
    table = court.round_table_svg(seats())
    assert table.count("lit") == 3
    assert table.count("locked") == 3


def test_the_table_is_stable() -> None:
    """The picture of the table does not move without a reason."""
    check_snapshot("round_table.svg", court.round_table_svg(seats()))
