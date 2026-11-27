"""The insignia of the ranks: the badges, the studs and the ribbons.

The badges are drawn by the code, so the numbers of the picture must
agree with the numbers of the catalogue and with the numbers that are
written down in the decisions of the project.
"""

from __future__ import annotations

import re
from pathlib import Path

from app.insignia import (
    load_titles,
    ordered_titles,
    render_badge,
    render_ribbon_rack,
)
from app.insignia.badge import describe_emblem
from app.insignia.ribbons import TIERS, highest_tier

DOCS = Path(__file__).resolve().parents[1] / "docs" / "DECISIONS.md"

# The titles of the ladder, from the lowest to the highest.
LADDER = (
    "page",
    "squire",
    "knight",
    "banneret",
    "baron",
    "viscount",
    "earl",
    "marquess",
    "duke",
    "prince",
    "king",
    "bretwalda",
)


def count(svg: str, marker: str) -> int:
    """How many times a marker stands in a picture."""
    return svg.count(marker)


def pearls(svg: str) -> int:
    return count(svg, 'class="insignia-pearl"')


def leaves(svg: str) -> int:
    return count(svg, 'class="insignia-leaf"')


def arches(svg: str) -> int:
    return count(svg, 'class="insignia-arch"')


def rays(svg: str) -> int:
    return count(svg, 'class="insignia-ray"')


# --- the catalogue ---


def test_every_title_of_the_ladder_has_a_badge() -> None:
    """The ladder of the ranks has twelve badges."""
    titles = load_titles()
    assert set(titles) == set(LADDER)
    assert [title.key for title in ordered_titles()] == list(LADDER)


def test_every_title_has_a_note() -> None:
    """Every badge tells the history of its title."""
    for title in ordered_titles():
        assert title.note_fa.strip(), f"the title {title.key} has no note"


# --- the drawing ---


def test_every_title_is_drawn() -> None:
    """Every title of the ladder can be drawn."""
    for key in LADDER:
        svg = render_badge(key, 0, 0, "lit", "night", "md")
        assert svg.startswith("<svg")
        assert f'data-title="{key}"' in svg


def test_the_baron_shows_four_pearls_and_the_viscount_nine() -> None:
    """The pearls of the two first barons are counted."""
    assert pearls(render_badge("baron")) == 4
    assert pearls(render_badge("viscount")) == 9


def test_the_earl_has_five_leaves_and_five_raised_pearls() -> None:
    """The earl stands on his leaves, and the pearls sit on their spikes."""
    svg = render_badge("earl")
    assert leaves(svg) == 5
    assert pearls(svg) == 5
    assert 'class="insignia-spike"' in svg


def test_the_marquess_alternates_leaves_and_pearls() -> None:
    """The leaves and the pearls of the marquess take turns."""
    svg = render_badge("marquess")
    assert leaves(svg) == 4
    assert pearls(svg) == 4
    # The elements take turns along the rim of the coronet.
    placed = re.findall(
        r'class="insignia-(leaf|pearl)" transform="translate\(([\d.]+)', svg
    )
    order = [kind for kind, _ in sorted(placed, key=lambda item: float(item[1]))]
    assert order == ["leaf", "pearl"] * 4


def test_the_duke_has_leaves_and_no_pearl() -> None:
    """The duke has no pearl at all."""
    svg = render_badge("duke")
    assert leaves(svg) == 5
    assert pearls(svg) == 0


def test_the_prince_has_one_arch_and_the_king_two() -> None:
    """The arch of the prince and the two arches of the king."""
    assert arches(render_badge("prince")) == 1
    assert arches(render_badge("king")) == 2
    assert "insignia-orb" in render_badge("king")
    assert "insignia-cross" in render_badge("king")


def test_the_bretwalda_has_rays_and_an_island() -> None:
    """The last title has the rays and the island."""
    svg = render_badge("bretwalda")
    assert rays(svg) == 12
    assert 'class="insignia-island"' in svg


