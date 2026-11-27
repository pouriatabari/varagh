"""The honours of the hall.

The medals, the degrees, the titles, the orders and the quests live in
the database; the rules that count them live in
:mod:`app.services.rewards` and the numbers in ``config/rewards.yaml``.

The honours are given by the musters. Nothing here creates an honour by
hand: a medal is written when a muster confirms its proposals.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.review import Achievement, Review
from app.models.rewards import Medal, MedalEvidence, Order, Quest, RealmClaim, TitleHistory
from app.models.task import Domain, Task
from app.services import court, rewards
from app.services.rewards_config import VIRTUES, RewardsConfig
from app.utils.jalali import jalali_of
from app.utils.time import utcnow


@dataclass(frozen=True)
class MedalProposal:
    """A medal the muster proposes, with the evidence that backs it."""

    title: str
    virtue: str
    tier: str
    domain_name: str | None = None
    evidence_task_ids: tuple[int, ...] = ()
    impact_note: str | None = None
    concrete: bool = False
    confidence: float = 0.0
    description_md: str = ""


@dataclass(frozen=True)
class AwardResult:
    """What a muster gave."""

    medals: list[Medal]
    created: list[Medal]
    skipped: list[str]


def month_key(day: date) -> str:
    """The key of a Jalali month, e.g. ``1404/01``."""
    jalali = jalali_of(day)
    return f"{jalali.year:04d}/{jalali.month:02d}"


def list_medals(session: Session) -> list[Medal]:
    """Return the medals, oldest first."""
    query = select(Medal).order_by(Medal.awarded_at.asc(), Medal.id.asc())
    return list(session.scalars(query).all())


def medal_records(session: Session, medals: Sequence[Medal]) -> list[rewards.MedalRecord]:
    """Turn the medals of the database into the records of the engine."""
    records = []
    for medal in medals:
        records.append(
            rewards.MedalRecord(
                tier=medal.tier,
                virtue=medal.virtue,
                value_counted=medal.value_counted,
                month_key=medal.month_key,
                domain_key=domain_key_of(session, medal),
            )
        )
    return records


def reached_titles(session: Session) -> list[str]:
    """The titles that were reached, oldest first."""
    rows = session.scalars(select(TitleHistory).order_by(TitleHistory.reached_at.asc())).all()
    return [row.title_key for row in rows]


def claimed_realms(session: Session) -> list[RealmClaim]:
    """The realms that were claimed."""
    rows = session.scalars(
        select(RealmClaim).where(RealmClaim.claimed_at.isnot(None))
    ).all()
    return list(rows)


def title_state(session: Session, config: RewardsConfig) -> rewards.TitleState:
    """Where the user stands with the titles."""
    medals = list_medals(session)
    musters = (
        session.scalar(
            select(func.count())
            .select_from(Review)
            .where(Review.status == "finished")
        )
        or 0
    )
    fiefs = len(claimed_realms(session))
    return rewards.title_state(
        medals=medal_records(session, medals),
        musters=musters,
        reached_titles=reached_titles(session),
        fiefs=fiefs,
        config=config,
    )


def _domain_for(session: Session, name: str | None) -> Domain | None:
    """Find a domain by its name, when the proposal names one."""
    if not name:
        return None
    return session.scalars(select(Domain).where(Domain.name == name)).first()


def _used_evidence_ids(session: Session) -> set[int]:
    """The tasks that already back a medal."""
    rows = session.scalars(select(MedalEvidence.task_id)).all()
    return set(rows)


def award_medals(
    session: Session,
    *,
    review: Review | None,
    proposals: Sequence[MedalProposal],
    config: RewardsConfig,
    now: datetime | None = None,
) -> AwardResult:
    """Give the medals of a muster.

    The evidence is checked first: the tasks must exist, be finished, be
    allowed to count and not back another medal. The tier is clamped to
    what the evidence proves, and the value is counted with the cap and
    the diminishing returns of the Jalali month of the muster.
    """
    stamp = now or utcnow()
    day = review.period_end if review is not None else stamp.date()
    key = month_key(day)

    used = _used_evidence_ids(session)
    created: list[Medal] = []
    skipped: list[str] = []

    for proposal in proposals:
        evidence = _check_evidence(session, proposal, used)
        if isinstance(evidence, str):
            skipped.append(f"{proposal.title}: {evidence}")
            continue
        domain = _domain_for(session, proposal.domain_name)
        tier = rewards.clamped_tier(
            proposal.tier,
            task_count=len(evidence),
            has_impact_note=bool(proposal.impact_note),
            concrete=proposal.concrete,
            config=config,
        )
        medal = Medal(
            muster_id=review.id if review is not None else None,
            tier=tier,
            virtue=proposal.virtue if proposal.virtue in VIRTUES else "prowess",
            kind="earned",
            domain_id=domain.id if domain is not None else None,
            month_key=key,
            value_raw=config.tier_value(tier),
            value_counted=0,
            awarded_at=stamp,
        )
        session.add(medal)
        session.flush()
        for task_id in evidence:
            session.add(MedalEvidence(medal_id=medal.id, task_id=task_id))
            used.add(task_id)
        created.append(medal)
    session.flush()

    recount_month(session, key, config)
    return AwardResult(
        medals=list_medals(session), created=created, skipped=skipped
    )


def _check_evidence(
    session: Session, proposal: MedalProposal, used: set[int]
) -> list[int] | str:
    """Check the evidence of a proposal: the ids, or the reason it fails."""
    if not proposal.evidence_task_ids:
        return "no evidence"
    tasks = list(
        session.scalars(
            select(Task).where(Task.id.in_(list(proposal.evidence_task_ids)))
        ).all()
    )
    found = {task.id for task in tasks}
    missing = [task_id for task_id in proposal.evidence_task_ids if task_id not in found]
    if missing:
        return f"unknown tasks: {missing}"
    for task in tasks:
        if task.status != "done":
            return f"the task {task.id} is not finished"
        if not task.counts_for_medals:
            return f"the task {task.id} does not count for the medals"
        if task.id in used:
            return f"the task {task.id} already backs a medal"
    return list(proposal.evidence_task_ids)


def recount_month(session: Session, key: str, config: RewardsConfig) -> None:
    """Count the value of the medals of a month again.

    The cap and the diminishing returns belong to the month, so every
    medal of the month is counted together, in the order of the ceremony.
    """
    medals = list(
        session.scalars(
            select(Medal)
            .where(Medal.month_key == key)
            .order_by(Medal.awarded_at.asc(), Medal.id.asc())
        ).all()
    )
    if not medals:
        return
    awards = []
    for medal in medals:
        awards.append(
            rewards.MedalAward(
                tier=medal.tier,
                virtue=medal.virtue,
                month_key=medal.month_key,
                value_raw=medal.value_raw,
                domain_key=domain_key_of(session, medal),
                kind=medal.kind,
            )
        )
    counted = rewards.count_awards(awards, config)
    for medal, value in zip(medals, counted.counted, strict=True):
        medal.value_counted = value
    session.flush()


def domain_key_of(session: Session, medal: Medal) -> str | None:
    """The key of the domain of a medal: its name, when it has one."""
    if medal.domain_id is None:
        return None
    domain = session.get(Domain, medal.domain_id)
    return domain.name if domain is not None else None


def list_orders(session: Session) -> list[Order]:
    """The orders that were earned."""
    return list(session.scalars(select(Order).order_by(Order.earned_at.asc())).all())


def list_quests(session: Session, month: str | None = None) -> list[Quest]:
    """The quests of a month, or of every month."""
    query = select(Quest).order_by(Quest.month_key.desc(), Quest.id.desc())
    if month is not None:
        query = query.where(Quest.month_key == month)
    return list(session.scalars(query).all())


def reach_title(
    session: Session, title_key: str, vigil: dict[str, Any] | None = None
) -> TitleHistory:
    """Write down a title that was reached.

    A title is never taken back: the row stays, and the vigil of the
    ceremony stays with it.
    """
    row = session.scalars(
        select(TitleHistory).where(TitleHistory.title_key == title_key)
    ).first()
    if row is not None:
        return row
    row = TitleHistory(title_key=title_key, vigil=vigil or {})
    session.add(row)
    session.flush()
    return row


def medals_of_review(session: Session, review_id: int) -> list[Medal]:
    """The medals a muster gave."""
    rows = session.scalars(
        select(Medal).where(Medal.muster_id == review_id).order_by(Medal.id.asc())
    ).all()
    return list(rows)


def achievement_of_medal(session: Session, medal: Medal) -> Achievement | None:
    """The record a medal came from, when it has one."""
    if medal.achievement_id is None:
        return None
    return session.get(Achievement, medal.achievement_id)


def top_domains(session: Session, limit: int = 3) -> list[str]:
    """The domains the user works in most, by the medals that counted."""
    rows = session.execute(
        select(Medal.domain_id, func.count(Medal.id))
        .where(Medal.domain_id.isnot(None), Medal.value_counted > 0)
        .group_by(Medal.domain_id)
        .order_by(func.count(Medal.id).desc())
    ).all()
    names = []
    for domain_id, _count in rows:
        domain = session.get(Domain, domain_id)
        if domain is not None:
            names.append(domain.name)
    return names[:limit]


def virtue_counts(session: Session) -> dict[str, int]:
    """The counted medals of every virtue."""
    rows = session.execute(
        select(Medal.virtue, func.count(Medal.id))
        .where(Medal.value_counted > 0)
        .group_by(Medal.virtue)
    ).all()
    return {virtue: int(count) for virtue, count in rows}


def court_tiers(session: Session, config: RewardsConfig) -> list[court.CourtTier]:
    """The tiers of the pyramid, from the page at the bottom to the king."""
    state = title_state(session, config)
    reached = set(state.reached)
    tiers = []
    for rule in config.titles:
        tiers.append(
            court.CourtTier(
                key=rule.key,
                reached=rule.key in reached,
                current=rule.key == state.current,
                next=rule.key == state.next_title,
            )
        )
    return tiers


def seats(session: Session) -> list[court.Seat]:
    """The six seats of the round table, with the medals of each virtue."""
    counts = virtue_counts(session)
    highest = max(counts.values(), default=0)
    seats = []
    for virtue in court.VIRTUE_ORDER:
        count = counts.get(virtue, 0)
        share = (count / highest) if highest else 0.0
        seats.append(court.Seat(virtue=virtue, count=count, share=share))
    return seats
