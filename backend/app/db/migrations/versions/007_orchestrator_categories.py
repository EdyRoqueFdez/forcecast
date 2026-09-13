"""Add orchestrator category junction table — HU-T11.

Revision ID: 007_orchestrator_categories
Revises: 006_domains
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_orchestrator_categories"
down_revision: Union[str, None] = "006_domains"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # orchestrator_categories
    op.create_table(
        "orchestrator_categories",
        sa.Column(
            "orchestrator_id",
            sa.String(length=36),
            sa.ForeignKey("orchestrators.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "category_id",
            sa.String(length=36),
            sa.ForeignKey("categories.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("taxonomy_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "orchestrator_id", "category_id",
            name="uq_orchestrator_categories_orchestrator_category",
        ),
    )


def downgrade() -> None:
    op.drop_table("orchestrator_categories")
