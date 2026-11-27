"""The deletion of the records of every section, and the review rating."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services import achievements as achievement_service
from app.services import learning as learning_service
from app.services import reviews as review_service
from app.services import tasks as task_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def _task(session: Session, title: str = "تسک"):
    task = task_service.create_task(session, title=title, now=NOW)
    session.flush()
    return task


def _learning_item(session: Session, title: str = "کتاب"):
    return learning_service.create_item(session, title=title, now=NOW)


def _review(session: Session):
    period = review_service.PeriodSelection(
        period_type="month",
        start=dt.date(2024, 8, 1),
        end=dt.date(2024, 8, 31),
    )
    return review_service.create_review(
        session,
        period=period,
        stats={"counts": {"completed": 1}},
    )


# ------------------------------- the learning items -------------------------------


def test_a_deleted_learning_item_disappears(session: Session) -> None:
    """A soft-deleted learning item is gone from the list."""
    item = _learning_item(session)
    learning_service.soft_delete(session, item, NOW)
    assert learning_service.get_item(session, item.id) is None
    assert item not in learning_service.list_items(session)
    assert learning_service.get_item(session, item.id, include_deleted=True) is not None


def test_the_learning_page_deletes_an_item(client: TestClient, session: Session) -> None:
    """The delete button of a learning item removes it."""
    item = _learning_item(session)
    response = client.post(f"/learning/{item.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert learning_service.get_item(session, item.id) is None


def test_the_learning_page_deletes_the_selection(client: TestClient, session: Session) -> None:
    """The bulk action of the learning page removes every item of the selection."""
    first = _learning_item(session, "کتاب اول")
    second = _learning_item(session, "کتاب دوم")
    third = _learning_item(session, "کتاب سوم")
    response = client.post(
        "/learning/delete",
        data={"item_ids": [str(first.id), str(second.id)]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert learning_service.get_item(session, first.id) is None
    assert learning_service.get_item(session, second.id) is None
    assert learning_service.get_item(session, third.id) is not None


def test_the_learning_page_offers_the_selection(client: TestClient, session: Session) -> None:
    """The learning page holds the checkboxes and the bulk action."""
    _learning_item(session)
    response = client.get("/learning")
    assert response.status_code == 200
    assert "deleteAll('/learning/delete', 'item_ids')" in response.text


# ------------------------------- the achievements -------------------------------


def test_the_achievement_page_deletes_an_item(client: TestClient, session: Session) -> None:
    """The delete button of an achievement removes it."""
    achievement = achievement_service.create_achievement(
        session,
        title="تحویل نسخهٔ اول",
        period_start=dt.date(2024, 8, 1),
        period_end=dt.date(2024, 8, 31),
    )
    response = client.post(f"/achievements/{achievement.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert achievement_service.get_achievement(session, achievement.id) is None


def test_the_achievement_page_deletes_the_selection(
    client: TestClient, session: Session
) -> None:
    """The bulk action of the achievements page removes the selection."""
    first = achievement_service.create_achievement(
        session,
        title="اول",
        period_start=dt.date(2024, 8, 1),
        period_end=dt.date(2024, 8, 31),
    )
    second = achievement_service.create_achievement(
        session,
        title="دوم",
        period_start=dt.date(2024, 8, 1),
        period_end=dt.date(2024, 8, 31),
    )
    response = client.post(
        "/achievements/delete",
        data={"achievement_ids": [str(first.id), str(second.id)]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert achievement_service.get_achievement(session, first.id) is None
    assert achievement_service.get_achievement(session, second.id) is None


# ------------------------------- the reviews -------------------------------


def test_the_review_page_deletes_a_review(client: TestClient, session: Session) -> None:
    """The delete button of a review removes it."""
    review = _review(session)
    response = client.post(f"/reviews/{review.id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert review_service.get_review(session, review.id) is None


def test_the_review_page_deletes_the_selection(client: TestClient, session: Session) -> None:
    """The bulk action of the reviews page removes the selection."""
    first = _review(session)
    second = _review(session)
    response = client.post(
        "/reviews/delete",
        data={"review_ids": [str(first.id), str(second.id)]},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert review_service.get_review(session, first.id) is None
    assert review_service.get_review(session, second.id) is None


def test_the_rating_shows_its_scale(client: TestClient, session: Session) -> None:
    """The rating of a review is shown with the scale it belongs to."""
    review = _review(session)
    review_service.update_review(session, review, user_final_md="یک ماه خوب بود.", rating=4)
    response = client.get("/reviews")
    assert response.status_code == 200
    assert "۴ از ۵" in response.text


def test_a_finished_review_can_be_viewed(client: TestClient, session: Session) -> None:
    """The read-only view of a review shows the final text, without the form."""
    review = _review(session)
    review_service.update_review(session, review, user_final_md="یک ماه خوب بود.", rating=4)
    response = client.get(f"/reviews/{review.id}?view=1")
    assert response.status_code == 200
    assert "یک ماه خوب بود." in response.text
    assert "textarea" not in response.text


def test_the_review_page_offers_the_selection(client: TestClient, session: Session) -> None:
    """The reviews page holds the checkboxes and the bulk action."""
    _review(session)
    response = client.get("/reviews")
    assert response.status_code == 200
    assert "deleteAll('/reviews/delete', 'review_ids')" in response.text


# ------------------------------- the tasks -------------------------------


def test_the_task_page_offers_the_selection(client: TestClient, session: Session) -> None:
    """The task page holds the checkboxes and the bulk action."""
    _task(session)
    response = client.get("/tasks")
    assert response.status_code == 200
    assert "deleteAll('/tasks/delete', 'task_ids')" in response.text
