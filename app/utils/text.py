"""Number/digit formatting helpers (Persian digits are the default)."""

from __future__ import annotations

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
LATIN_DIGITS = "0123456789"
PERSIAN_THOUSANDS_SEPARATOR = "٬"

_TRANSLATE_TO_PERSIAN = str.maketrans(LATIN_DIGITS + ARABIC_DIGITS, PERSIAN_DIGITS * 2)
_TRANSLATE_TO_LATIN = str.maketrans(PERSIAN_DIGITS + ARABIC_DIGITS, LATIN_DIGITS * 2)


def to_persian_digits(value: str) -> str:
    """Convert Latin/Arabic digits in a string to Persian digits."""
    return value.translate(_TRANSLATE_TO_PERSIAN)


def to_latin_digits(value: str) -> str:
    """Convert Persian/Arabic digits in a string to Latin digits."""
    return value.translate(_TRANSLATE_TO_LATIN)


def apply_digits(value: str, mode: str) -> str:
    """Apply the user's digit preference to a string."""
    if mode == "persian":
        return to_persian_digits(value)
    if mode == "latin":
        return to_latin_digits(value)
    return value


def format_number(value: int | float, mode: str = "persian", thousands: bool = False) -> str:
    """Format a number honouring the digit preference."""
    if thousands:
        raw = f"{value:,}"
    else:
        raw = f"{value}"
    if mode == "persian":
        raw = to_persian_digits(raw)
        if thousands:
            raw = raw.replace(",", PERSIAN_THOUSANDS_SEPARATOR)
    elif mode == "latin":
        raw = to_latin_digits(raw)
    return raw


def format_minutes(minutes: int | None, mode: str = "persian") -> str:
    """Render a number of minutes as a Persian duration string."""
    if minutes is None:
        return "—"
    sign = "-" if minutes < 0 else ""
    minutes = abs(int(minutes))
    hours, mins = divmod(minutes, 60)
    if hours and mins:
        text = f"{sign}{hours} ساعت و {mins} دقیقه"
    elif hours:
        text = f"{sign}{hours} ساعت"
    else:
        text = f"{sign}{mins} دقیقه"
    return apply_digits(text, mode)