def test_the_squire_has_two_spurs_and_the_knight_a_sword() -> None:
    """The charges of the two first ranks."""
    assert count(render_badge("squire"), 'class="insignia-spur"') == 2
    assert 'class="insignia-sword"' in render_badge("knight")
    assert 'class="insignia-banner"' in render_badge("banneret")


def test_the_page_has_no_charge() -> None:
    """The shield of the page is plain."""
    svg = render_badge("page")
    assert "insignia-charge" not in svg


# --- the decisions of the project ---


def _decisions() -> str:
    """The decisions of the project."""
    return DOCS.read_text(encoding="utf-8")


def test_the_visible_counts_are_written_down() -> None:
    """The counts that are drawn are written down in the decisions."""
    text = _decisions()
    assert re.search(r"baron draws (\d+) pearls", text)
    assert re.search(r"viscount (\d+) of its", text)
    assert re.search(r"earl (\d+) leaves and (\d+) pearls", text)
    assert re.search(r"marquess (\d+) leaves and (\d+) pearls", text)
    assert re.search(r"duke (\d+) leaves", text)


def test_the_drawing_agrees_with_the_decisions() -> None:
    """The picture and the decisions say the same thing."""
    text = _decisions()
    baron = int(re.search(r"baron draws (\d+) pearls", text).group(1))
    viscount = int(re.search(r"viscount (\d+) of its", text).group(1))
    earl_leaves, earl_pearls = re.search(
        r"earl (\d+) leaves and (\d+) pearls", text
    ).groups()
    marquess_leaves, marquess_pearls = re.search(
        r"marquess (\d+) leaves and (\d+) pearls", text
    ).groups()
    duke_leaves = int(re.search(r"duke (\d+) leaves", text).group(1))

    assert pearls(render_badge("baron")) == baron
    assert pearls(render_badge("viscount")) == viscount
    assert leaves(render_badge("earl")) == int(earl_leaves)
    assert pearls(render_badge("earl")) == int(earl_pearls)
    assert leaves(render_badge("marquess")) == int(marquess_leaves)
    assert pearls(render_badge("marquess")) == int(marquess_pearls)
    assert leaves(render_badge("duke")) == duke_leaves


# --- the studs of the degrees ---


def test_the_studs_show_the_degrees_that_are_done() -> None:
    """The filled studs are the degrees that are done."""
    svg = render_badge("knight", 3, 5, "lit", "night", "md")
    assert count(svg, 'class="insignia-stud filled"') == 3
    assert count(svg, 'class="insignia-stud hollow"') == 2


def test_the_studs_stop_at_twelve_and_the_number_is_written() -> None:
    """More than twelve studs do not fit: the number stands beside them."""
    svg = render_badge("king", 14, 18, "lit", "night", "md")
    assert count(svg, 'class="insignia-stud ') == 12
    assert "14/18" in svg
    assert "insignia-stud-count" in svg


def test_a_title_without_a_title_above_it_has_no_stud() -> None:
    """The king has no title above it: the years of the reign stand in
    the place of the studs."""
    svg = render_badge("king", 0, 0, "lit", "night", "md")
    assert count(svg, 'class="insignia-stud ') == 0


# --- the states ---


def test_every_state_has_a_cue_of_its_own() -> None:
    """The state of a badge is never told by the colour alone."""
    lit = render_badge("knight", 1, 4, "lit", "night", "md")
    locked = render_badge("knight", 1, 4, "locked", "night", "md")
    following = render_badge("knight", 1, 4, "next", "night", "md")
    assert "insignia-lock" in locked
    assert "insignia-lock" not in lit
    assert "insignia-progress" in following
    assert "insignia-progress" not in lit
    assert locked != lit != following


def test_every_badge_has_a_name_and_a_description() -> None:
    """Every badge carries a title and a description."""
    svg = render_badge("duke", 0, 0, "lit", "night", "md", name="دوک")
    assert "<title>دوک</title>" in svg
    assert "<desc>" in svg
    assert describe_emblem(load_titles()["duke"].emblem)


def test_the_badge_is_the_same_every_time() -> None:
    """The picture of a badge does not move without a reason."""
    first = render_badge("earl", 2, 5, "lit", "night", "md")
    second = render_badge("earl", 2, 5, "lit", "night", "md")
    assert first == second


