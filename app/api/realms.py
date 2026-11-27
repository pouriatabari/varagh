"""The map of the realms: the page, the assignment and the suggestion."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.ai.provider import AIError, get_provider
from app.ai.service import suggest_realm
from app.api.deps import SessionDep, base_context
from app.api.forms import form_int
from app.models.task import Domain
from app.security import validate_csrf
from app.services import realm_map, realms
from app.services.tasks import list_domains
from app.templating import templates

router = APIRouter(dependencies=[Depends(validate_csrf)])


def _redirect(url: str, flash: str | None = None, error: str | None = None) -> RedirectResponse:
    """Redirect back to a page, optionally carrying a flash message."""
    params = []
    if flash:
        params.append(f"flash={flash}")
    if error:
        params.append(f"error={error}")
    if params:
        joiner = "&" if "?" in url else "?"
        url = f"{url}{joiner}{'&'.join(params)}"
    return RedirectResponse(url, status_code=303)


def _int_param(value: str | None) -> int:
    """Read an integer out of the query string."""
    try:
        return int(value or 0)
    except ValueError:
        return 0


def _candidates(session: Session) -> list[dict]:
    """The realms a domain may take, as the AI may read them."""
    return [
        {
            "key": realm.key,
            "name_fa": realm.name_fa,
            "coverage_fa": realm.coverage_fa,
            "themes": list(realm.themes),
        }
        for realm in realms.assignable_realms(session)
    ]


@router.get("/realms", response_class=HTMLResponse)
async def realm_map_page(request: Request, session: SessionDep) -> HTMLResponse:
    """The map of the realms."""
    states = realms.states(session)
    route = realms.campaign_route(session)
    context = base_context(
        request,
        session,
        active_page="realms",
        realm_states=states,
        realm_map_svg=realm_map.map_svg(states, route),
        realm_route=route,
        realm_candidates=realms.assignable_realms(session),
        realm_domains=list_domains(session),
        realm_claimed=len(route),
        ceremony=request.query_params.get("ceremony") == "1",
        suggested=request.query_params.get("suggested", ""),
        suggested_domain=_int_param(request.query_params.get("domain")),
    )
    return templates.TemplateResponse(request, "realms.html", context)


@router.post("/realms/assign")
async def realm_assign(request: Request, session: SessionDep) -> RedirectResponse:
    """Give a realm to a domain."""
    form = await request.form()
    realm_key = str(form.get("realm_key", ""))
    domain_id = form_int(form, "domain_id", 0)
    if not realm_key or not domain_id:
        return _redirect("/realms", error="error.validation")
    try:
        realms.assign_realm(session, realm_key, domain_id)
    except ValueError:
        return _redirect("/realms", error="realms.assign_error")
    return _redirect("/realms", flash="realms.assigned")


@router.post("/realms/suggest")
async def realm_suggest(request: Request, session: SessionDep) -> RedirectResponse:
    """Ask the AI which free realm fits the craft of a domain.

    The AI only names a realm of the list; the user still takes it.
    """
    form = await request.form()
    domain_id = form_int(form, "domain_id", 0)
    if not domain_id:
        return _redirect("/realms", error="error.validation")
    domain = session.get(Domain, domain_id)
    if domain is None:
        return _redirect("/realms", error="error.not_found")
    candidates = _candidates(session)
    if not candidates:
        return _redirect("/realms", error="realms.no_candidates")
    provider = get_provider(session)
    if provider is None:
        return _redirect("/realms", error="error.ai_disabled")
    try:
        draft = suggest_realm(
            session,
            provider,
            domain_name=domain.name,
            candidates=candidates,
        )
    except AIError:
        return _redirect("/realms", error="error.ai_failed")
    return _redirect(f"/realms?suggested={draft.realm_key}&domain={domain_id}")
