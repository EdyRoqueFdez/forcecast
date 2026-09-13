"""Add comment field to vote_events — HU-V03.

Revision ID: 008_vote_comment
Revises: 007_orchestrator_categories
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008_vote_comment"
down_revision: Union[str, None] = "007_orchestrator_categories"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "vote_events",
        sa.Column("comment", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("vote_events", "comment")
