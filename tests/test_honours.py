"""The honours of the hall: the medals a muster gives, and only that."""

from __future__ import annotations

import datetime as dt

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.review import Review
from app.models.task import Domain, Task
from app.services import honours, rewards_config

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def finished_task(session: Session, title: str, task_id: int = 0) -> Task:
    """A task that is done and may back a medal."""
    task = Task(
        title=title,
        status="done",
        context="company",
        origin="assigned",
        created_at=NOW,
        completed_at=NOW,
    )
    session.add(task)
    session.flush()
    return task


def make_review(session: Session, end: dt.date = dt.date(2024, 8, 4)) -> Review:
    """A muster of a month."""
    review = Review(
        period_type="month",
        period_start=dt.date(2024, 7, 6),
        period_end=end,
        stats={},
        status="draft",
    )
    session.add(review)
    session.flush()
    return review


def test_the_honours_are_not_registered_by_hand(client: TestClient) -> None:
    """Nothing can be written into the hall by hand."""
    response = client.post(
        "/achievements",
        data={"title": "دستی", "period_start": "2024-08-04", "period_end": "2024-08-04"},
        follow_redirects=False,
    )
    assert response.status_code == 405


def test_the_hall_shows_the_title_and_the_gates(client: TestClient) -> None:
    """The page of the hall tells where the user stands."""
    response = client.get("/achievements")
    assert response.status_code == 200
    assert "honours.degree" not in response.text


def test_a_muster_gives_its_medals(session: Session) -> None:
    """The medals of a muster are written when the muster is confirmed."""
    config = rewards_config.load_config()
    task = finished_task(session, "کاری که تمام شد")
    review = make_review(session)
    result = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="نشان نخست",
                virtue="prowess",
                tier="bronze",
                evidence_task_ids=(task.id,),
                impact_note="اثر روشن",
            )
        ],
        config=config,
    )
    assert len(result.created) == 1
    medal = result.created[0]
    assert medal.tier == "bronze"
    assert medal.virtue == "prowess"
    assert medal.value_counted == 1
    assert medal.month_key == "1403/05"


def test_the_tier_is_lowered_when_the_evidence_is_thin(session: Session) -> None:
    """A proposal may not claim more than its evidence proves."""
    config = rewards_config.load_config()
    task = finished_task(session, "یک کار")
    review = make_review(session)
    result = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="ادعای بزرگ",
                virtue="prowess",
                tier="gold",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    assert result.created[0].tier == "bronze"


def test_a_task_cannot_back_two_medals(session: Session) -> None:
    """The evidence of a medal is used once."""
    config = rewards_config.load_config()
    task = finished_task(session, "کار مشترک")
    review = make_review(session)
    honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="نخست",
                virtue="prowess",
                tier="bronze",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    second = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="دوم",
                virtue="valor",
                tier="bronze",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    assert second.created == []
    assert "already backs a medal" in second.skipped[0]


def test_a_task_that_is_not_done_cannot_back_a_medal(session: Session) -> None:
    """Only a finished task may be evidence."""
    config = rewards_config.load_config()
    task = Task(title="ناتمام", status="doing", context="company", created_at=NOW)
    session.add(task)
    session.flush()
    review = make_review(session)
    result = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="نشان",
                virtue="prowess",
                tier="bronze",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    assert result.created == []
    assert "not finished" in result.skipped[0]


def test_a_task_that_does_not_count_cannot_back_a_medal(session: Session) -> None:
    """A task of the personal life may keep its place out of the honours."""
    config = rewards_config.load_config()
    task = finished_task(session, "کار شخصی")
    task.counts_for_medals = False
    review = make_review(session)
    result = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="نشان",
                virtue="prowess",
                tier="bronze",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    assert result.created == []
    assert "does not count" in result.skipped[0]


def test_the_month_counts_at_most_the_cap(session: Session) -> None:
    """The cap of the month holds for the medals of the musters too."""
    config = rewards_config.load_config()
    review = make_review(session)
    proposals = []
    for index in range(6):
        tasks = [finished_task(session, f"کار {index}-{part}") for part in range(3)]
        proposals.append(
            honours.MedalProposal(
                title=f"نشان {index}",
                virtue="prowess",
                tier="gold",
                domain_name=None,
                evidence_task_ids=tuple(task.id for task in tasks),
                impact_note="اثر روشن",
                concrete=True,
            )
        )
    result = honours.award_medals(
        session, review=review, proposals=proposals, config=config
    )
    assert sum(medal.value_counted for medal in result.created) == config.counting.monthly_cap


