"""Pytest fixtures — every test runs against the isolated ``varagh_test`` database."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import create_app
from app.models import Base
from app.security import validate_csrf


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Create the schema once per test session."""
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://varagh:varagh@db:5432/varagh_test"
    )
    test_engine = create_engine(url, pool_pre_ping=True, future=True)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture()
def session(engine: Engine) -> Iterator[Session]:
    """Provide a transactional session that is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(
        bind=connection,
        join_transaction_mode="conditional_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield db
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def app(session: Session):
    """Build the application with the test session and CSRF checks relaxed."""
    application = create_app()
    application.dependency_overrides[get_session] = lambda: session
    application.dependency_overrides[validate_csrf] = lambda: None
    return application


@pytest.fixture()
def client(app) -> Iterator[TestClient]:
    """Provide an HTTP client bound to the test application."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def now() -> datetime:
    """A fixed instant used by the tests."""
    return datetime(2024, 8, 5, 9, 0, tzinfo=UTC)
