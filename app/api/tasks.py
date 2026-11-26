"""Task routes: list, filters, CRUD, quick-add, notes and domains."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.api.deps import SessionDep, base_context
from app.api.forms import form_datetime, form_int, form_optional_str, form_str
from app.security import validate_csrf
from app.services import settings as settings_service
from app.services import tasks as task_service
from app.services import time_entries as time_service
from app.templating import templates
from app.utils.time import utcnow

router = APIRouter(dependencies=[Depends(validate_csrf)])

VALID_STATUSES = {"todo", "doing", "done", "cancelled"}
VALID_ORIGINS = {"self_initiated", "assigned"}
VALID_CONTEXTS = {"company", "personal", "learning"}
VALID_DUE = {"today", "overdue", "this_week"}


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


def _filters_from_request(request: Request) -> task_service.TaskFilters:
    """Build the task filters from the query string."""
    params = request.query_params
    status = params.get("status") or None
    if status and status not in VALID_STATUSES and status != "open":
        status = None
    origin = params.get("origin") or None
    if origin not in VALID_ORIGINS:
        origin = None
    context = params.get("context") or None
    if context not in VALID_CONTEXTS:
        context = None
    due = params.get("due") or None
    if due not in VALID_DUE:
        due = None
    domain_id = params.get("domain")
    try:
        domain_id_int = int(domain_id) if domain_id else None
    except ValueError:
        domain_id_int = None
    return task_service.TaskFilters(
        q=(params.get("q") or "").strip() or None,
        status=status,
        origin=origin,
        context=context,
        due=due,
        domain_id=domain_id_int,
        include_deleted=params.get("deleted") == "1",
    )


def _task_context(request: Request, session: Session, **extra: object) -> dict[str, object]:
    context = base_context(request, session)
    context.update(extra)
    return context


@router.get("/tasks", response_class=HTMLResponse)
async def task_list(request: Request, session: SessionDep) -> HTMLResponse:
    """List tasks with filters."""
    timezone = settings_service.timezone_name(session)
    now = utcnow()
    filters = _filters_from_request(request)
    rows = task_service.list_tasks(session, filters, now=now, timezone=timezone)
    domains = task_service.list_domains(session)
    context = _task_context(
        request,
        session,
        active_page="tasks",
        tasks=rows,
        domains=domains,
        filters=filters,
        now=now,
        domain_names_by_task=task_service.domain_names_for_tasks(
            session, [task.id for task in rows]
        ),
    )
    return templates.TemplateResponse(request, "tasks.html", context)


@router.get("/tasks/new", response_class=HTMLResponse)
async def task_new(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the full task creation form."""
    context = _task_context(
        request,
        session,
        active_page="tasks",
        domains=task_service.list_domains(session),
        task=None,
    )
    return templates.TemplateResponse(request, "task_form.html", context)


@router.post("/tasks")
async def task_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Create a task from the full form."""
    form = await request.form()
    timezone = settings_service.timezone_name(session)
    now = utcnow()
    title = form_str(form, "title")
    if not title:
        return _redirect("/tasks/new", error="error.validation")
    status_value = form_str(form, "status")
    origin_value = form_str(form, "origin")
    context_value = form_str(form, "context")
    task = task_service.create_task(
        session,
        title=title,
        now=now,
        description_md=form_str(form, "description_md"),
        status=status_value if status_value in VALID_STATUSES else "todo",
        priority=form_int(form, "priority", 2) or 0,
        origin=origin_value if origin_value in VALID_ORIGINS else "self_initiated",
        assigned_by=form_optional_str(form, "assigned_by"),
        context=context_value if context_value in VALID_CONTEXTS else "personal",
        due_at=form_datetime(form, "due_at", timezone),
        effort_minutes_estimate=form_int(form, "effort_minutes_estimate"),
    )
    domain_ids = [int(value) for value in form.getlist("domain_ids") if str(value).isdigit()]
    if domain_ids:
        task_service.set_task_domains(session, task, domain_ids, now)
    return _redirect(f"/tasks/{task.id}", flash="flash.task_created")


@router.post("/tasks/quick-add", response_model=None)
async def task_quick_add(request: Request, session: SessionDep) -> Response:
    """Create a task from the quick-add bar (no AI involved)."""
    form = await request.form()
    title = form_str(form, "title")
    if not title:
        return _redirect("/tasks", error="error.validation")
    now = utcnow()
    task = task_service.create_task(session, title=title, now=now)
    if request.headers.get("hx-request"):
        context = _task_context(
            request, session, task=task, now=now, domain_names_by_task={}
        )
        return templates.TemplateResponse(request, "partials/task_item.html", context)
    return _redirect(f"/tasks/{task.id}", flash="flash.task_created")


@router.get("/tasks/{task_id}", response_class=HTMLResponse)
async def task_detail(request: Request, task_id: int, session: SessionDep) -> HTMLResponse:
    """Show a single task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    now = utcnow()
    notes = task_service.list_notes(session, task.id)
    entries = time_service.list_entries(session, task_id=task.id)
    domains = task_service.list_domains(session)
    task_domain_ids = [link.domain_id for link in task_service.task_domains(session, task.id)]
    context = _task_context(
        request,
        session,
        active_page="tasks",
        task=task,
        notes=notes,
        entries=entries,
        domains=domains,
        task_domain_ids=task_domain_ids,
        time_basis=time_service.task_hours_basis(task, session),
        now=now,
    )
    return templates.TemplateResponse(request, "task_detail.html", context)


