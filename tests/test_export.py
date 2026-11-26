"""The JSON export and the demo data."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import export as export_service
from app.services import learning as learning_service
from app.services import tasks as task_service
from app.services import time_entries as time_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def test_export_contains_every_table(session: Session) -> None:
    """The export carries the tasks, the entries and the learning items."""
    task = task_service.create_task(session, title="تسک", now=NOW)
    time_service.create_entry(
        session, kind="work", started_at=NOW, now=NOW, duration_minutes=30, task_id=task.id
    )
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    learning_service.add_unit(session, item, "فصل اول")

    payload = export_service.export_all(session)
    assert len(payload["tasks"]) == 1
    assert payload["tasks"][0]["title"] == "تسک"
    assert len(payload["time_entries"]) == 1
    assert payload["time_entries"][0]["duration_minutes"] == 30
    assert payload["learning_items"][0]["units"][0]["title"] == "فصل اول"
    assert "exported_at" in payload


def test_export_route_returns_json(client: TestClient) -> None:
    """The export route serves the document."""
    response = client.get("/export.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "tasks" in response.json()


def test_the_seed_script_is_importable() -> None:
    """The seed module exposes the entry point used by ``make seed``."""
    from app import seed

    assert callable(seed.seed)
    assert callable(seed.main)
