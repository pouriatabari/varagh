"""The seed: the demo rows, and the reset that keeps them from piling up."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import seed
from app.models.learning import LearningItem
from app.models.task import Task
from app.models.timing import TimeEntry
from app.services import learning as learning_service
from app.services import tasks as task_service
from app.services import time_entries as time_service
from app.utils.time import utcnow

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def _demo_task(session: Session) -> Task:
    """Create a task that carries the mark of the demo rows."""
    return task_service.create_task(
        session,
        title="نوشتن گزارش ماهانه",
        now=NOW,
        description_md="یادداشت نمونه برای «نوشتن گزارش ماهانه».",
    )


def test_the_reset_removes_the_demo_rows(session: Session) -> None:
    """The rows of the seed are removed before the seed runs again."""
    task = _demo_task(session)
    entry = time_service.create_entry(
        session,
        kind="work",
        started_at=NOW,
        now=NOW,
        duration_minutes=60,
        note="ثبت نمونه",
    )
    item = learning_service.create_item(
        session, title="توسعهٔ وب با FastAPI", kind="book", now=NOW, notes_md="مورد نمونه."
    )
    session.flush()

    seed._clear_demo_data(session, NOW)
    session.flush()

    assert task_service.get_task(session, task.id) is None
    assert session.get(TimeEntry, entry.id) is None
    assert session.get(LearningItem, item.id) is None


def test_the_reset_keeps_the_rows_of_the_user(session: Session) -> None:
    """The work of the user is never touched by the reset."""
    task = task_service.create_task(
        session, title="تسک من", now=NOW, description_md="یادداشت من."
    )
    entry = time_service.create_entry(
        session, kind="work", started_at=NOW, now=NOW, duration_minutes=60, note="یادداشت من"
    )
    item = learning_service.create_item(
        session, title="یادگیری من", kind="book", now=NOW, notes_md="یادداشت من."
    )
    session.flush()

    seed._clear_demo_data(session, NOW)
    session.flush()

    assert task_service.get_task(session, task.id) is not None
    assert session.get(TimeEntry, entry.id) is not None
    assert session.get(LearningItem, item.id) is not None


def test_the_demo_entries_are_finished_measurements(session: Session) -> None:
    """The demo entries are closed: they never look like a running timer."""
    seed._seed_time_entries(session, NOW)
    entries = session.scalars(select(TimeEntry)).all()
    assert entries
    for entry in entries:
        assert entry.ended_at is not None
        assert entry.duration_minutes is not None
        assert time_service.running_entry(session) is None


def test_the_demo_entries_hold_reasonable_durations(session: Session) -> None:
    """No demo entry lasts longer than a working day."""
    seed._seed_time_entries(session, NOW)
    for entry in session.scalars(select(TimeEntry)).all():
        assert entry.duration_minutes is not None
        assert entry.duration_minutes <= 24 * 60


def test_the_seed_marks_its_own_rows(session: Session) -> None:
    """The rows of the seed carry the marks the reset looks for."""
    seed._seed_tasks(session, utcnow())
    tasks = session.scalars(select(Task)).all()
    assert tasks
    for task in tasks:
        assert task.description_md.startswith(seed.DEMO_TASK_MARK)
