"""Add domain tables — HU-T05.

Revision ID: 006_domains
Revises: 005_orchestrators
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006_domains"
down_revision: Union[str, None] = "005_orchestrators"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # domains
    op.create_table(
        "domains",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("parent_id", sa.String(length=36), sa.ForeignKey("domains.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug", name="uq_domains_slug"),
    )
    op.create_index("idx_domains_slug", "domains", ["slug"])
    op.create_index("idx_domains_status", "domains", ["status"])

    # domain_translations
    op.create_table(
        "domain_translations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "domain_id",
            sa.String(length=36),
            sa.ForeignKey("domains.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("locale", sa.String(length=10), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "domain_id", "locale",
            name="uq_domain_translations_domain_locale",
        ),
    )
    op.create_index(
        "idx_domain_translations_domain",
        "domain_translations",
        ["domain_id"],
    )


def downgrade() -> None:
    op.drop_table("domain_translations")
    op.drop_table("domains")