def test_both_themes_are_drawn() -> None:
    """The badge of both themes is drawn."""
    night = render_badge("knight", 1, 3, "lit", "night", "md")
    parchment = render_badge("knight", 1, 3, "lit", "parchment", "md")
    assert 'data-theme="night"' in night
    assert 'data-theme="parchment"' in parchment


def test_the_three_sizes_are_drawn() -> None:
    """A badge comes in three sizes."""
    sizes = {
        size: render_badge("knight", 0, 0, "lit", "night", size)
        for size in ("sm", "md", "lg")
    }
    assert 'width="40"' in sizes["sm"]
    assert 'width="74"' in sizes["md"]
    assert 'width="124"' in sizes["lg"]


# --- the rack of the ribbons ---


def test_the_rack_has_six_ribbons() -> None:
    """The rack holds one ribbon for every virtue."""
    svg = render_ribbon_rack({})
    assert count(svg, 'class="ribbon ') == 6


def test_every_ribbon_has_a_pattern_of_its_own() -> None:
    """No two ribbons are told by the same pattern."""
    patterns = re.findall(r'id="ribbon-([a-z]+)"', render_ribbon_rack({}))
    assert len(patterns) == len(set(patterns))
    assert len(patterns) >= 5


def test_the_pip_of_a_ribbon_is_the_best_tier() -> None:
    """The pip of a ribbon shows the best tier of its virtue."""
    svg = render_ribbon_rack({"prowess": {"bronze": 1, "silver": 2, "gold": 0}})
    assert 'data-virtue="prowess"' in svg
    assert 'data-tier="silver"' in svg
    assert highest_tier({"bronze": 1, "silver": 2, "gold": 0}) == "silver"
    assert highest_tier({}) is None
    assert highest_tier({"bronze": 0, "silver": 0, "gold": 3}) == "gold"


def test_a_virtue_without_a_medal_keeps_its_ribbon_locked() -> None:
    """The ribbon of a virtue with no medal is locked."""
    svg = render_ribbon_rack({"wisdom": {"bronze": 0}})
    assert 'data-virtue="wisdom"' in svg
    assert re.search(r'data-virtue="wisdom" data-tier=""', svg)
    assert "ribbon locked" in svg


def test_the_ribbons_are_in_the_order_of_the_virtues() -> None:
    """The ribbons stand in the order of the virtues."""
    svg = render_ribbon_rack({})
    order = re.findall(r'data-virtue="([a-z]+)"', svg)
    assert order == ["prowess", "valor", "wisdom", "loyalty", "largesse", "temperance"]
    assert TIERS == ("bronze", "silver", "gold")


# --- the case of the insignia ---


def test_the_case_shows_every_badge(client) -> None:
    """The case of the insignia lists the twelve badges."""
    response = client.get("/insignia")
    assert response.status_code == 200
    body = response.text
    for key in LADDER:
        assert f'data-title="{key}"' in body
    assert "insignia.footnote" not in body  # the words are translated
    assert body.count('class="insignia-slot ') == len(LADDER)


def test_the_case_shows_the_state_of_every_badge(client, session) -> None:
    """The badges of the ladder are told apart by their state."""
    response = client.get("/insignia")
    body = response.text
    # The page is the first title of the ladder and it is earned.
    assert 'class="insignia-slot lit"' in body
    assert 'class="insignia-slot locked"' in body


def test_the_plain_lexicon_names_the_titles_by_their_level() -> None:
    """In the plain pack the titles are the levels of the ladder."""
    from app.i18n.fa_medieval import STRINGS as medieval
    from app.i18n.fa_plain import STRINGS as plain

    assert plain["title_king"].startswith("سطح")
    assert plain["title_page"].startswith("سطح")
    assert medieval["title_king"] == "پادشاه"
    assert not medieval["title_king"].startswith("سطح")
    # Both packs know every title of the ladder.
    for key in LADDER:
        assert f"title_{key}" in plain
        assert f"title_{key}" in medieval
