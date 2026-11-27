"""Jinja2 environment, globals and filters shared by every page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from markupsafe import Markup

from app.i18n import Term, tip, translate
from app.i18n import t as translate_plain
from app.utils.jalali import PERSIAN_MONTHS, jalali_input_string, jalali_of
from app.utils.markdown import render_markdown
from app.utils.text import apply_digits, format_minutes, to_persian_digits
from app.utils.time import format_date, format_datetime

TEMPLATES_DIR = Path(__file__).parent / "templates"
STATIC_DIR = Path(__file__).parent / "static"
ICON_DIR = STATIC_DIR / "icons"

_ICON_CACHE: dict[str, str] = {}


def read_icon(name: str) -> str:
    """Return the SVG of an icon, or an empty string when it is missing.

    The icons are read once and kept in memory: a page may hold a few of
    them, and the files never change while the app runs.
    """
    if name not in _ICON_CACHE:
        path = ICON_DIR / name
        try:
            _ICON_CACHE[name] = path.read_text(encoding="utf-8").strip()
        except OSError:
            _ICON_CACHE[name] = ""
    return _ICON_CACHE[name]


def read_manifest() -> list[dict[str, str]]:
    """Return the entries of the icon manifest: the name, the source and
    the licence of every vendored icon."""
    try:
        data = json.loads((ICON_DIR / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [entry for entry in data if isinstance(entry, dict)]


@pass_context
def _t(context: Any, key: str, **kwargs: Any) -> str:
    """Translate a key in the pack the user has chosen."""
    pack = context.get("lexicon", "plain")
    return str(translate(key, pack, **kwargs))


@pass_context
def _t_term(context: Any, key: str, **kwargs: Any) -> Term:
    """Translate a key and keep the plain wording with it."""
    pack = context.get("lexicon", "plain")
    return translate(key, pack, **kwargs)


@pass_context
def _t_plain(context: Any, key: str, **kwargs: Any) -> str:
    """Translate a key in the plain pack, whatever the pack of the user is."""
    return str(translate(key, "plain", **kwargs))


templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["t"] = _t
templates.env.globals["t_term"] = _t_term
templates.env.globals["t_plain"] = _t_plain
templates.env.globals["persian_months"] = PERSIAN_MONTHS
templates.env.globals["app_name"] = "ورق"
templates.env.globals["jalali_of"] = jalali_of
templates.env.globals["ICON_DIR"] = str(ICON_DIR) + "/"
templates.env.globals["read_icon"] = read_icon


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


@pass_context
def _rating_filter(context: Any, value: object) -> str:
    """Render a rating with its scale, e.g. ۴ از ۵."""
    mode = context.get("digits", "persian")
    if value is None or value == "":
        return ""
    scale = translate_plain("reviews.rating_of").format(max=apply_digits("5", mode))
    return f"{apply_digits(str(value), mode)} {scale}"


templates.env.filters["tip"] = tip
templates.env.filters["digits"] = _digits_filter
templates.env.filters["rating"] = _rating_filter
templates.env.filters["fa_digits"] = to_persian_digits
templates.env.filters["markdown"] = lambda value: Markup(render_markdown(value))
templates.env.filters["nl2br"] = lambda value: Markup(str(value or "").replace("\n", "<br />"))
templates.env.filters["jdatetime"] = _datetime_filter
templates.env.filters["jdate"] = _date_filter
templates.env.filters["duration"] = _minutes_filter
templates.env.filters["jalali_input"] = jalali_input_string
