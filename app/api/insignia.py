"""The case of the insignia.

The case is the shelf of every badge of the ladder: the ones that were
reached, the one that waits and the ones that are still closed. Every
badge is drawn by the code from the catalogue; the words of the
interface come from the lexicon pack of the user.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, base_context
from app.i18n import translate
from app.insignia import ordered_titles, render_badge
from app.services import honours, rewards_config
from app.services import settings as settings_service

router = APIRouter()


def _badge_name(key: str, lexicon: str) -> str:
    """The name of a title in the lexicon of the user."""
    return str(translate(f"title_{key}", lexicon))


def _vigil_text(vigil: dict) -> str:
    """The words of the vigil of a title, when they were written down."""
    for field in ("text", "answer", "note", "body"):
        value = vigil.get(field)
        if value:
            return str(value)
    return ""


@router.get("/insignia", response_class=HTMLResponse)
async def insignia_case(request: Request, session: SessionDep) -> HTMLResponse:
    """The shelf of every badge of the ladder."""
    config = rewards_config.load_config()
    lexicon = settings_service.lexicon(session)
    theme = settings_service.theme(session)
    state = honours.title_state(session, config)

    reached = set(honours.reached_titles(session))
    if config.titles:
        reached.add(config.titles[0].key)
    next_title = state.next_title
    if next_title is None and state.current == config.titles[-1].key:
        # The last title of the ladder waits for the realms of the map.
        claimed = len(honours.claimed_realms(session))
        if claimed >= config.endgame.realms:
            next_title = config.endgame.title

    slots = []
    for title in ordered_titles():
        if title.key in reached:
            badge_state = "lit"
        elif title.key == next_title:
            badge_state = "next"
        else:
            badge_state = "locked"
        name = _badge_name(title.key, lexicon)
        reached_at = honours.title_reached_at(session, title.key)
        vigil = honours.title_vigil(session, title.key)
        slots.append(
            {
                "key": title.key,
                "name": name,
                "note": title.note_fa,
                "state": badge_state,
                "state_label": {
                    "lit": "insignia.earned",
                    "next": "insignia.next",
                    "locked": "insignia.locked",
                }[badge_state],
                "badge": render_badge(
                    title.key,
                    state="lit" if badge_state == "lit" else badge_state,
                    theme=theme,
                    size="md",
                    name=name,
                    desc=title.note_fa,
                ),
                "large_badge": render_badge(
                    title.key,
                    state="lit" if badge_state == "lit" else badge_state,
                    theme=theme,
                    size="lg",
                    name=name,
                    desc=title.note_fa,
                ),
                "reached_on": reached_at,
                "vigil": _vigil_text(vigil),
                "level": title.level,
            }
        )

    context = base_context(
        request,
        session,
        active_page="insignia",
        insignia_slots=slots,
    )
    from app.templating import templates

    return templates.TemplateResponse(request, "insignia.html", context)
