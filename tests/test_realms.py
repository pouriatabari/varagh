"""The map of the realms: the states, the rule of the neighbours and the
castles that the medals light."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.rewards import Medal, Order
from app.models.task import Domain, Task
from app.services import honours, realms, rewards_config

NOW = dt.datetime(2024, 8, 5, 9, 0, tzinfo=dt.UTC)


def a_domain(session: Session, name: str = "شبکه") -> Domain:
    """A domain of the work."""
    domain = Domain(name=name)
    session.add(domain)
    session.flush()
    return domain


def a_finished_task(session: Session) -> Task:
    """A task that is done and may back a medal."""
    task = Task(
        title="کاری که تمام شد",
        status="done",
        context="company",
        origin="assigned",
        created_at=NOW,
        completed_at=NOW,
    )
    session.add(task)
    session.flush()
    return task


def a_counted_medal(session: Session, domain: Domain) -> Medal:
    """A medal that counted, in the domain."""
    medal = Medal(
        tier="bronze",
        virtue="prowess",
        kind="earned",
        domain_id=domain.id,
        month_key="1403/05",
        value_raw=1,
        value_counted=1,
        awarded_at=NOW,
    )
    session.add(medal)
    session.flush()
    return medal


def test_every_realm_of_the_map_is_there() -> None:
    """The map holds the fourteen realms and the hidden one."""
    keys = {realm.key for realm in realms.realm_list()}
    assert len(keys) == 15
    assert "lyonesse" in keys
    assert realms.realm_of("dumnonia") is not None
    assert realms.realm_of("dumnonia").start is True


def test_the_adjacency_is_symmetric() -> None:
    """Two realms that touch each other know it both ways."""
    for realm in realms.realm_list():
        for neighbour in realm.adjacent:
            other = realms.realm_of(neighbour)
            assert other is not None, neighbour
            assert realm.key in other.adjacent


def test_a_realm_is_fog_before_it_is_taken(session: Session) -> None:
    """A realm nobody has reached is covered with fog."""
    state = realms.state_of(session, realms.realm_of("dumnonia"))
    assert state.state == realms.STATE_FOG
    assert state.castles_lit == 0


def test_the_hidden_realm_stays_hidden(session: Session) -> None:
    """The hidden realm is closed until the order of the scholar is earned."""
    state = realms.state_of(session, realms.realm_of("lyonesse"))
    assert state.state == realms.STATE_HIDDEN
    assert "lyonesse" not in {realm.key for realm in realms.assignable_realms(session)}


def test_the_order_of_the_scholar_opens_the_hidden_realm(session: Session) -> None:
    """The order of the scholar gives the hidden realm."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    session.add(Order(order_key=realms.SCHOLAR_ORDER, earned_at=NOW))
    session.flush()
    state = realms.state_of(session, realms.realm_of("lyonesse"))
    assert state.state == realms.STATE_FOG
    assert "lyonesse" in {realm.key for realm in realms.assignable_realms(session)}


def test_the_first_medal_gives_the_start_realm(session: Session) -> None:
    """The first work of the user lights the first realm."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    state = realms.state_of(session, realms.realm_of("dumnonia"))
    assert state.state == realms.STATE_PROGRESS
    assert state.castles_lit == 1
    assert state.domain_name == "شبکه"


def test_the_third_castle_claims_the_realm(session: Session) -> None:
    """The third counted medal claims the realm."""
    domain = a_domain(session)
    for _ in range(3):
        a_counted_medal(session, domain)
    honours.light_realms(session)
    state = realms.state_of(session, realms.realm_of("dumnonia"))
    assert state.state == realms.STATE_CLAIMED
    assert state.castles_lit == 3


def test_a_realm_must_touch_a_taken_one(session: Session) -> None:
    """A realm may only be taken next to a realm that is already taken."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    # Caledonia touches nothing but Hadrian's Wall, which is not taken.
    assert "caledonia" not in {realm.key for realm in realms.assignable_realms(session)}
    assert "avalon" in {realm.key for realm in realms.assignable_realms(session)}
    with pytest.raises(ValueError):
        realms.assign_realm(session, "caledonia", domain.id)


def test_a_taken_realm_may_not_be_taken_again(session: Session) -> None:
    """A realm is given once."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    other = a_domain(session, "پژوهش")
    with pytest.raises(ValueError):
        realms.assign_realm(session, "dumnonia", other.id)


def test_the_road_of_the_campaign_follows_the_claims(session: Session) -> None:
    """The claimed realms stand in the order they were claimed."""
    domain = a_domain(session)
    for _ in range(3):
        a_counted_medal(session, domain)
    honours.light_realms(session)
    assert realms.campaign_route(session) == ["dumnonia"]


def test_the_map_page_shows_every_realm(client: TestClient) -> None:
    """The page of the map draws every realm of the map."""
    response = client.get("/realms")
    assert response.status_code == 200
    for realm in realms.realm_list():
        assert f'id="realm-{realm.key}"' in response.text
    assert response.text.count('data-state=') == 15


def test_the_map_page_needs_no_javascript_to_be_read(client: TestClient) -> None:
    """The table of the realms says everything the picture says."""
    response = client.get("/realms")
    assert response.status_code == 200
    assert "realms.table_title" not in response.text
    assert "قلمروها" in response.text


def test_a_realm_is_taken_over_the_web(client: TestClient, session: Session) -> None:
    """The user takes a realm from the page of the map."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    other = a_domain(session, "پژوهش")
    session.flush()
    response = client.post(
        "/realms/assign",
        data={"realm_key": "avalon", "domain_id": str(other.id)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    claim = realms.claim_of_domain(session, other.id)
    assert claim is not None
    assert claim.realm_key == "avalon"


def test_a_realm_that_may_not_be_taken_is_refused(
    client: TestClient, session: Session
) -> None:
    """The rule of the neighbours is checked on the web too."""
    domain = a_domain(session)
    a_counted_medal(session, domain)
    honours.light_realms(session)
    other = a_domain(session, "پژوهش")
    session.flush()
    response = client.post(
        "/realms/assign",
        data={"realm_key": "caledonia", "domain_id": str(other.id)},
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert "error=realms.assign_error" in response.headers["location"]
    assert realms.claim_of_domain(session, other.id) is None


def test_the_medals_of_a_muster_light_the_castles(session: Session) -> None:
    """A medal given by a muster lights a castle of the realm."""
    config = rewards_config.load_config()
    domain = a_domain(session)
    task = a_finished_task(session)
    honours.award_medals(
        session,
        review=None,
        proposals=[
            honours.MedalProposal(
                title="نشان نخست",
                virtue="prowess",
                tier="bronze",
                domain_name=domain.name,
                evidence_task_ids=(task.id,),
            )
        ],
        config=config,
    )
    state = realms.state_of(session, realms.realm_of("dumnonia"))
    assert state.state == realms.STATE_PROGRESS
    assert state.castles_lit == 1
