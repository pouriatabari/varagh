"""Learning tracker routes: items, units, progress and the stale report."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from app.api.deps import SessionDep, base_context
from app.api.forms import form_int, form_str
from app.i18n import t
from app.security import validate_csrf
from app.services import charts as chart_service
from app.services import learning as learning_service
from app.templating import templates
from app.utils.time import utcnow

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


@router.get("/learning", response_class=HTMLResponse)
async def learning_list(request: Request, session: SessionDep) -> HTMLResponse:
    """List the learning items with their progress."""
    items = learning_service.list_items(session)
    charts = chart_service.build_charts(
        [
            {
                "type": "bar",
                "series": "progress_by_item",
                "title_fa": t("learning.progress_chart"),
                "basis": "measured",
            },
            {
                "type": "bar",
                "series": "minutes_by_item",
                "title_fa": t("learning.minutes_chart"),
                "basis": "measured",
            },
        ],
        learning_service.progress_series(session, items),
        id_prefix="learning",
    )
    context = base_context(
        request,
        session,
        active_page="learning",
        items=items,
        item_ids=[item.id for item in items],
        charts=charts,
        progress={item.id: learning_service.progress(session, item) for item in items},
        stale=[
            item
            for item, _progress in learning_service.stale_items(
                session, threshold_days=30, now=utcnow()
            )
        ],
    )
    return templates.TemplateResponse(request, "learning.html", context)


@router.get("/learning/new", response_class=HTMLResponse)
async def learning_new(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the form of a new learning item."""
    context = base_context(request, session, active_page="learning", item=None)
    return templates.TemplateResponse(request, "learning_form.html", context)


@router.post("/learning")
async def learning_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Create a learning item, optionally with its syllabus."""
    form = await request.form()
    title = form_str(form, "title")
    if not title:
        return _redirect("/learning/new", error="error.validation")
    item = learning_service.create_item(
        session,
        title=title,
        kind=form_str(form, "kind") or "book",
        author_or_provider=form_str(form, "author_or_provider") or None,
        notes_md=form_str(form, "notes_md"),
        now=utcnow(),
    )
    syllabus = form_str(form, "syllabus")
    if syllabus:
        learning_service.set_units(session, item, syllabus.splitlines())
    return _redirect(f"/learning/{item.id}", flash="flash.learning_created")


@router.get("/learning/{item_id}", response_class=HTMLResponse)
async def learning_detail(request: Request, item_id: int, session: SessionDep) -> HTMLResponse:
    """Show a learning item with its units and its study log."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    context = base_context(
        request,
        session,
        active_page="learning",
        item=item,
        units=learning_service.list_units(session, item.id),
        progress=learning_service.progress(session, item),
    )
    return templates.TemplateResponse(request, "learning_detail.html", context)


@router.post("/learning/{item_id}/delete")
async def learning_delete(request: Request, item_id: int, session: SessionDep) -> RedirectResponse:
    """Soft-delete a learning item."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    learning_service.soft_delete(session, item, utcnow())
    return _redirect("/learning", flash="flash.learning_deleted")


@router.post("/learning/delete")
async def learning_delete_many(request: Request, session: SessionDep) -> RedirectResponse:
    """Soft-delete every learning item of the selection."""
    form = await request.form()
    ids = [int(value) for value in form.getlist("item_ids") if str(value).isdigit()]
    if not ids:
        return _redirect("/learning", error="error.validation")
    now = utcnow()
    deleted = 0
    for item_id in ids:
        item = learning_service.get_item(session, item_id)
        if item is None:
            continue
        learning_service.soft_delete(session, item, now)
        deleted += 1
    if not deleted:
        return _redirect("/learning", error="error.not_found")
    return _redirect(f"/learning?flash=flash.learning_deleted_many&count={deleted}")


@router.post("/learning/{item_id}/status")
async def learning_status(request: Request, item_id: int, session: SessionDep) -> RedirectResponse:
    """Change the status of a learning item."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    form = await request.form()
    learning_service.set_status(session, item, form_str(form, "status"), utcnow())
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")


@router.post("/learning/{item_id}/units")
async def learning_add_unit(
    request: Request, item_id: int, session: SessionDep
) -> RedirectResponse:
    """Append a unit to a learning item."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    form = await request.form()
    title = form_str(form, "title")
    if not title:
        return _redirect(f"/learning/{item.id}", error="error.validation")
    learning_service.add_unit(session, item, title)
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")


@router.post("/learning/{item_id}/units/{unit_id}/toggle")
async def learning_toggle_unit(
    request: Request, item_id: int, unit_id: int, session: SessionDep
) -> RedirectResponse:
    """Mark a unit as read or not read."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    unit = next(
        (unit for unit in learning_service.list_units(session, item.id) if unit.id == unit_id),
        None,
    )
    if unit is None:
        return _redirect(f"/learning/{item.id}", error="error.not_found")
    now = utcnow()
    learning_service.tick_unit(session, unit, unit.done_at is None, now)
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")


@router.post("/learning/{item_id}/read-up-to")
async def learning_read_up_to(
    request: Request, item_id: int, session: SessionDep
) -> RedirectResponse:
    """Mark every unit up to the given one as read."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    form = await request.form()
    position = form_int(form, "position", 0) or 0
    now = utcnow()
    for unit in learning_service.list_units(session, item.id):
        learning_service.tick_unit(session, unit, unit.position <= position, now)
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")


@router.post("/learning/{item_id}/log")
async def learning_log(request: Request, item_id: int, session: SessionDep) -> RedirectResponse:
    """Record a study session."""
    item = learning_service.get_item(session, item_id)
    if item is None:
        return _redirect("/learning", error="error.not_found")
    form = await request.form()
    learning_service.log_activity(
        session,
        item,
        now=utcnow(),
        minutes=form_int(form, "minutes"),
        note=form_str(form, "note") or None,
    )
    return _redirect(f"/learning/{item.id}", flash="flash.learning_updated")
