"""Task service and route tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import tasks as task_service

NOW = datetime(2024, 8, 5, 9, 0, tzinfo=UTC)


def _make_task(session: Session, **kwargs: object):
    payload: dict[str, object] = {"title": "نوشتن گزارش", "now": NOW}
    payload.update(kwargs)
    return task_service.create_task(session, **payload)  # type: ignore[arg-type]


def test_create_task_sets_activity_stamp(session: Session) -> None:
    """A new task records its creation and last activity."""
    task = _make_task(session)
    assert task.id is not None
    assert task.status == "todo"
    assert task.origin == "self_initiated"
    assert task.context == "personal"
    assert task.last_activity_at == NOW


def test_set_status_maintains_timestamps(session: Session) -> None:
    """Moving a task to done stamps started_at and completed_at."""
    task = _make_task(session)
    task_service.set_status(session, task, "doing", NOW)
    assert task.started_at == NOW
    task_service.set_status(session, task, "done", NOW + timedelta(hours=2))
    assert task.completed_at == NOW + timedelta(hours=2)
    assert task.status == "done"


def test_soft_delete_hides_the_task(session: Session) -> None:
    """A soft-deleted task disappears from the default listing."""
    task = _make_task(session)
    task_service.soft_delete(session, task, NOW)
    visible = task_service.list_tasks(session, task_service.TaskFilters(), now=NOW)
    assert task not in visible
    assert task_service.get_task(session, task.id) is None
    assert task_service.get_task(session, task.id, include_deleted=True) is not None


def test_filters_by_origin_context_and_domain(session: Session) -> None:
    """Filters narrow the task list down."""
    mine = _make_task(session, title="کار شخصی", origin="self_initiated", context="personal")
    theirs = _make_task(session, title="کار محول‌شده", origin="assigned", context="company")
    domain = task_service.create_domain(session, "پروژهٔ الف")

    assert task_service.list_tasks(
        session, task_service.TaskFilters(origin="assigned"), now=NOW
    ) == [theirs]
    assert task_service.list_tasks(
        session, task_service.TaskFilters(context="personal"), now=NOW
    ) == [mine]

    task_service.assign_domain(session, theirs, domain, source="user", confirmed=True)
    assert task_service.list_tasks(
        session, task_service.TaskFilters(domain_id=domain.id), now=NOW
    ) == [theirs]


def test_overdue_filter_ignores_finished_tasks(session: Session) -> None:
    """Overdue means past due and not finished."""
    late = _make_task(session, title="عقب‌افتاده", due_at=NOW - timedelta(days=2))
    finished = _make_task(session, title="تمام‌شده", due_at=NOW - timedelta(days=2))
    task_service.set_status(session, finished, "done", NOW)

    overdue = task_service.list_tasks(session, task_service.TaskFilters(due="overdue"), now=NOW)
    assert late in overdue
    assert finished not in overdue


def test_user_domain_choice_is_never_overwritten_by_ai(session: Session) -> None:
    """A confirmed user domain wins over an AI suggestion."""
    task = _make_task(session)
    domain = task_service.create_domain(session, "یادگیری")
    task_service.assign_domain(session, task, domain, source="user", confirmed=True)
    task_service.assign_domain(session, task, domain, source="ai", confidence=0.2)
    link = task_service.task_domains(session, task.id)[0]
    assert link.source == "user"
    assert link.confirmed is True


def test_task_list_page_renders(client: TestClient) -> None:
    """The task list page answers with 200."""
    response = client.get("/tasks")
    assert response.status_code == 200
    assert "تسک‌ها" in response.text


def test_quick_add_creates_a_task(client: TestClient, session: Session) -> None:
    """The quick-add bar creates a task and redirects to it."""
    response = client.post("/tasks/quick-add", data={"title": "خرید نان"}, follow_redirects=False)
    assert response.status_code == 303
    rows = task_service.list_tasks(session, task_service.TaskFilters(), now=NOW)
    assert [task.title for task in rows] == ["خرید نان"]


def test_quick_add_returns_an_htmx_partial(client: TestClient) -> None:
    """With the HTMX header the quick-add returns only the task item."""
    response = client.post(
        "/tasks/quick-add",
        data={"title": "تسک HTMX"},
        headers={"hx-request": "true"},
    )
    assert response.status_code == 200
    assert "task-item" in response.text
    assert "<html" not in response.text


def test_task_detail_page_shows_the_title(client: TestClient, session: Session) -> None:
    """The detail page renders the task."""
    task = _make_task(session, title="گزارش ماهانه")
    response = client.get(f"/tasks/{task.id}")
    assert response.status_code == 200
    assert "گزارش ماهانه" in response.text


def test_soft_delete_route_hides_the_task(client: TestClient, session: Session) -> None:
    """Deleting a task removes it from the listing."""
    task = _make_task(session, title="حذف‌شونده")
    response = client.post(f"/tasks/{task.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    listing = client.get("/tasks")
    assert "حذف‌شونده" not in listing.text


def test_markdown_is_sanitised(client: TestClient, session: Session) -> None:
    """Raw HTML in a task description never reaches the page."""
    task = _make_task(session, title="ناامن", description_md="<script>alert(1)</script> **مهم**")
    response = client.get(f"/tasks/{task.id}")
    assert "<script>alert(1)</script>" not in response.text
    assert "<strong>مهم</strong>" in response.text


def test_api_tasks_returns_json(client: TestClient, session: Session) -> None:
    """The JSON API lists the tasks."""
    _make_task(session, title="تسک API")
    response = client.get("/api/tasks")
    assert response.status_code == 200
    assert response.json()["count"] == 1


def test_a_task_can_be_deleted_from_the_list(client: TestClient, session: Session) -> None:
    """The delete button of the task list soft-deletes the task."""
    task = _make_task(session, title="تسک برای حذف")
    response = client.post(f"/tasks/{task.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert task.deleted_at is not None


def test_several_tasks_can_be_deleted_at_once(client: TestClient, session: Session) -> None:
    """The selection of the task list deletes every chosen task."""
    first = _make_task(session, title="تسک اول")
    second = _make_task(session, title="تسک دوم")
    response = client.post(
        "/tasks/delete",
        data={"task_ids": [first.id, second.id]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "flash.tasks_deleted" in response.headers["location"]
    assert first.deleted_at is not None
    assert second.deleted_at is not None


def test_a_deleted_task_leaves_the_list(client: TestClient, session: Session) -> None:
    """A deleted task is not listed any more."""
    task = _make_task(session, title="تسک پنهان")
    client.post(f"/tasks/{task.id}/delete")
    response = client.get("/tasks")
    assert "تسک پنهان" not in response.text


def test_the_task_list_offers_the_selection(client: TestClient, session: Session) -> None:
    """The list shows the checkboxes and the bulk action."""
    _make_task(session, title="تسک انتخابی")
    response = client.get("/tasks")
    assert response.status_code == 200
    assert 'name="task_ids"' in response.text
    assert "/tasks/delete" in response.text
