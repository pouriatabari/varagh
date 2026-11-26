"""Database engine, session factory and FastAPI session dependency."""

from __future__ import annotations

from collections.abc import Iterator
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Return the process-wide SQLAlchemy engine."""
    settings = get_settings()
    kwargs: dict[str, object] = {"pool_pre_ping": True, "future": True}
    if settings.environment == "test":
        # Tests run in a throw-away container; keep the pool small and cheap.
        kwargs.update({"pool_size": 5, "max_overflow": 0})
    return create_engine(settings.database_url, **kwargs)  # type: ignore[arg-type]


@lru_cache(maxsize=1)
def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide session factory."""
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False, class_=Session)


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
