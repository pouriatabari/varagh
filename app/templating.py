"""Jinja2 environment, globals and filters shared by every page."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.templating import Jinja2Templates
from jinja2 import pass_eval_context
from markupsafe import Markup

from app.i18n import t
from app.utils.jalali import PERSIAN_MONTHS
from app.utils.markdown import render_markdown
from app.utils.text import apply_digits, to_persian_digits

TEMPLATES_DIR = Path(__file__).parent / "templates"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["t"] = t
templates.env.globals["persian_months"] = PERSIAN_MONTHS
templates.env.globals["app_name"] = "ورق"


@pass_eval_context
def _digits_filter(eval_ctx: Any, value: object) -> str:
    """Render a number honouring the current digit preference."""
    mode = eval_ctx.get("digits", "persian")
    return apply_digits(str(value), mode)


templates.env.filters["digits"] = _digits_filter
templates.env.filters["fa_digits"] = to_persian_digits
templates.env.filters["markdown"] = lambda value: Markup(render_markdown(value))
templates.env.filters["nl2br"] = lambda value: Markup(str(value or "").replace("\n", "<br />"))
