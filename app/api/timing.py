"""Time tracking, calendar and daily-journal routes."""

from __future__ import annotations

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import SessionDep, base_context
from app.api.forms import form_int, form_optional_str, form_str
from app.models.timing import DailyJournal
from app.security import validate_csrf
from app.services import settings as settings_service
from app.services import tasks as task_service
from app.services import time_entries as time_service
from app.templating import templates
from app.utils.jalali import (
    PERSIAN_MONTHS,
    PERSIAN_WEEKDAYS_SHORT,
    days_in_jalali_month,
    jalali_month_grid,
    jalali_of,
)
from app.utils.time import parse_jalali_date, parse_jalali_date_and_time, to_local, utcnow

router = APIRouter(dependencies=[Depends(validate_csrf)])

VALID_KINDS = {"work", "overtime", "study", "learning"}


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


def _today(session: Session) -> date:
    """Return today's date in the configured timezone."""
    timezone = settings_service.timezone_name(session)
    return to_local(utcnow(), timezone).date()


@router.get("/calendar", response_class=HTMLResponse)
async def calendar(request: Request, session: SessionDep) -> HTMLResponse:
    """Render the Jalali month grid with the measured minutes per day."""
    params = request.query_params
    today = _today(session)
    current = jalali_of(today)
    try:
        year = int(params.get("year") or current.year)
        month = int(params.get("month") or current.month)
    except ValueError:
        year, month = current.year, current.month
    if not 1 <= month <= 12:
        year, month = current.year, current.month

    weeks = jalali_month_grid(year, month)
    month_length = days_in_jalali_month(year, month)
    first_day = weeks[0][0] if weeks[0][0].month == month else weeks[1][0]
    last_day = first_day + timedelta(days=month_length - 1)

    totals = time_service.minutes_by_day(session, first_day, last_day)
    policy = time_service.policy_from_settings(session)
    off_days = {
        day for week in weeks for day in week if time_service.compute_is_off_day(day, policy)
    }

    selected_day: date | None = None
    selected_entries = []
    raw_day = params.get("day")
    if raw_day:
        parsed = parse_jalali_date(raw_day)
        if parsed is not None:
            selected_day = parsed
            selected_entries = time_service.list_entries_for_day(session, parsed)

    context = base_context(
        request,
        session,
        active_page="calendar",
        weeks=weeks,
        year=year,
        month=month,
        month_name=PERSIAN_MONTHS[month - 1],
        month_length=month_length,
        totals=totals,
        off_days=off_days,
        weekday_names=PERSIAN_WEEKDAYS_SHORT,
        selected_day=selected_day,
        selected_entries=selected_entries,
        today=today,
        prev_year=year - 1 if month == 1 else year,
        prev_month=12 if month == 1 else month - 1,
        next_year=year + 1 if month == 12 else year,
        next_month=1 if month == 12 else month + 1,
    )
    return templates.TemplateResponse(request, "calendar.html", context)


@router.post("/time/start")
async def start_timer(request: Request, session: SessionDep) -> RedirectResponse:
    """Start a running timer."""
    form = await request.form()
    kind = form_str(form, "kind", "work")
    if kind not in VALID_KINDS:
        kind = "work"
    task_id = form_int(form, "task_id")
    reason = form_optional_str(form, "reason")
    if kind == "overtime" and not reason:
        return _redirect("/calendar", error="time.overtime_reason_required")
    policy = time_service.policy_from_settings(session)
    time_service.start_timer(
        session,
        now=utcnow(),
        kind=kind,
        task_id=task_id,
        reason=reason,
        policy=policy,
    )
    return _redirect("/calendar", flash="flash.time_created")


@router.post("/time/stop")
async def stop_timer(request: Request, session: SessionDep) -> RedirectResponse:
    """Stop the running timer."""
    entry = time_service.running_entry(session)
    if entry is None:
        return _redirect("/calendar", error="error.not_found")
    time_service.stop_timer(session, entry, utcnow())
    return _redirect("/calendar", flash="flash.time_created")


