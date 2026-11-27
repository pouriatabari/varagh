"""The drawings of a board.

A drawing is a PNG file in the data directory. The board saves it as a note
of the task, so the drawing stays with the task and can be seen again in the
notes of the task.
"""

from __future__ import annotations

import base64
import binascii
import re
import uuid
from pathlib import Path

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 4 * 1024 * 1024
NAME_PATTERN = re.compile(r"^[0-9a-f]{32}\.png$")
PREFIX = "data:image/png;base64,"


def drawings_dir(data_dir: str) -> Path:
    """Return the directory of the drawings."""
    return Path(data_dir) / "drawings"


def valid_name(name: str) -> bool:
    """Whether a file name is one of ours."""
    return bool(NAME_PATTERN.fullmatch(name))


def save_png(data_dir: str, data_url: str) -> str:
    """Save a PNG drawing and return its file name.

    The data URL is checked: it must carry a PNG, and it may not be bigger
    than a few megabytes. Anything else is refused.
    """
    if not data_url.startswith(PREFIX):
        raise ValueError("the drawing is not a PNG data URL")
    payload = data_url[len(PREFIX) :]
    if len(payload) > MAX_BYTES * 2:
        raise ValueError("the drawing is too big")
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("the drawing is not a valid base64 payload") from exc
    if not raw.startswith(PNG_MAGIC):
        raise ValueError("the drawing is not a PNG file")
    if len(raw) > MAX_BYTES:
        raise ValueError("the drawing is too big")
    directory = drawings_dir(data_dir)
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.png"
    (directory / name).write_bytes(raw)
    return name


def delete_png(data_dir: str, name: str) -> None:
    """Remove a drawing file."""
    if not valid_name(name):
        return
    path = drawings_dir(data_dir) / name
    if path.exists():
        path.unlink()
