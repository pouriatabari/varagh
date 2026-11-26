"""Board routes: sticky notes on a per-task board."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from app.api.deps import SessionDep, base_context
from app.api.forms import form_str
from app.models.task import BoardItem
from app.services import board as board_service
from app.services import tasks as task_service
from app.templating import templates

router = APIRouter()


def _board_context(request: Request, session: SessionDep, task_id: int) -> dict[str, object]:
    """Build the template context of the board partial."""
    context = base_context(request, session, task_id=task_id)
    context["board_items"] = board_service.list_items(session, task_id)
    return context


@router.get("/tasks/{task_id}/board", response_class=HTMLResponse)
async def board_list(request: Request, task_id: int, session: SessionDep) -> HTMLResponse:
    """Return the board of a task as an HTMX partial."""
    return templates.TemplateResponse(
        request, "partials/board.html", _board_context(request, session, task_id)
    )


@router.post("/tasks/{task_id}/board", response_class=HTMLResponse)
async def board_create(request: Request, task_id: int, session: SessionDep) -> HTMLResponse:
    """Add a sticky note to the board."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return templates.TemplateResponse(
            request, "partials/board.html", _board_context(request, session, task_id)
        )
    form = await request.form()
    content = form_str(form, "content")
    if content:
        board_service.create_item(
            session,
            task_id=task.id,
            content=content,
            item_type=form_str(form, "type") or "sticky",
            color=form_str(form, "color") or "yellow",
        )
    return templates.TemplateResponse(
        request, "partials/board.html", _board_context(request, session, task.id)
    )


@router.post("/tasks/{task_id}/board/{item_id}/move")
async def board_move(
    request: Request, task_id: int, item_id: int, session: SessionDep
) -> JSONResponse:
    """Persist the position of a sticky note."""
    item = session.get(BoardItem, item_id)
    if item is None or item.task_id != task_id:
        return JSONResponse({"ok": False}, status_code=404)
    form = await request.form()
    try:
        x = float(form_str(form, "x") or 0)
        y = float(form_str(form, "y") or 0)
    except ValueError:
        return JSONResponse({"ok": False, "error": "invalid position"}, status_code=400)
    board_service.move_item(session, item, x, y)
    return JSONResponse({"ok": True, "x": item.x, "y": item.y})


@router.post("/tasks/{task_id}/board/{item_id}/update", response_class=HTMLResponse)
async def board_update(
    request: Request, task_id: int, item_id: int, session: SessionDep
) -> HTMLResponse:
    """Update the text or the colour of a sticky note."""
    item = session.get(BoardItem, item_id)
    if item is None or item.task_id != task_id:
        return templates.TemplateResponse(
            request, "partials/board.html", _board_context(request, session, task_id)
        )
    form = await request.form()
    board_service.update_item(
        session,
        item,
        content=form_str(form, "content"),
        color=form_str(form, "color") or None,
    )
    return templates.TemplateResponse(
        request, "partials/board.html", _board_context(request, session, task_id)
    )


@router.post("/tasks/{task_id}/board/{item_id}/delete", response_class=HTMLResponse)
async def board_delete(
    request: Request, task_id: int, item_id: int, session: SessionDep
) -> Response:
    """Remove a sticky note."""
    item = session.get(BoardItem, item_id)
    if item is not None and item.task_id == task_id:
        board_service.delete_item(session, item)
    return templates.TemplateResponse(
        request, "partials/board.html", _board_context(request, session, task_id)
    )
