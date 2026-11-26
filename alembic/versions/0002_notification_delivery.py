"""Track when a browser notification was delivered to the page.

Revision ID: 0002_notification_delivery
Revises: 0001_initial
Create Date: 2026-11-26

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_notification_delivery"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the delivery marker used by the browser channel."""
    op.add_column(
        "notification_log",
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_log",
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )
    op.create_index(
        "ix_notification_log_channel",
        "notification_log",
        ["channel"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the delivery marker again."""
    op.drop_index("ix_notification_log_channel", table_name="notification_log")
    op.drop_column("notification_log", "payload")
    op.drop_column("notification_log", "delivered_at")
