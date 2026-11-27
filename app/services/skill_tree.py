"""The tree of the ranks.

The ranks are the nodes of the tree and the gates of a rank are the
paths that lead into it. Everything comes from the configuration of the
reward engine and from the state of the user: no node and no path is
written by hand, and a rank that the data does not know is never drawn.

The spine of the tree is the ladder of the titles, from the page at the
bottom to the last title at the top. The gates of a rank stand beside
it, on the left and on the right, and every one of them has a path into
the rank it belongs to.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.i18n import translate
from app.insignia.catalog import title_of
from app.services import honours, rewards_config
from app.services.rewards import TitleGate, TitleState

# The place of the nodes on the canvas. The spine of the tree winds a
# little, the way a road winds, and the gates of a rank fan out on both
# sides of it.
RANK_SPACING = 172.0
SPINE_SWING = 62.0
GATE_OFFSET = 152.0
GATE_FAN = 62.0
GATE_LIFT = 24.0
CANVAS_WIDTH = 1120.0
MARGIN_TOP = 120.0

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
    middle = CANVAS_WIDTH / 2

    for index, rule in enumerate(titles):
        # The first title of the ladder is at the bottom of the tree and
        # the last one at the top, the way the ladder of the hall is read.
        level = len(titles) - 1 - index
        y = MARGIN_TOP + level * RANK_SPACING
        # The spine winds: the ranks are not stacked in a straight line.
        x = middle + SPINE_SWING * math.sin(index * 0.85)
        node_state = _rank_state(rule.key, state)
        title = title_of(rule.key)
        nodes.append(
            TreeNode(
                id=f"rank:{rule.key}",
                kind="rank",
                state=node_state,
                label=str(translate(f"honours.title.{rule.key}", lexicon)),
                detail=(title.note_fa if title is not None else ""),
                x=x,
                y=y,
                title_key=rule.key,
                degrees=rule.degrees,
            )
        )

        # The gates of the rank stand beside it: the first on the left,
        # the second on the right, the third on the left again.
        gates = honours.title_gates(session, config, rule.key)
        for position, gate in enumerate(gates):
            side = -1 if position % 2 == 0 else 1
            fan = position // 2
            gate_x = x + side * (GATE_OFFSET + fan * GATE_FAN)
            gate_y = y + (GATE_LIFT if side > 0 else -GATE_LIFT)
            nodes.append(
                TreeNode(
                    id=f"gate:{rule.key}:{gate.key}",
                    kind="gate",
                    state=MET if gate.satisfied else UNMET,
                    label=_gate_label(gate, lexicon),
                    detail=str(translate(f"honours.gate.{gate.key}", lexicon)),
                    x=gate_x,
                    y=gate_y,
                    title_key=rule.key,
                    gate_key=gate.key,
                    required=gate.required,
                    current=gate.current,
                    satisfied=gate.satisfied,
                )
            )
            edges.append(
                TreeEdge(
                    source=f"gate:{rule.key}:{gate.key}",
                    target=f"rank:{rule.key}",
                    state=OPEN if gate.satisfied else LOCKED,
                )
            )

        # The path of the ladder: from the rank below into this one.
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

    height = MARGIN_TOP * 2 + max(len(titles) - 1, 0) * RANK_SPACING
    return SkillTree(
        nodes=tuple(nodes),
        edges=tuple(edges),
        width=CANVAS_WIDTH,
        height=height,
        current=state.current,
        next_title=state.next_title,
    )
