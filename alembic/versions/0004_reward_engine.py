"""The tables of the reward engine.

Revision ID: 0004_reward_engine
Revises: 0003_learning_soft_delete
Create Date: 2026-11-27

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_reward_engine"
down_revision: str | None = "0003_learning_soft_delete"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the medals, the titles, the orders, the quests and the realms."""
    op.add_column(
        "reviews",
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
    )

    op.add_column(
        "tasks",
        sa.Column("is_private", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "tasks",
        sa.Column(
            "counts_for_medals", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )

    op.create_table(
        "medals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("muster_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="SET NULL")),
        sa.Column(
            "achievement_id",
            sa.Integer(),
            sa.ForeignKey("achievements.id", ondelete="SET NULL"),
        ),
        sa.Column("tier", sa.String(length=20), nullable=False),
        sa.Column("virtue", sa.String(length=20), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False, server_default="earned"),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("domains.id", ondelete="SET NULL")),
        sa.Column("month_key", sa.String(length=10), nullable=False),
        sa.Column("value_raw", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("value_counted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "awarded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_medals_month_key", "medals", ["month_key"])
    op.create_index("ix_medals_virtue", "medals", ["virtue"])
    op.create_index("ix_medals_domain_id", "medals", ["domain_id"])

    op.create_table(
        "medal_evidence",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "medal_id", sa.Integer(), sa.ForeignKey("medals.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column(
            "task_id", sa.Integer(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False
        ),
        sa.UniqueConstraint("task_id", name="uq_medal_evidence_task"),
    )

    op.create_table(
        "title_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title_key", sa.String(length=30), nullable=False),
        sa.Column(
            "reached_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("vigil", postgresql.JSONB(astext_type=sa.Text())),
    )
    op.create_index("ix_title_history_title_key", "title_history", ["title_key"])

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_key", sa.String(length=30), nullable=False),
        sa.Column(
            "earned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("order_key", name="uq_orders_key"),
    )

    op.create_table(
        "quests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("month_key", sa.String(length=10), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("medal_id", sa.Integer(), sa.ForeignKey("medals.id", ondelete="SET NULL")),
    )
    op.create_index("ix_quests_month_key", "quests", ["month_key"])

    op.create_table(
        "realm_claims",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("realm_key", sa.String(length=40), nullable=False),
        sa.Column("domain_id", sa.Integer(), sa.ForeignKey("domains.id", ondelete="SET NULL")),
        sa.Column("castles_lit", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("assigned_at", sa.DateTime(timezone=True)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("realm_key", name="uq_realm_claims_key"),
    )

    op.create_table(
        "saga_chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "review_id", sa.Integer(), sa.ForeignKey("reviews.id", ondelete="CASCADE")
        ),
        sa.Column("volume_key", sa.String(length=40), nullable=False),
        sa.Column("body_md", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "facts", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"
        ),
        sa.Column("edited", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_saga_chapters_volume_key", "saga_chapters", ["volume_key"])


def downgrade() -> None:
    """Remove the tables of the reward engine."""
    op.drop_index("ix_saga_chapters_volume_key", table_name="saga_chapters")
    op.drop_table("saga_chapters")
    op.drop_table("realm_claims")
    op.drop_index("ix_quests_month_key", table_name="quests")
    op.drop_table("quests")
    op.drop_table("orders")
    op.drop_index("ix_title_history_title_key", table_name="title_history")
    op.drop_table("title_history")
    op.drop_table("medal_evidence")
    op.drop_index("ix_medals_domain_id", table_name="medals")
    op.drop_index("ix_medals_virtue", table_name="medals")
    op.drop_index("ix_medals_month_key", table_name="medals")
    op.drop_table("medals")
    op.drop_column("tasks", "counts_for_medals")
    op.drop_column("tasks", "is_private")
    op.drop_column("reviews", "status")
