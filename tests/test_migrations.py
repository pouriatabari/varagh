"""Migration up/down smoke test — run against the isolated test database."""

from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command
from app.models import Base

REPO_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_TABLES = {
    "tasks",
    "domains",
    "task_domains",
    "time_entries",
    "task_notes",
    "board_items",
    "daily_journal",
    "achievements",
    "achievement_tasks",
    "reviews",
    "learning_items",
    "learning_units",
    "learning_logs",
    "settings",
    "notification_log",
    "ai_runs",
}


def _config() -> Config:
    url = os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    if url:
        config.set_main_option("sqlalchemy.url", url)
    return config


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_migrations_upgrade_and_downgrade() -> None:
    """The schema can be dropped and rebuilt from scratch, in both directions."""
    config = _config()
    url = config.get_main_option("sqlalchemy.url")
    assert url

    # Start from a completely empty database.
    engine = create_engine(url)
    try:
        Base.metadata.drop_all(engine)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS alembic_version"))
    finally:
        engine.dispose()

    command.upgrade(config, "head")
    tables = _tables(url)
    assert EXPECTED_TABLES.issubset(tables)
    assert "alembic_version" in tables

    command.downgrade(config, "base")
    tables = _tables(url)
    assert not (EXPECTED_TABLES & tables)

    command.upgrade(config, "head")
    assert EXPECTED_TABLES.issubset(_tables(url))
