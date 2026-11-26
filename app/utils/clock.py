"""Clock abstraction so every time-dependent code path is testable."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Minimal clock interface: the only source of "now" in the app."""

    def now(self) -> datetime:
        """Return the current time as a timezone-aware UTC datetime."""


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        """Return the current UTC time."""
        return datetime.now(UTC)


class FixedClock:
    """A clock frozen at a given instant — used by tests and the fake worker."""

    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        """Return the frozen instant."""
        return self.moment

    def advance(self, seconds: float) -> None:
        """Move the frozen instant forward."""
        from datetime import timedelta

        self.moment = self.moment + timedelta(seconds=seconds)


def system_clock() -> Clock:
    """Return the real clock."""
    return SystemClock()
