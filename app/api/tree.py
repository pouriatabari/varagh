"""The tree of the ranks.

The tree is the picture of the ladder of the titles: the ranks are the
nodes and the gates of a rank are the paths that lead into it. The
picture is drawn by the server; the details of a node come from this
route.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, base_context
from app.i18n import translate
from app.insignia import render_badge, render_skill_tree
from app.services import honours, rewards_config, skill_tree
from app.services import settings as settings_service
from app.templating import templates

router = APIRouter()


def badge_maker(lexicon: str, theme: str) -> Callable[[str, str], str]:
    """Draw the badge of a rank in a state, for the nodes of the tree."""

    def draw(key: str, state: str) -> str:
        return render_badge(
            key,
            state=state,
            theme=theme,
            size="sm",
            name=str(translate(f"honours.title.{key}", lexicon)),
            desc=str(translate(f"title_{key}", lexicon)),
        )

    return draw


def virtue_colours(theme: str) -> dict[str, str]:
    """The colour of the ribbon of every virtue, in the theme of the user."""
    from app.insignia.ribbons import load_virtues

    ribbons = load_virtues()
    if theme == "parchment":
        return {key: ribbon.color for key, ribbon in ribbons.items()}
    return {key: ribbon.color_dark for key, ribbon in ribbons.items()}


def draw_tree(session: SessionDep, tree: skill_tree.SkillTree, lexicon: str) -> str:
    """Draw the tree of the ranks for the page."""
    theme = settings_service.theme(session)
    return render_skill_tree(
        tree,
        badge_for=badge_maker(lexicon, theme),
        virtue_colours=virtue_colours(theme),
        labels={"tree": str(translate("tree.title", lexicon))},
    )


def node_context(request: Request, session: SessionDep, node_id: str) -> dict:
    """The context of the details of one node of the tree."""
    config = rewards_config.load_config()
    lexicon = settings_service.lexicon(session)
    tree = skill_tree.build(session, config, lexicon)
    node = next((item for item in tree.nodes if item.id == node_id), None)
    gates: tuple = ()
    if node is not None and node.kind == "rank":
        gates = honours.title_gates(session, config, node.title_key)
    return {
        "tree_node": node,
        "tree_gates": gates,
        "tree_badge": (
            render_badge(
                node.title_key,
                state="lit" if node.state != "locked" else "locked",
                theme=settings_service.theme(session),
                size="md",
                name=node.label,
                desc=node.detail,
            )
            if node is not None and node.kind == "rank"
            else ""
        ),
    }


def render_detail(
    request: Request, session: SessionDep, tree: skill_tree.SkillTree
) -> str:
    """The panel of the details, at the start: the rank of the user."""
    context = base_context(
        request,
        session,
        active_page="achievements",
        **node_context(request, session, f"rank:{tree.current}"),
    )
    return templates.get_template("partials/tree_node.html").render(**context)


@router.get("/tree/node/{node_id}", response_class=HTMLResponse)
async def tree_node(request: Request, node_id: str, session: SessionDep) -> HTMLResponse:
    """The details of one node of the tree."""
    context = base_context(
        request,
        session,
        active_page="achievements",
        **node_context(request, session, node_id),
    )
    return templates.TemplateResponse(request, "partials/tree_node.html", context)
