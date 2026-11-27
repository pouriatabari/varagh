"""The AI features, exercised with the fake provider (no network)."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.ai.fake_provider import FakeAIProvider
from app.ai.provider import AIError
from app.models.system import AIRun
from app.services import tasks as task_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def test_quick_add_draft_is_validated(session: Session) -> None:
    """A quick-add draft is validated against the strict schema."""
    provider = FakeAIProvider()
    draft = ai_service.parse_quick_add(session, provider, "فردا با علی جلسه", now=NOW)
    assert draft.title == "تسک نمونه"
    assert draft.context == "personal"
    assert provider.calls[0][0] == "parse_quick_add"


def test_an_unknown_field_is_rejected(session: Session) -> None:
    """A model answer with an unknown field is refused."""
    provider = FakeAIProvider({"parse_quick_add": {"title": "یک عنوان", "unexpected": True}})
    with pytest.raises(AIError):
        ai_service.parse_quick_add(session, provider, "متن", now=NOW)


def test_an_invalid_context_is_rejected(session: Session) -> None:
    """A model answer with an unknown context is refused."""
    provider = FakeAIProvider({"parse_quick_add": {"title": "یک عنوان", "context": "space"}})
    with pytest.raises(AIError):
        ai_service.parse_quick_add(session, provider, "متن", now=NOW)


def test_the_journal_proposal_writes_nothing(session: Session) -> None:
    """Parsing a journal proposes entries without writing them."""
    provider = FakeAIProvider()
    proposal = ai_service.parse_daily_journal(session, provider, "امروز کار کردم", now=NOW)
    assert proposal.entries
    from app.models.timing import DailyJournal

    assert session.scalars(select(DailyJournal)).all() == []


def test_the_review_draft_rejects_unknown_task_ids(session: Session) -> None:
    """A draft that cites a task it never saw is rejected."""
    provider = FakeAIProvider(
        {
            "review_draft": {
                "achievements_technical": [
                    {"title": "کار بزرگ", "description_fa": "", "task_ids": [999], "impact_fa": ""}
                ],
                "achievements_work": [],
                "comparison": "",
                "bottlenecks": [],
                "suggestions": [],
                "narrative_fa": "",
            }
        }
    )
    with pytest.raises(AIError):
        ai_service.review_draft(session, provider, {"tasks": [{"id": 1}]})


def test_the_review_draft_accepts_known_task_ids(session: Session) -> None:
    """A draft that cites known tasks is accepted."""
    provider = FakeAIProvider(
        {
            "review_draft": {
                "achievements_technical": [
                    {"title": "کار بزرگ", "description_fa": "", "task_ids": [1], "impact_fa": ""}
                ],
                "achievements_work": [],
                "comparison": "",
                "bottlenecks": [],
                "suggestions": [],
                "narrative_fa": "دورهٔ خوبی بود.",
            }
        }
    )
    draft = ai_service.review_draft(session, provider, {"tasks": [{"id": 1}]})
    assert draft.achievements_technical[0].task_ids == [1]
    assert draft.narrative_fa == "دورهٔ خوبی بود."


def test_every_call_is_logged(session: Session) -> None:
    """Each provider call is recorded in ``ai_runs``."""
    provider = FakeAIProvider()
    ai_service.parse_syllabus(session, provider, "فصل اول\nفصل دوم")
    runs = session.scalars(select(AIRun)).all()
    assert len(runs) == 1
    assert runs[0].feature == "parse_syllabus"
    assert runs[0].ok is True


def test_a_failing_call_is_logged_as_failed(session: Session) -> None:
    """A provider failure is recorded and re-raised."""
    provider = FakeAIProvider({"parse_syllabus": AIError("boom")})
    with pytest.raises(AIError):
        ai_service.parse_syllabus(session, provider, "متن")
    runs = session.scalars(select(AIRun)).all()
    assert len(runs) == 1
    assert runs[0].ok is False
    assert "boom" in (runs[0].error or "")


def test_the_daily_plan_only_uses_given_task_ids(session: Session) -> None:
    """The plan is built from the tasks of the payload."""
    provider = FakeAIProvider()
    task = task_service.create_task(session, title="تسک", now=NOW)
    payload = {"open_tasks": [{"id": task.id, "title": task.title}]}
    draft = ai_service.daily_plan(session, provider, payload)
    assert draft.plan


def test_the_ai_routes_answer_without_a_provider(client: TestClient) -> None:
    """Without a configured provider the AI routes say so."""
    response = client.get("/api/ai/daily-plan")
    assert response.status_code == 503
    assert response.json()["ok"] is False


# --- the budget of the answer ---


def test_the_budget_of_the_answer_is_clamped() -> None:
    """A budget that no model can give is brought back to what a model gives.

    A gateway that is asked for more tokens than the model can ever
    answer answers with a server error, and then every call of the app
    fails for a reason the user cannot act on.
    """
    from app.ai.anthropic_provider import MAX_OUTPUT_TOKENS, AnthropicProvider
    from app.ai.config import AIConfig

    config = AIConfig(
        enabled=True,
        provider="anthropic",
        api_key="k",
        model="m",
        max_output_tokens=200_000,
    )
    provider = AnthropicProvider(config)
    assert provider._max_tokens == MAX_OUTPUT_TOKENS

    small = AnthropicProvider(
        AIConfig(enabled=True, provider="anthropic", api_key="k", model="m",
                 max_output_tokens=4096)
    )
    assert small._max_tokens == 4096

    empty = AnthropicProvider(
        AIConfig(enabled=True, provider="anthropic", api_key="k", model="m",
                 max_output_tokens=0)
    )
    assert empty._max_tokens == 2048


def test_the_message_of_the_gateway_is_kept() -> None:
    """The words of the gateway travel with the failure."""
    from app.ai.anthropic_provider import _upstream_message

    class FakeResponse:
        status_code = 502

        @staticmethod
        def json() -> dict:
            return {"error": {"message": "does not support max tokens > 196608"}}

    assert "196608" in _upstream_message(FakeResponse())  # type: ignore[arg-type]
