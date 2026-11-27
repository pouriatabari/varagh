"""The guide of the round: the steps, the scoring and the ranks.

The guide is built out of the configuration of the reward engine, so the
numbers it shows are the numbers the app works with.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.rewards import Medal
from app.services import honours, rewards_config

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def finished_muster(session: Session, index: int) -> Review:
    """A muster that was given."""
    review = Review(
        period_type="month",
        period_start=dt.date(2024, 1, 6) + dt.timedelta(days=index * 28),
        period_end=dt.date(2024, 2, 4) + dt.timedelta(days=index * 28),
        stats={},
        status="finished",
    )
    session.add(review)
    session.flush()
    return review


def counted_medal(session: Session, value: int, month: str = "1403/05") -> Medal:
    """A medal that counted."""
    medal = Medal(
        tier="gold" if value >= 4 else "bronze",
        virtue="prowess",
        kind="earned",
        month_key=month,
        value_raw=value,
        value_counted=value,
        awarded_at=NOW,
    )
    session.add(medal)
    session.flush()
    return medal


def test_the_guide_is_a_page(client: TestClient) -> None:
    """The guide is a page of the app."""
    response = client.get("/guide")
    assert response.status_code == 200
    assert "راهنمای" in response.text


def test_the_guide_shows_the_numbers_of_the_engine(client: TestClient) -> None:
    """The numbers of the guide are the numbers of the config."""
    config = rewards_config.load_config()
    response = client.get("/guide")
    body = response.text
    assert str(config.degree_size) in body
    assert str(config.counting.monthly_cap) in body
    assert str(config.endgame.realms) in body
    assert str(config.fiefs.medals_per_fief) in body
    for tier in rewards_config.TIERS:
        assert str(config.tier_value(tier)) in body


def test_the_guide_shows_every_title_of_the_ladder(client: TestClient) -> None:
    """The ladder of the titles stands on the page."""
    config = rewards_config.load_config()
    response = client.get("/guide")
    body = response.text
    for rule in config.titles:
        assert rule.key not in body  # the keys stay out of the page
    assert str(config.titles[-1].degrees) in body


def test_the_guide_says_the_steps_and_the_rules(client: TestClient) -> None:
    """The guide tells the steps of the month and the rules."""
    response = client.get("/guide")
    body = response.text
    assert "قانون" in body  # the rules of the round
    assert "تأیید" in body  # the confirmation of the muster
    assert "درجه" in body  # the degrees


def test_both_packs_know_the_guide() -> None:
    """Both lexicon packs know every word of the guide."""
    from app.i18n.fa_medieval import STRINGS as medieval
    from app.i18n.fa_plain import STRINGS as plain

    guide_keys = {key for key in plain if key.startswith("guide.")}
    assert len(guide_keys) > 30
    for key in guide_keys:
        assert key in medieval
        assert plain[key].strip()
        assert medieval[key].strip()


def test_the_title_is_given_when_every_gate_is_met(session: Session) -> None:
    """The ceremony of the title is the app's own step."""
    config = rewards_config.load_config()
    # The squire needs two degrees (twelve points of value) and two
    # musters.
    counted_medal(session, 12)
    finished_muster(session, 0)
    finished_muster(session, 1)
    session.flush()
    state = honours.title_state(session, config)
    assert state.eligible
    row = honours.promote_if_ready(session, config)
    assert row is not None
    assert row.title_key == "squire"
    # The title is never taken back, and the next one is not given
    # before its own gates are met.
    assert honours.promote_if_ready(session, config) is None
    assert honours.reached_titles(session) == ["squire"]


def test_no_title_without_the_gates(session: Session) -> None:
    """A title is not given while a gate stands closed."""
    config = rewards_config.load_config()
    counted_medal(session, 6)
    session.flush()
    assert honours.promote_if_ready(session, config) is None


def test_no_page_shows_a_raw_placeholder(client: TestClient) -> None:
    """No page shows the name of a placeholder instead of a word."""
    for path in ("/achievements", "/guide", "/insignia", "/reviews"):
        body = client.get(path).text
        assert "{count}" not in body, path
        assert "{max}" not in body, path


def test_the_rack_of_the_ribbons_speaks_the_lexicon() -> None:
    """The tooltips of the rack are in the words of the caller."""
    from app.insignia import render_ribbon_rack

    svg = render_ribbon_rack(
        {"prowess": {"bronze": 2}},
        tier_labels={"bronze": "مدال برنزی", "silver": "مدال نقره‌ای", "gold": "مدال طلایی"},
        labels={"prowess": "چابکی"},
        label="روبان‌های فضیلت",
        digits=lambda value: str(value),
    )
    assert "روبان‌های فضیلت" in svg
    assert "مدال برنزی" in svg
    # The words of the tooltips are the ones of the caller; the English
    # names live only in the data attributes of the picture.
    import re

    for title in re.findall(r"<title>([^<]*)</title>", svg):
        assert "bronze" not in title
        assert "silver" not in title
