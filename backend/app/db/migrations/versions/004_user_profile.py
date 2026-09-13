"""Add profile fields to users — bio, preferred_locale, visibility_mode.

Revision ID: 004_user_profile
Revises: 003_voting_initial
Create Date: 2026-09-13
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_user_profile"
down_revision: Union[str, None] = "003_voting_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create visibility_mode enum type
    op.execute("CREATE TYPE visibility_mode_enum AS ENUM ('pseudonym', 'public')")

    # Add new columns to users table
    op.add_column("users", sa.Column("bio", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("preferred_locale", sa.String(length=10), nullable=False, server_default="en"))
    op.add_column(
        "users",
        sa.Column(
            "visibility_mode",
            sa.Enum("pseudonym", "public", name="visibility_mode_enum"),
            nullable=False,
            server_default="pseudonym",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "visibility_mode")
    op.drop_column("users", "preferred_locale")
    op.drop_column("users", "bio")
    op.execute("DROP TYPE IF EXISTS visibility_mode_enum")
