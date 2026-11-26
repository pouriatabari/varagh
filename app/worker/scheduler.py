"""Scheduler wiring for the background worker.

The worker only *decides* what should be notified and records it in
``notification_log``; the browser turns those into OS-level notifications
(a Docker container cannot notify the host operating system directly).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.config import get_settings
from app.services import settings as settings_service

logger = logging.getLogger("varagh.worker")

# How often the worker re-evaluates the notification rules.
CHECK_INTERVAL_MINUTES = 5


def build_scheduler() -> BackgroundScheduler:
    """Build the APScheduler instance with the periodic jobs registered."""
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone=settings.timezone)
    scheduler.add_job(
        run_scheduled_jobs,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="varagh-scheduled-jobs",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    return scheduler


def run_scheduled_jobs() -> None:
    """Job executed on every tick — implemented fully in the notification milestone."""
    from app.db import get_session_factory

    session = get_session_factory()()
    try:
        configured = settings_service.get_all_settings(session)
        logger.debug("scheduled jobs tick (timezone=%s)", configured.get("timezone"))
    finally:
        session.close()


def run_scheduler() -> None:
    """Start the scheduler and block."""
    scheduler = build_scheduler()
    scheduler.start()
    try:
        import threading

        threading.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("worker stopping")
    finally:
        scheduler.shutdown(wait=False)
