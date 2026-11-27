"""The realms of the map and the rules that give them.

The data of the realms is static: ``data/realms.json`` holds every realm
with its name, its legend, the ground it covers and the realms that
touch it. The state of a realm — the fog, the progress, the claim — is
computed from the database: the medals of the domain of the realm light
its castles.

A realm is never given by hand: it is assigned to a domain by the user,
and only next to a realm that is already assigned or claimed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.rewards import Medal, Order, RealmClaim
from app.models.task import Domain
from app.utils.time import utcnow

# The states of a realm on the map.
STATE_FOG = "fog"
STATE_PROGRESS = "progress"
STATE_CLAIMED = "claimed"
STATE_HIDDEN = "hidden"

# The order that opens the hidden realm.
SCHOLAR_ORDER = "scholar"


@dataclass(frozen=True)
class Realm:
    """A realm of the map, as it is written in the data file."""

    key: str
    name_fa: str
    name_en: str
    legend_fa: str
    coverage_fa: str
    coverage_en: str
    themes: tuple[str, ...]
    adjacent: tuple[str, ...]
    hidden: bool
    start: bool
    castles: int


@dataclass(frozen=True)
class RealmState:
    """The state of a realm, as the map shows it."""

    realm: Realm
    state: str
    castles_lit: int = 0
    domain_id: int | None = None
    domain_name: str | None = None
    assigned_at: datetime | None = None
    claimed_at: datetime | None = None

    @property
    def key(self) -> str:
        """The key of the realm."""
        return self.realm.key


def _candidate_paths() -> list[Path]:
    """The places the data file may live in."""
    paths = [Path(get_settings().data_dir) / "realms.json"]
    paths.append(Path(__file__).resolve().parents[2] / "data" / "realms.json")
    return paths


@lru_cache(maxsize=1)
def load_realms() -> dict[str, Realm]:
    """Read the realms of the map.

    The file is read once and kept: the realms of the map do not change
    while the app runs.
    """
    for path in _candidate_paths():
        if not path.exists():
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        castles = int(payload.get("castles", 3))
        realms: dict[str, Realm] = {}
        for item in payload.get("realms", []):
            realm = Realm(
                key=str(item["key"]),
                name_fa=str(item.get("name_fa", "")),
                name_en=str(item.get("name_en", "")),
                legend_fa=str(item.get("legend_fa", "")),
                coverage_fa=str(item.get("coverage_fa", "")),
                coverage_en=str(item.get("coverage_en", "")),
                themes=tuple(str(theme) for theme in item.get("themes", ())),
                adjacent=tuple(str(key) for key in item.get("adjacent", ())),
                hidden=bool(item.get("hidden", False)),
                start=bool(item.get("start", False)),
                castles=castles,
            )
            realms[realm.key] = realm
        if realms:
            return realms
    return {}


def realm_list() -> list[Realm]:
    """Every realm of the map, in the order of the data file."""
    return list(load_realms().values())


def realm_of(key: str) -> Realm | None:
    """The realm of a key, when it is a realm of the map."""
    return load_realms().get(key)


def start_realm() -> Realm | None:
    """The realm every user begins with."""
    for realm in load_realms().values():
        if realm.start:
            return realm
    return None


def hidden_realms() -> list[Realm]:
    """The realms that stay hidden until their order is earned."""
    return [realm for realm in load_realms().values() if realm.hidden]


def claims(session: Session) -> dict[str, RealmClaim]:
    """The claims of the database, by the key of the realm."""
    rows = session.scalars(select(RealmClaim)).all()
    return {row.realm_key: row for row in rows}


def claim_of_domain(session: Session, domain_id: int) -> RealmClaim | None:
    """The claim of a domain, when the domain has a realm."""
    row = session.scalars(
        select(RealmClaim).where(RealmClaim.domain_id == domain_id)
    ).first()
    return row


def has_scholar_order(session: Session) -> bool:
    """Whether the order of the scholar is earned."""
    row = session.scalars(
        select(Order).where(Order.order_key == SCHOLAR_ORDER)
    ).first()
    return row is not None


def counted_medals_of_domain(session: Session, domain_id: int) -> int:
    """The number of the counted medals of a domain."""
    return int(
        session.scalar(
            select(func.count(Medal.id)).where(
                Medal.domain_id == domain_id, Medal.value_counted > 0
            )
        )
        or 0
    )


def state_of(session: Session, realm: Realm) -> RealmState:
    """The state of one realm."""
    claim = claims(session).get(realm.key)
    if realm.hidden and not has_scholar_order(session):
        return RealmState(realm=realm, state=STATE_HIDDEN)
    if claim is None:
        return RealmState(realm=realm, state=STATE_FOG)
    domain = None
    if claim.domain_id is not None:
        domain = session.get(Domain, claim.domain_id)
    state = STATE_CLAIMED if claim.claimed_at is not None else STATE_PROGRESS
    return RealmState(
        realm=realm,
        state=state,
        castles_lit=int(claim.castles_lit or 0),
        domain_id=claim.domain_id,
        domain_name=domain.name if domain is not None else None,
        assigned_at=claim.assigned_at,
        claimed_at=claim.claimed_at,
    )


def states(session: Session) -> list[RealmState]:
    """The state of every realm of the map."""
    return [state_of(session, realm) for realm in realm_list()]


def assigned_keys(session: Session) -> set[str]:
    """The realms that are already assigned or claimed."""
    return {
        key
        for key, claim in claims(session).items()
        if claim.assigned_at is not None or claim.claimed_at is not None
    }


def assignable_realms(session: Session) -> list[Realm]:
    """The realms a domain may take.

    A realm may only be taken next to a realm that is already assigned
    or claimed, and the hidden realms stay closed until their order is
    earned.
    """
    taken = assigned_keys(session)
    scholar = has_scholar_order(session)
    candidates = []
    for realm in load_realms().values():
        if realm.key in taken:
            continue
        if realm.hidden and not scholar:
            continue
        if not taken:
            # The first realm of the map is the start realm.
            if realm.start:
                candidates.append(realm)
            continue
        if any(neighbour in taken for neighbour in realm.adjacent):
            candidates.append(realm)
    return candidates


def assign_realm(session: Session, realm_key: str, domain_id: int) -> RealmClaim:
    """Give a realm to a domain.

    The rule of the map is checked here: the realm must be free, it must
    touch a realm that is already assigned or claimed, and it must not be
    one of the hidden realms while the order is not earned.
    """
    realm = realm_of(realm_key)
    if realm is None:
        raise ValueError("unknown realm")
    if realm_key not in {item.key for item in assignable_realms(session)}:
        raise ValueError("the realm may not be taken here")
    domain = session.get(Domain, domain_id)
    if domain is None:
        raise ValueError("unknown domain")
    existing = claim_of_domain(session, domain_id)
    if existing is not None:
        raise ValueError("the domain already has a realm")
    claim = RealmClaim(
        realm_key=realm.key,
        domain_id=domain.id,
        castles_lit=0,
        assigned_at=utcnow(),
    )
    session.add(claim)
    session.flush()
    sync_castles(session, domain.id)
    return claim


def assign_start_realm(session: Session, domain_id: int) -> RealmClaim | None:
    """Give the start realm to the first domain that earned a medal.

    The map begins empty, so the first realm of the map is the one that
    is given; the rule of the neighbours applies from the next one on.
    """
    if assigned_keys(session):
        return None
    realm = start_realm()
    if realm is None:
        return None
    domain = session.get(Domain, domain_id)
    if domain is None:
        return None
    claim = RealmClaim(
        realm_key=realm.key,
        domain_id=domain.id,
        castles_lit=0,
        assigned_at=utcnow(),
    )
    session.add(claim)
    session.flush()
    return claim


def sync_castles(session: Session, domain_id: int) -> RealmClaim | None:
    """Light the castles of the realm of a domain.

    Every counted medal of the domain lights the next castle of its
    realm; the third one claims the realm. The castles are counted from
    the medals every time, so the count never drifts.
    """
    claim = claim_of_domain(session, domain_id)
    if claim is None:
        return None
    counted = counted_medals_of_domain(session, domain_id)
    realm = realm_of(claim.realm_key)
    castles = realm.castles if realm is not None else 3
    claim.castles_lit = min(counted, castles)
    if claim.castles_lit >= castles and claim.claimed_at is None:
        claim.claimed_at = utcnow()
    session.flush()
    return claim


def campaign_route(session: Session) -> list[str]:
    """The realms that were claimed, in the order they were claimed."""
    rows = session.scalars(
        select(RealmClaim)
        .where(RealmClaim.claimed_at.isnot(None))
        .order_by(RealmClaim.claimed_at.asc(), RealmClaim.id.asc())
    ).all()
    return [row.realm_key for row in rows]
