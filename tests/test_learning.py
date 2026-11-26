"""The learning tracker."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import learning as learning_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def test_create_item_starts_not_started(session: Session) -> None:
    """A new learning item has not started yet."""
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    assert item.status == "not_started"
    assert item.kind == "book"


def test_units_and_progress(session: Session) -> None:
    """The progress is the share of the finished units."""
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    first = learning_service.add_unit(session, item, "فصل اول")
    learning_service.add_unit(session, item, "فصل دوم")
    progress = learning_service.progress(session, item)
    assert progress.total_units == 2
    assert progress.done_units == 0
    assert progress.percent == 0

    learning_service.tick_unit(session, first, True, NOW)
    progress = learning_service.progress(session, item)
    assert progress.done_units == 1
    assert progress.percent == 50


def test_logging_activity_starts_the_item(session: Session) -> None:
    """Logging a study session moves the item to «in progress»."""
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    learning_service.log_activity(session, item, now=NOW, minutes=45)
    assert item.status == "in_progress"
    assert learning_service.progress(session, item).minutes == 45


def test_stale_items_are_reported(session: Session) -> None:
    """An item without activity for too long is reported as stale."""
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    learning_service.set_status(session, item, "in_progress", NOW)
    later = dt.datetime.now(dt.UTC) + dt.timedelta(days=60)
    stale = learning_service.stale_items(session, threshold_days=30, now=later)
    assert [row[0].id for row in stale] == [item.id]


def test_the_report_sums_the_items(session: Session) -> None:
    """The report counts the items and their minutes."""
    item = learning_service.create_item(session, title="کتاب", now=NOW)
    learning_service.log_activity(session, item, now=NOW, minutes=30)
    learning_service.set_status(session, item, "done", NOW)
    report = learning_service.learning_report(session, now=NOW)
    assert report["total_items"] == 1
    assert report["finished"] == 1
    assert report["total_minutes"] == 30


def test_learning_pages_render(client: TestClient) -> None:
    """The learning pages render."""
    assert client.get("/learning").status_code == 200
    assert client.get("/learning/new").status_code == 200


def test_the_learning_routes_work(client: TestClient) -> None:
    """Creating an item, adding units and reading up to one of them."""
    response = client.post(
        "/learning",
        data={"title": "کتاب تست", "kind": "book", "syllabus": "فصل اول\nفصل دوم"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    location = response.headers["location"]
    item_id = int(location.rsplit("/", 1)[-1].split("?")[0])

    detail = client.get(f"/learning/{item_id}")
    assert detail.status_code == 200
    assert "فصل اول" in detail.text

    read_up_to = client.post(
        f"/learning/{item_id}/read-up-to",
        data={"position": "0"},
        follow_redirects=False,
    )
    assert read_up_to.status_code == 303

    logged = client.post(
        f"/learning/{item_id}/log",
        data={"minutes": "25", "note": "مطالعه"},
        follow_redirects=False,
    )
    assert logged.status_code == 303
