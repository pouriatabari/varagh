"""The notification payload shared by every channel."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Notification:
    """A single thing worth telling the user about.

    ``window_key`` identifies the "window" the notification belongs to and is
    the key used for de-duplication: the same window is never notified twice.
    """

    kind: str
    ref_id: int
    title: str
    body: str
    window_key: str
    url: str = "/"
