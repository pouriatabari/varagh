"""The tree of the ranks: the data of the app becomes the picture.

Nothing in the tree is written by hand: every node and every path comes
from the configuration of the reward engine and from the state of the
user. The tests below check that the picture is the data and not a
drawing that somebody liked.
"""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.insignia import render_badge, render_skill_tree
from app.models.review import Review
from app.models.rewards import Medal
from app.services import honours, rewards_config, skill_tree

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


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


def badge(key: str, state: str) -> str:
    """A badge for the nodes of the tree."""
    return render_badge(key, state=state, theme="night", size="sm")


def test_every_title_of_the_ladder_is_a_node(session: Session) -> None:
    """The tree has a node for every title the configuration knows."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    ranks = [node for node in tree.nodes if node.kind == "rank"]
    assert [node.title_key for node in ranks] == [rule.key for rule in config.titles]


def test_the_gates_of_a_rank_are_nodes_too(session: Session) -> None:
    """The gates of a rank are the paths that lead into it."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    ranks = [node for node in tree.nodes if node.kind == "rank"]
    gates = [node for node in tree.nodes if node.kind == "gate"]
    assert gates
    for rank in ranks:
        own = [node for node in gates if node.title_key == rank.title_key]
        assert own, rank.title_key
        for gate in own:
            # Every gate has a path into its rank, and no other.
            edges = [
                edge
                for edge in tree.edges
                if edge.source == gate.id and edge.target == rank.id
            ]
            assert len(edges) == 1


def test_the_spine_of_the_tree_is_the_ladder(session: Session) -> None:
    """The ranks are joined by one path each, from the page upwards."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    spine = [
        edge for edge in tree.edges if edge.source.startswith("rank:") and
        edge.target.startswith("rank:")
    ]
    assert len(spine) == len(config.titles) - 1
    for edge in spine:
        below = edge.source.split(":", 1)[1]
        above = edge.target.split(":", 1)[1]
        rules = {rule.key: rule for rule in config.titles}
        assert rules[below].degrees < rules[above].degrees


def test_the_state_of_the_user_is_told(session: Session) -> None:
    """The rank of the user and the one that waits are marked."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    states = {node.title_key: node.state for node in tree.nodes if node.kind == "rank"}
    state = honours.title_state(session, config)
    assert states[state.current] == skill_tree.CURRENT
    if state.next_title:
        assert states[state.next_title] == skill_tree.NEXT


def test_a_gate_that_is_met_is_open(session: Session) -> None:
    """A gate that is met is lit, and the path of it is gold."""
    config = rewards_config.load_config()
    counted_medal(session, 12)
    finished_muster(session, 0)
    finished_muster(session, 1)
    session.flush()
    tree = skill_tree.build(session, config, "medieval")
    gates = [node for node in tree.nodes if node.kind == "gate"]
    assert any(gate.satisfied for gate in gates)
    open_edges = [edge for edge in tree.edges if edge.state == skill_tree.OPEN]
    assert open_edges


def test_the_ranks_are_a_chain_and_the_gates_hang_under_them(
    session: Session,
) -> None:
    """The picture is a chain of ranks with the gates hanging under it."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    ranks = [node for node in tree.nodes if node.kind == "rank"]
    gates = [node for node in tree.nodes if node.kind == "gate"]
    # The ranks stand in one row, in the order of the ladder.
    assert len({node.y for node in ranks}) == 1
    assert [node.x for node in ranks] == sorted(node.x for node in ranks)
    # The gates hang under the row of the ranks.
    assert all(gate.y > rank.y for gate in gates for rank in ranks[:1])


def test_the_picture_carries_the_nodes_and_the_roads(session: Session) -> None:
    """The drawing shows the nodes and the roads of the data."""
    config = rewards_config.load_config()
    tree = skill_tree.build(session, config, "medieval")
    svg = render_skill_tree(tree, badge_for=badge)
    assert svg.count("skill-node skill-rank") == len(config.titles)
    assert "skill-path" in svg
    assert "skill-badge" in svg
    # The name of a rank in the picture is the name of the interface and
    # never the key of the configuration.
    assert ">اسکوایر<" in svg


def test_the_details_of_a_node_are_served(client: TestClient) -> None:
    """The panel of a node is served by the app."""
    response = client.get("/tree/node/rank:squire")
    assert response.status_code == 200
    assert "اسکوایر" in response.text or "squire" in response.text


def test_the_details_of_a_gate_are_served(client: TestClient) -> None:
    """A gate has a panel of its own."""
    response = client.get("/tree/node/gate:squire:musters")
    assert response.status_code == 200
    assert "سان" in response.text


def test_the_hall_shows_the_tree(client: TestClient) -> None:
    """The hall of the honours shows the tree of the ranks."""
    response = client.get("/achievements")
    assert response.status_code == 200
    assert "skill-tree" in response.text
    assert "tree-detail" in response.text
