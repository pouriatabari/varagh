"""The charts of the AI answers."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.ai import service as ai_service
from app.ai.charts import resolve_charts, validate_charts
from app.ai.fake_provider import FakeAIProvider
from app.ai.provider import AIError
from app.ai.schemas import ChartSpec
from app.services import dashboard as dashboard_service
from app.services import settings as settings_service

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)

STATS = {
    "tasks": [{"id": 1}],
    "series": {
        "measured_minutes_by_kind": {
            "labels": ["کار عادی", "اضافه‌کاری"],
            "values": [120.0, 60.0],
            "unit": "units.minutes",
        }
    },
}


def test_a_chart_resolves_the_labels_and_the_values() -> None:
    """The model names a series; the server resolves its data."""
    charts = [ChartSpec(series="measured_minutes_by_kind", title_fa="ساعت کاری")]
    resolved = resolve_charts(charts, {"series": STATS["series"]})
    assert len(resolved) == 1
    assert resolved[0]["labels"] == ["کار عادی", "اضافه‌کاری"]
    assert resolved[0]["values"] == [120.0, 60.0]
    assert resolved[0]["title"] == "ساعت کاری"
    assert resolved[0]["basis_label"]


def test_a_chart_of_an_unknown_series_is_refused() -> None:
    """A chart may not name a series the payload does not have."""
    charts = [ChartSpec(series="invented_series")]
    with pytest.raises(AIError):
        validate_charts(charts, {"series": STATS["series"]})


def test_the_review_draft_refuses_an_unknown_series(session: Session) -> None:
    """The review draft is rejected when it charts an unknown series."""
    provider = FakeAIProvider(
        {
            "review_draft": {
                "achievements_technical": [],
                "achievements_work": [],
                "comparison": "",
                "bottlenecks": [],
                "suggestions": [],
                "narrative_fa": "",
                "charts": [{"type": "bar", "series": "made_up", "title_fa": ""}],
            }
        }
    )
    with pytest.raises(AIError):
        ai_service.review_draft(session, provider, STATS)


def test_the_review_draft_keeps_a_known_series(session: Session) -> None:
    """A chart of a known series is accepted and resolved."""
    provider = FakeAIProvider(
        {
            "review_draft": {
                "achievements_technical": [],
                "achievements_work": [],
                "comparison": "",
                "bottlenecks": [],
                "suggestions": [],
                "narrative_fa": "",
                "charts": [
                    {
                        "type": "doughnut",
                        "series": "measured_minutes_by_kind",
                        "title_fa": "ساعت کاری",
                        "basis": "measured",
                    }
                ],
            }
        }
    )
    draft = ai_service.review_draft(session, provider, STATS)
    data = ai_service.draft_to_dict(draft, ai_service.review_payload(STATS))
    assert data["charts"][0]["type"] == "doughnut"
    assert data["charts"][0]["values"] == [120.0, 60.0]


def test_the_series_are_built_out_of_the_database(session: Session) -> None:
    """The series of the personal data come from the database."""
    series = dashboard_service.build_series(session, now=NOW, timezone="Asia/Tehran", days=7)
    assert "measured_minutes_by_kind" in series
    assert "counts_by_context" in series
    assert series["measured_minutes_by_kind"]["unit"] == "units.minutes"


def test_the_chart_partial_renders_a_canvas() -> None:
    """The partial of the charts renders a canvas with its data."""
    from app.templating import templates

    charts = resolve_charts(
        [ChartSpec(series="measured_minutes_by_kind", title_fa="ساعت کاری")],
        {"series": STATS["series"]},
    )
    html = templates.get_template("partials/charts.html").render(charts=charts)
    assert "data-chart" in html
    assert "canvas" in html
    assert "ساعت کاری" in html


def test_the_ask_page_renders_without_an_ai(
    client: TestClient, session: Session
) -> None:
    """The page answers even when no provider is configured."""
    settings_service.set_setting(session, "lexicon", "plain")
    session.commit()
    response = client.post("/ask", data={"question": "این هفته چه کردم؟"})
    assert response.status_code == 200
    assert "هوش مصنوعی فعال نیست" in response.text