@router.post("/tasks/{task_id}/update")
async def task_update(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Update the editable fields of a task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    form = await request.form()
    timezone = settings_service.timezone_name(session)
    now = utcnow()
    changes: dict[str, object] = {}
    if "title" in form:
        title = form_str(form, "title")
        if title:
            changes["title"] = title
    if "description_md" in form:
        changes["description_md"] = form_str(form, "description_md")
    if "priority" in form:
        changes["priority"] = form_int(form, "priority", task.priority)
    if "origin" in form:
        origin = form_str(form, "origin")
        changes["origin"] = origin if origin in VALID_ORIGINS else task.origin
    if "assigned_by" in form:
        changes["assigned_by"] = form_optional_str(form, "assigned_by")
    if "context" in form:
        context = form_str(form, "context")
        changes["context"] = context if context in VALID_CONTEXTS else task.context
    if "due_at" in form:
        changes["due_at"] = form_datetime(form, "due_at", timezone)
    if "effort_minutes_estimate" in form:
        changes["effort_minutes_estimate"] = form_int(form, "effort_minutes_estimate")
    task_service.update_task(session, task, now, **changes)
    return _redirect(f"/tasks/{task.id}", flash="flash.task_updated")


@router.post("/tasks/{task_id}/status")
async def task_status(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Change the status of a task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    form = await request.form()
    status = form_str(form, "status")
    if status not in VALID_STATUSES:
        return _redirect(f"/tasks/{task.id}", error="error.validation")
    now = utcnow()
    task_service.set_status(session, task, status, now)
    return _redirect(f"/tasks/{task.id}", flash="flash.task_updated")


@router.post("/tasks/{task_id}/delete")
async def task_delete(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Soft-delete a task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    task_service.soft_delete(session, task, utcnow())
    return _redirect("/tasks", flash="flash.task_deleted")


@router.post("/tasks/{task_id}/restore")
async def task_restore(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Undo a soft delete."""
    task = task_service.get_task(session, task_id, include_deleted=True)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    task_service.restore_task(session, task, utcnow())
    return _redirect(f"/tasks/{task.id}", flash="flash.task_updated")


@router.post("/tasks/{task_id}/notes")
async def task_add_note(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Append a note to a task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    form = await request.form()
    body = form_str(form, "body_md")
    if not body:
        return _redirect(f"/tasks/{task.id}", error="error.validation")
    task_service.add_note(session, task, body, utcnow())
    return _redirect(f"/tasks/{task.id}", flash="flash.note_added")


@router.post("/tasks/{task_id}/domains")
async def task_set_domains(request: Request, task_id: int, session: SessionDep) -> RedirectResponse:
    """Replace the domains of a task with the user's choice."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return _redirect("/tasks", error="error.not_found")
    form = await request.form()
    domain_ids = [int(value) for value in form.getlist("domain_ids") if str(value).isdigit()]
    task_service.set_task_domains(session, task, domain_ids, utcnow())
    return _redirect(f"/tasks/{task.id}", flash="flash.task_updated")


@router.post("/domains")
async def domain_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Create a new domain."""
    form = await request.form()
    name = form_str(form, "name")
    if not name:
        return _redirect("/tasks", error="error.validation")
    task_service.create_domain(session, name)
    return _redirect("/tasks", flash="flash.task_updated")


@router.get("/api/tasks")
async def api_tasks(request: Request, session: SessionDep) -> dict[str, object]:
    """JSON API returning the filtered task list."""
    timezone = settings_service.timezone_name(session)
    filters = _filters_from_request(request)
    rows = task_service.list_tasks(session, filters, now=utcnow(), timezone=timezone)
    return {
        "items": [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status,
                "origin": task.origin,
                "context": task.context,
                "due_at": task.due_at.isoformat() if task.due_at else None,
                "last_activity_at": (
                    task.last_activity_at.isoformat() if task.last_activity_at else None
                ),
            }
            for task in rows
        ],
        "count": len(rows),
    }


def _utc(moment: datetime) -> datetime:
    """Return an aware UTC datetime."""
    return moment.astimezone(UTC)