@router.post("/time/entries")
async def create_entry(request: Request, session: SessionDep) -> RedirectResponse:
    """Create a manual time entry."""
    form = await request.form()
    timezone = settings_service.timezone_name(session)
    kind = form_str(form, "kind", "work")
    if kind not in VALID_KINDS:
        kind = "work"
    reason = form_optional_str(form, "reason")
    if kind == "overtime" and not reason:
        return _redirect("/calendar", error="time.overtime_reason_required")
    started_at = parse_jalali_date_and_time(
        form_str(form, "date"), form_str(form, "start_time"), timezone
    )
    if started_at is None:
        return _redirect("/calendar", error="error.validation")
    duration = form_int(form, "duration_minutes")
    ended_at = None
    if duration is None:
        ended_at = parse_jalali_date_and_time(
            form_str(form, "date"), form_str(form, "end_time"), timezone
        )
        if ended_at is None:
            return _redirect("/calendar", error="error.validation")
    policy = time_service.policy_from_settings(session)
    time_service.create_entry(
        session,
        kind=kind,
        started_at=started_at,
        now=utcnow(),
        ended_at=ended_at,
        duration_minutes=duration,
        task_id=form_int(form, "task_id"),
        reason=reason,
        note=form_optional_str(form, "note"),
        policy=policy,
    )
    return _redirect("/calendar", flash="flash.time_created")


@router.post("/time/entries/{entry_id}/delete")
async def delete_entry(request: Request, entry_id: int, session: SessionDep) -> RedirectResponse:
    """Delete a time entry."""
    entry = time_service.get_entry(session, entry_id)
    if entry is None:
        return _redirect("/calendar", error="error.not_found")
    time_service.delete_entry(session, entry)
    return _redirect("/calendar", flash="flash.time_deleted")


@router.get("/journal", response_class=HTMLResponse)
async def journal_page(request: Request, session: SessionDep) -> HTMLResponse:
    """Show the daily journal."""
    rows = list(
        session.scalars(select(DailyJournal).order_by(DailyJournal.date.desc()).limit(60)).all()
    )
    context = base_context(
        request,
        session,
        active_page="calendar",
        entries=rows,
        today=_today(session),
    )
    return templates.TemplateResponse(request, "journal.html", context)


@router.post("/journal")
async def journal_create(request: Request, session: SessionDep) -> RedirectResponse:
    """Store a journal entry.

    In manual mode the text is stored as it is. In AI mode the proposals the
    user confirmed are stored next to it; nothing is ever written before the
    confirmation.
    """
    form = await request.form()
    raw_text = form_str(form, "raw_text")
    if not raw_text:
        return _redirect("/journal", error="error.validation")
    mode = form_str(form, "mode") or "manual"
    parsed = None
    if mode == "ai":
        parsed = {
            "entries": _parse_entries(form_str(form, "entries")),
            "summary_fa": form_str(form, "summary"),
        }
    day = parse_jalali_date(form_str(form, "date")) or _today(session)
    entry = session.scalars(select(DailyJournal).where(DailyJournal.date == day)).first()
    if entry is None:
        entry = DailyJournal(date=day, raw_text=raw_text, parsed=parsed, confirmed=True)
        session.add(entry)
    else:
        entry.raw_text = raw_text
        entry.parsed = parsed
        entry.confirmed = True
    return _redirect("/journal", flash="flash.time_created")


def _parse_entries(raw: str) -> list[dict[str, object]]:
    """Parse the confirmed entries of a journal."""
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


@router.get("/tasks/{task_id}/time", response_class=HTMLResponse)
async def task_time_form(request: Request, task_id: int, session: SessionDep) -> HTMLResponse:
    """Return the partial used to attach time to a task."""
    task = task_service.get_task(session, task_id)
    if task is None:
        return HTMLResponse("", status_code=404)
    context = base_context(request, session, task=task)
    return templates.TemplateResponse(request, "partials/task_time_form.html", context)
