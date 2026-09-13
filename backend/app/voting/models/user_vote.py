"""UserVote — materialized current vote state (RG-08).

One active vote per user per category per target_type.
Enforced by composite primary key.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    PrimaryKeyConstraint,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(UTC)


class UserVote(Base):
    """Materialized current vote state.

    Derived from vote_events. Updated atomically with vote event creation.
    Composite PK enforces one active vote per user per category per target_type.
    """

    __tablename__ = "user_votes"
    __table_args__ = (
        PrimaryKeyConstraint(
            "user_id", "category_id", "target_type",
            name="pk_user_votes",
        ),
        CheckConstraint(
            "target_type IN ('model', 'orchestrator')",
            name="ck_user_votes_target_type",
        ),
        CheckConstraint("weight >= 0", name="ck_user_votes_weight_nonneg"),
        Index("idx_user_votes_target", "target_type", "target_id"),
        Index("idx_user_votes_user", "user_id"),
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("1.0")
    )
    vote_event_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vote_events.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )
