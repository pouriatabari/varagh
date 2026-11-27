"""The tree of the ranks.

The ranks are the nodes of the tree and the gates of a rank are the
paths that lead into it. Everything comes from the configuration of the
reward engine and from the state of the user: no node and no path is
written by hand, and a rank that the data does not know is never drawn.

The shape of the picture is the shape of the reference: the ladder of the
titles is a chain of nodes that runs from left to right, and the gates of
a rank hang under it like the pendants of a chain, each on its own stem.
The chain widens where the gates of two neighbouring ranks are many, so
that no two gates ever stand on each other.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.i18n import translate
from app.insignia.catalog import title_of
from app.services import honours, rewards_config
from app.services.rewards import TitleGate, TitleState

# The place of the nodes on the canvas. The chain of the ranks runs from
# left to right; the gates hang under it.
RANK_PITCH = 132.0
GATE_PITCH = 32.0
MARGIN_LEFT = 96.0
MARGIN_RIGHT = 96.0
RANK_ROW = 150.0
GATE_ROW = 302.0
MARGIN_TOP = 92.0
MARGIN_BOTTOM = 74.0

# The states of a node and of a path.
REACHED = "reached"
CURRENT = "current"
NEXT = "next"
LOCKED = "locked"
MET = "met"
UNMET = "unmet"
OPEN = "open"
READY = "ready"


@dataclass(frozen=True)
class TreeNode:
    """One node of the tree: a rank, or one gate of a rank."""

    id: str
    kind: str
    state: str
    label: str
    detail: str
    x: float
    y: float
    title_key: str = ""
    gate_key: str = ""
    required: int = 0
    current: int = 0
    satisfied: bool = False
    degrees: int = 0


@dataclass(frozen=True)
class TreeEdge:
    """One path of the tree: from a gate, or from a rank, into a rank."""

    source: str
    target: str
    state: str


@dataclass(frozen=True)
class SkillTree:
    """The whole tree: the nodes, the paths and the size of the canvas."""

    nodes: tuple[TreeNode, ...]
    edges: tuple[TreeEdge, ...]
    width: float
    height: float
    current: str
    next_title: str | None


def _gate_label(gate: TitleGate, lexicon: str) -> str:
    """The name of a gate, in the words of the interface."""
    if gate.key.startswith("virtue:"):
        name = gate.key.split(":", 1)[1]
        return str(translate(f"honours.virtue.{name}", lexicon))
    return str(translate(f"honours.gate.{gate.key}", lexicon))


def _rank_state(rule_key: str, state: TitleState) -> str:
    """Where a rank stands for the user."""
    if rule_key == state.current:
        return CURRENT
    if rule_key == state.next_title:
        return NEXT
    if rule_key in state.reached:
        return REACHED
    return LOCKED


def build(
    session: Session, config: rewards_config.RewardsConfig, lexicon: str
) -> SkillTree:
    """Build the tree of the ranks out of the data of the app."""
    state = honours.title_state(session, config)
    titles = list(config.titles)
    nodes: list[TreeNode] = []
    edges: list[TreeEdge] = []

    # The gates of every rank, so the chain knows how much room each
    # rank asks for before the next one may come.
    gates_of: list[tuple[TitleGate, ...]] = [
        tuple(honours.title_gates(session, config, rule.key)) for rule in titles
    ]

    # The chain of the ranks: an even row, the way the ranks of a table
    # sit, and the gates hang under it in a row of their own.
    places: list[float] = [
        MARGIN_LEFT + index * RANK_PITCH for index in range(len(titles))
    ]

    gate_cursor = MARGIN_LEFT
    for index, rule in enumerate(titles):
        node_state = _rank_state(rule.key, state)
        title = title_of(rule.key)
        nodes.append(
            TreeNode(
                id=f"rank:{rule.key}",
                kind="rank",
                state=node_state,
                label=str(translate(f"honours.title.{rule.key}", lexicon)),
                detail=(title.note_fa if title is not None else ""),
                x=places[index],
                y=RANK_ROW,
                title_key=rule.key,
                degrees=rule.degrees,
            )
        )

        # The gates of the rank hang under it, each on its own stem. They
        # stand side by side in a row of their own, the way the small
        # medallions of the picture stand under the shields.
        gates = gates_of[index]
        for gate in gates:
            nodes.append(
                TreeNode(
                    id=f"gate:{rule.key}:{gate.key}",
                    kind="gate",
                    state=MET if gate.satisfied else UNMET,
                    label=_gate_label(gate, lexicon),
                    detail=str(translate(f"honours.gate.{gate.key}", lexicon)),
                    x=gate_cursor,
                    y=GATE_ROW,
                    title_key=rule.key,
                    gate_key=gate.key,
                    required=gate.required,
                    current=gate.current,
                    satisfied=gate.satisfied,
                )
            )
            gate_cursor += GATE_PITCH
            edges.append(
                TreeEdge(
                    source=f"gate:{rule.key}:{gate.key}",
                    target=f"rank:{rule.key}",
                    state=OPEN if gate.satisfied else LOCKED,
                )
            )

        # The road of the ladder: from the rank before into this one.
        if index > 0:
            below = titles[index - 1].key
            if node_state in (REACHED, CURRENT):
                edge_state = OPEN
            elif node_state == NEXT:
                edge_state = READY
            else:
                edge_state = LOCKED
            edges.append(
                TreeEdge(
                    source=f"rank:{below}",
                    target=f"rank:{rule.key}",
                    state=edge_state,
                )
            )

    width = max(
        places[-1] + MARGIN_RIGHT if places else MARGIN_LEFT + MARGIN_RIGHT,
        gate_cursor + MARGIN_RIGHT,
    )
    height = MARGIN_TOP + GATE_ROW + MARGIN_BOTTOM
    return SkillTree(
        nodes=tuple(nodes),
        edges=tuple(edges),
        width=width,
        height=height,
        current=state.current,
        next_title=state.next_title,
    )