def test_the_medals_of_the_month_are_counted_again_together(session: Session) -> None:
    """A second muster of the same month shares the cap of the month."""
    config = rewards_config.load_config()
    first = make_review(session)
    tasks_a = [finished_task(session, f"کار الف-{part}") for part in range(3)]
    honours.award_medals(
        session,
        review=first,
        proposals=[
            honours.MedalProposal(
                title="نخست",
                virtue="prowess",
                tier="gold",
                evidence_task_ids=tuple(task.id for task in tasks_a),
                impact_note="اثر روشن",
                concrete=True,
            )
        ],
        config=config,
    )
    second = make_review(session)
    proposals = []
    for index in range(2):
        tasks = [finished_task(session, f"کار ب-{index}-{part}") for part in range(3)]
        proposals.append(
            honours.MedalProposal(
                title=f"دوم {index}",
                virtue="valor",
                tier="gold",
                evidence_task_ids=tuple(task.id for task in tasks),
                impact_note="اثر روشن",
                concrete=True,
            )
        )
    honours.award_medals(
        session, review=second, proposals=proposals, config=config
    )
    # The month was already at four: the medals of the second muster only
    # count what is left of the cap, and the first medal keeps its value.
    assert sum(medal.value_counted for medal in honours.list_medals(session)) == 10


def test_the_domain_of_the_proposal_is_found(session: Session) -> None:
    """The proposal names a domain; the medal keeps it."""
    config = rewards_config.load_config()
    session.add(Domain(name="شبکه"))
    session.flush()
    task = finished_task(session, "کار شبکه")
    review = make_review(session)
    result = honours.award_medals(
        session,
        review=review,
        proposals=[
            honours.MedalProposal(
                title="نشان",
                virtue="prowess",
                tier="bronze",
                domain_name="شبکه",
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    assert result.created[0].domain_id is not None


def test_the_title_is_never_lost(session: Session) -> None:
    """A title that was reached stays reached."""
    config = rewards_config.load_config()
    honours.reach_title(session, "knight", {"learned": "چیزی"})
    state = honours.title_state(session, config)
    assert state.current == "knight"
    assert "knight" in state.reached


def test_the_vigil_stays_with_the_title(session: Session) -> None:
    """The answers of the ceremony are kept."""
    honours.reach_title(session, "knight", {"learned": "چیزی"})
    row = honours.reached_titles(session)
    assert row == ["knight"]


def test_the_muster_is_confirmed_over_http(client: TestClient, session: Session) -> None:
    """Confirming a muster over the web gives the medals and closes it."""
    task = finished_task(session, "کار نخست")
    review = make_review(session)
    review.ai_draft = {
        "medal_proposals": [
            {
                "title": "نشان نخست",
                "description": "",
                "virtue": "prowess",
                "domain": "",
                "tier": "bronze",
                "evidence_task_ids": [task.id],
                "impact_note": "اثر روشن",
                "concrete": False,
                "confidence": 0.8,
                "achievement_id": None,
            }
        ]
    }
    session.flush()
    response = client.post(
        f"/reviews/{review.id}/confirm",
        data={"tier_0": "silver"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    medals = honours.list_medals(session)
    assert len(medals) == 1
    assert medals[0].tier == "bronze"
    session.refresh(review)
    assert review.status == "finished"


def test_a_muster_is_confirmed_only_once(client: TestClient, session: Session) -> None:
    """A confirmed muster gives its medals once."""
    task = finished_task(session, "کار دوم")
    review = make_review(session)
    review.ai_draft = {
        "medal_proposals": [
            {
                "title": "نشان",
                "virtue": "prowess",
                "domain": "",
                "tier": "bronze",
                "evidence_task_ids": [task.id],
                "impact_note": "",
                "concrete": False,
                "confidence": 0.5,
                "achievement_id": None,
            }
        ]
    }
    session.flush()
    client.post(f"/reviews/{review.id}/confirm", data={}, follow_redirects=False)
    client.post(f"/reviews/{review.id}/confirm", data={}, follow_redirects=False)
    assert len(honours.list_medals(session)) == 1


def test_the_worker_writes_the_draft_of_the_month(session: Session) -> None:
    """At the start of a Jalali month the draft of the last one is ready."""
    from app.worker.muster import ensure_monthly_muster

    # The second of Farvardin 1404: the muster of the month before is due.
    now = dt.datetime(2024, 3, 21, 12, 0, tzinfo=dt.UTC)
    review = ensure_monthly_muster(session, now)
    assert review is not None
    assert review.status == "draft"
    assert review.stats


def test_the_worker_does_not_write_the_draft_twice(session: Session) -> None:
    """A second tick of the worker finds the draft and leaves it alone."""
    from app.worker.muster import ensure_monthly_muster

    now = dt.datetime(2024, 3, 21, 12, 0, tzinfo=dt.UTC)
    first = ensure_monthly_muster(session, now)
    second = ensure_monthly_muster(session, now)
    assert first is not None
    assert second is not None
    assert first.id == second.id


def test_the_worker_waits_for_the_end_of_the_month(session: Session) -> None:
    """While the month runs there is no muster."""
    from app.worker.muster import ensure_monthly_muster

    now = dt.datetime(2024, 5, 10, 12, 0, tzinfo=dt.UTC)
    assert ensure_monthly_muster(session, now) is None
