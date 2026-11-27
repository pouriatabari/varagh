"""Soft-delete the learning items.

Revision ID: 0003_learning_soft_delete
Revises: 0002_notification_delivery
Create Date: 2026-11-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_learning_soft_delete"
down_revision: str | None = "0002_notification_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the deletion marker of a learning item."""
    op.add_column(
        "learning_items",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove the deletion marker again."""
    op.drop_column("learning_items", "deleted_at")
