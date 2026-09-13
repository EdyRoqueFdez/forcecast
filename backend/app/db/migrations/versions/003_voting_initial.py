"""Voting initial schema — vote_events, user_votes, audit_logs.

Revision ID: 003_voting_initial
Revises: 002_taxonomy_initial
Create Date: 2026-09-12
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_voting_initial"
down_revision: Union[str, None] = "002_taxonomy_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # vote_events — append-only vote log
    op.create_table(
        "vote_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column(
            "category_id",
            sa.String(length=36),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "taxonomy_version",
            sa.String(length=50),
            sa.ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(10, 4),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "idempotency_key",
            sa.String(length=255),
            nullable=False,
            unique=True,
        ),
        sa.Column("device_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # Constraints
        sa.CheckConstraint(
            "target_type IN ('model', 'orchestrator')",
            name="ck_vote_events_target_type",
        ),
        sa.CheckConstraint(
            "action IN ('vote', 'change', 'revoke')",
            name="ck_vote_events_action",
        ),
        sa.CheckConstraint(
            "weight >= 0",
            name="ck_vote_events_weight_nonneg",
        ),
    )

    # Indexes for vote_events
    op.create_index("idx_vote_events_user", "vote_events", ["user_id"])
    op.create_index(
        "idx_vote_events_target",
        "vote_events",
        ["target_type", "target_id"],
    )
    op.create_index(
        "idx_vote_events_category", "vote_events", ["category_id"]
    )
    op.create_index(
        "idx_vote_events_created", "vote_events", ["created_at"]
    )

    # Append-only rules (PostgreSQL only)
    op.execute(
        """
        CREATE RULE vote_events_no_update AS
            ON UPDATE TO vote_events DO INSTEAD NOTHING;
        """
    )
    op.execute(
        """
        CREATE RULE vote_events_no_delete AS
            ON DELETE TO vote_events DO INSTEAD NOTHING;
        """
    )

    # user_votes — materialized current vote state
    op.create_table(
        "user_votes",
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "category_id",
            sa.String(length=36),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=50), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column(
            "weight",
            sa.Numeric(10, 4),
            nullable=False,
            server_default=sa.text("1.0"),
        ),
        sa.Column(
            "vote_event_id",
            sa.String(length=36),
            sa.ForeignKey("vote_events.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # Composite primary key
        sa.PrimaryKeyConstraint(
            "user_id", "category_id", "target_type",
            name="pk_user_votes",
        ),
        # Constraints
        sa.CheckConstraint(
            "target_type IN ('model', 'orchestrator')",
            name="ck_user_votes_target_type",
        ),
        sa.CheckConstraint(
            "weight >= 0",
            name="ck_user_votes_weight_nonneg",
        ),
    )

    # Indexes for user_votes
    op.create_index(
        "idx_user_votes_target",
        "user_votes",
        ["target_type", "target_id"],
    )
    op.create_index("idx_user_votes_user", "user_votes", ["user_id"])

    # audit_logs — append-only audit trail
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "actor_id",
            sa.String(length=36),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=36), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("request_id", sa.String(length=255), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    # Indexes for audit_logs
    op.create_index("idx_audit_logs_actor", "audit_logs", ["actor_id"])
    op.create_index(
        "idx_audit_logs_entity",
        "audit_logs",
        ["entity_type", "entity_id"],
    )
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index(
        "idx_audit_logs_created", "audit_logs", ["created_at"]
    )

    # Append-only rules (PostgreSQL only)
    op.execute(
        """
        CREATE RULE audit_logs_no_update AS
            ON UPDATE TO audit_logs DO INSTEAD NOTHING;
        """
    )
    op.execute(
        """
        CREATE RULE audit_logs_no_delete AS
            ON DELETE TO audit_logs DO INSTEAD NOTHING;
        """
    )


def downgrade() -> None:
    # Drop tables in reverse order (respect FKs)
    op.execute("DROP RULE IF EXISTS audit_logs_no_delete ON audit_logs")
    op.execute("DROP RULE IF EXISTS audit_logs_no_update ON audit_logs")
    op.drop_table("audit_logs")

    op.drop_table("user_votes")

    op.execute("DROP RULE IF EXISTS vote_events_no_delete ON vote_events")
    op.execute("DROP RULE IF EXISTS vote_events_no_update ON vote_events")
    op.drop_table("vote_events")
