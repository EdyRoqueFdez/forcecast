"""Add orchestrator tables — HU-T08.

Revision ID: 005_orchestrators
Revises: 004_user_profile
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005_orchestrators"
down_revision: Union[str, None] = "004_user_profile"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # orchestrators
    op.create_table(
        "orchestrators",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=100), nullable=True),
        sa.Column("maintainer", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=500), nullable=True),
        sa.Column("repo_url", sa.String(length=500), nullable=True),
        sa.Column("license", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_orchestrators_slug"),
    )
    op.create_index("idx_orchestrators_slug", "orchestrators", ["slug"])
    op.create_index("idx_orchestrators_status", "orchestrators", ["status"])

    # orchestrator_translations
    op.create_table(
        "orchestrator_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "orchestrator_id",
            sa.String(length=36),
            sa.ForeignKey("orchestrators.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "orchestrator_id", "locale",
            name="uq_orchestrator_translations_orchestrator_locale",
        ),
    )
    op.create_index(
        "idx_orchestrator_translations_orchestrator",
        "orchestrator_translations",
        ["orchestrator_id"],
    )

    # orchestrator_providers
    op.create_table(
        "orchestrator_providers",
        sa.Column(
            "orchestrator_id",
            sa.String(length=36),
            sa.ForeignKey("orchestrators.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "provider_id",
            sa.String(length=36),
            sa.ForeignKey("providers.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "orchestrator_id", "provider_id",
            name="uq_orchestrator_providers_orchestrator_provider",
        ),
    )


def downgrade() -> None:
    op.drop_table("orchestrator_providers")
    op.drop_table("orchestrator_translations")
    op.drop_table("orchestrators")
