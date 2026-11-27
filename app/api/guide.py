"""The guide of the round: the steps, the scoring and the ranks.

The page is built out of the configuration of the reward engine, so the
numbers it shows are the numbers the app really works with: when a
number is changed in the settings, the guide changes with it.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.api.deps import SessionDep, base_context
from app.i18n import translate
from app.services import rewards_config
from app.services import settings as settings_service
from app.templating import templates

router = APIRouter()


def _tiers(config: rewards_config.RewardsConfig, lexicon: str) -> list[dict]:
    """The three tiers of a medal and the evidence each of them needs."""
    rows = []
    for tier in rewards_config.TIERS:
        rule = config.evidence[tier]
        rows.append(
            {
                "key": tier,
                "name": str(translate(f"medals.tier.{tier}", lexicon)),
                "value": config.tier_value(tier),
                "tasks": rule.tasks,
                "impact": rule.impact_note,
                "concrete": rule.concrete,
            }
        )
    return rows


def _titles(config: rewards_config.RewardsConfig, lexicon: str) -> list[dict]:
    """The ladder of the titles and the gates of every one of them."""
    rows = []
    for rule in config.titles:
        # The degrees stand in a column of their own; the gates are the
        # other doors of the title.
        gates: list[dict] = []
        if rule.musters is not None:
            gates.append(
                {
                    "key": "musters",
                    "label": str(translate("honours.gate.musters", lexicon)),
                    "required": rule.musters,
                }
            )
        if rule.silver is not None:
            gates.append(
                {
                    "key": "silver",
                    "label": str(translate("honours.gate.silver", lexicon)),
                    "required": rule.silver,
                }
            )
        if rule.gold is not None:
            gates.append(
                {
                    "key": "gold",
                    "label": str(translate("honours.gate.gold", lexicon)),
                    "required": rule.gold,
                }
            )
        if rule.virtues is not None:
            gates.append(
                {
                    "key": "virtues",
                    "label": str(translate("honours.gate.virtues", lexicon)),
                    "required": rule.virtues,
                }
            )
        for name in rule.virtues_must_include:
            gates.append(
                {
                    "key": f"virtue:{name}",
                    "label": str(translate(f"honours.virtue.{name}", lexicon)),
                    "required": 1,
                }
            )
        if rule.fiefs is not None:
            gates.append(
                {
                    "key": "fiefs",
                    "label": str(translate("honours.gate.fiefs", lexicon)),
                    "required": rule.fiefs,
                }
            )
        if rule.vigil:
            gates.append(
                {
                    "key": "vigil",
                    "label": str(translate("honours.gate.vigil", lexicon)),
                    "required": 1,
                }
            )
        rows.append(
            {
                "key": rule.key,
                "name": str(translate(f"honours.title.{rule.key}", lexicon)),
                "degrees": rule.degrees,
                "gates": gates,
            }
        )
    return rows


@router.get("/guide", response_class=HTMLResponse)
async def guide(request: Request, session: SessionDep) -> HTMLResponse:
    """The guide of the whole round: the steps, the scoring and the ranks."""
    config = rewards_config.load_config()
    lexicon = settings_service.lexicon(session)
    context = base_context(
        request,
        session,
        active_page="guide",
        guide_tiers=_tiers(config, lexicon),
        guide_titles=_titles(config, lexicon),
        guide_degree_size=config.degree_size,
        guide_monthly_cap=config.counting.monthly_cap,
        guide_diminishing=int(config.counting.diminishing_factor * 100),
        guide_medals_per_fief=config.fiefs.medals_per_fief,
        guide_endgame_realms=config.endgame.realms,
        guide_endgame_title=str(translate(f"honours.title.{config.endgame.title}", lexicon)),
        guide_virtues=[
            {
                "key": virtue,
                "name": str(translate(f"honours.virtue.{virtue}", lexicon)),
            }
            for virtue in rewards_config.VIRTUES
        ],
    )
    return templates.TemplateResponse(request, "guide.html", context)
