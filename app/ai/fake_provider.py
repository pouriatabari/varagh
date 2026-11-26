"""A provider that answers from a script; used by the tests and offline demos."""

from __future__ import annotations

from typing import Any

from app.ai.provider import AIError

DEFAULT_ANSWERS: dict[str, dict[str, Any]] = {
    "parse_quick_add": {
        "title": "تسک نمونه",
        "due_at": None,
        "priority": 2,
        "context": "personal",
        "origin": "self_initiated",
        "assigned_by": None,
        "effort_minutes_estimate": None,
        "note_md": "",
    },
    "parse_daily_journal": {
        "entries": [{"text": "کار روی گزارش", "minutes": 60, "kind": "work", "task_id": None}],
        "summary_fa": "یک روز کاری معمولی.",
    },
    "classify_task": {"domains": ["کار"]},
    "parse_syllabus": {"units": ["فصل اول", "فصل دوم"]},
    "daily_plan": {
        "plan": [{"title": "کار روی تسک اول", "task_id": None, "minutes": 60, "note_fa": ""}],
        "summary_fa": "برنامه سبکی برای امروز.",
    },
    "review_draft": {
        "achievements_technical": [],
        "achievements_work": [],
        "comparison": "",
        "bottlenecks": [],
        "suggestions": [],
        "narrative_fa": "دورهٔ آرامی بود.",
    },
    "ask_my_data": {"answer_fa": "پاسخ نمونه.", "used_task_ids": [], "used_dates": []},
}


class FakeAIProvider:
    """A provider that returns canned answers and records the calls."""

    name = "fake"

    def __init__(self, answers: dict[str, dict[str, Any]] | None = None) -> None:
        self.answers = {**DEFAULT_ANSWERS, **(answers or {})}
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.model = "fake-model"

    def complete_json(self, feature: str, system: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Return the canned answer of the feature."""
        self.calls.append((feature, payload))
        if feature not in self.answers:
            raise AIError(f"the fake provider has no answer for {feature}")
        answer = self.answers[feature]
        if isinstance(answer, Exception):
            raise answer
        return answer
