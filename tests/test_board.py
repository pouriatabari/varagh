"""The per-task board: sticky notes."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.task import BoardItem
from app.services import board as board_service
from app.services import tasks as task_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def test_create_item_defaults(session: Session) -> None:
    """A new board item is a yellow sticky at the origin."""
    task = task_service.create_task(session, title="تسک", now=NOW)
    item = board_service.create_item(session, task_id=task.id, content="یادداشت")
    assert item.type == "sticky"
    assert item.color == "yellow"
    assert item.x == 0.0
    assert item.y == 0.0


def test_move_item_persists_the_position(session: Session) -> None:
    """Moving a sticky stores the new coordinates."""
    task = task_service.create_task(session, title="تسک", now=NOW)
    item = board_service.create_item(session, task_id=task.id, content="یادداشت")
    board_service.move_item(session, item, 120.5, 40.0)
    assert item.x == 120.5
    assert item.y == 40.0


def test_update_item_changes_text_and_color(session: Session) -> None:
    """The text and the colour of a sticky can be changed."""
    task = task_service.create_task(session, title="تسک", now=NOW)
    item = board_service.create_item(session, task_id=task.id, content="اولی")
    board_service.update_item(session, item, content="دومی", color="blue")
    assert item.content == "دومی"
    assert item.color == "blue"


def test_delete_item(session: Session) -> None:
    """A sticky can be removed."""
    task = task_service.create_task(session, title="تسک", now=NOW)
    item = board_service.create_item(session, task_id=task.id, content="یادداشت")
    board_service.delete_item(session, item)
    assert board_service.list_items(session, task.id) == []


def test_board_route_creates_and_moves_a_sticky(client: TestClient) -> None:
    """The board routes create, move and delete the sticky notes."""
    from app.db import get_session

    task = client.post(
        "/tasks/quick-add",
        data={"title": "تسک تخته"},
        follow_redirects=False,
    )
    assert task.status_code == 303
    location = task.headers["location"]
    task_id = int(location.rsplit("/", 1)[-1].split("?")[0])

    response = client.post(
        f"/tasks/{task_id}/board",
        data={"content": "یادداشت چسبان", "color": "green"},
    )
    assert response.status_code == 200
    assert "یادداشت چسبان" in response.text

    items = client.get(f"/tasks/{task_id}/board").text
    assert "sticky c-green" in items

    session = client.app.dependency_overrides[get_session]()
    item = session.query(BoardItem).one()
    moved = client.post(
        f"/tasks/{task_id}/board/{item.id}/move",
        data={"x": "30", "y": "45"},
    )
    assert moved.status_code == 200
    assert moved.json() == {"ok": True, "x": 30.0, "y": 45.0}

    deleted = client.post(f"/tasks/{task_id}/board/{item.id}/delete")
    assert deleted.status_code == 200
    assert 'class="sticky' not in deleted.text
