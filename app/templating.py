"""Jinja2 environment, globals and filters shared by every page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from markupsafe import Markup

from app.i18n import t
from app.utils.jalali import PERSIAN_MONTHS, jalali_input_string, jalali_of
from app.utils.markdown import render_markdown
from app.utils.text import apply_digits, format_minutes, to_persian_digits
from app.utils.time import format_date, format_datetime

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["t"] = t
templates.env.globals["persian_months"] = PERSIAN_MONTHS
templates.env.globals["app_name"] = "ورق"
templates.env.globals["jalali_of"] = jalali_of


@pass_context
def _digits_filter(context: Any, value: object) -> str:
    """Render a number honouring the current digit preference."""
    mode = context.get("digits", "persian")
    return apply_digits(str(value), mode)


@pass_context
def _datetime_filter(context: Any, value: object, with_time: bool = True) -> str:
    """Render a datetime as a Jalali string."""
    timezone = context.get("timezone", "Asia/Tehran")
    mode = context.get("digits", "persian")
    return format_datetime(value, timezone, mode, with_time)


@pass_context
def _date_filter(context: Any, value: object) -> str:
    """Render a date as a Jalali string."""
    mode = context.get("digits", "persian")
    return format_date(value, mode)


@pass_context
def _minutes_filter(context: Any, value: object) -> str:
    """Render a number of minutes as a Persian duration."""
    mode = context.get("digits", "persian")
    return format_minutes(value if isinstance(value, int) else None, mode)


templates.env.filters["digits"] = _digits_filter
templates.env.filters["fa_digits"] = to_persian_digits
templates.env.filters["markdown"] = lambda value: Markup(render_markdown(value))
templates.env.filters["nl2br"] = lambda value: Markup(str(value or "").replace("\n", "<br />"))
templates.env.filters["jdatetime"] = _datetime_filter
templates.env.filters["jdate"] = _date_filter
templates.env.filters["duration"] = _minutes_filter
templates.env.filters["jalali_input"] = jalali_input_string
