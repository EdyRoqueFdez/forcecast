"""VoteEvent — append-only vote log (RG-13).

Every vote action (vote, change, revoke) is recorded here.
No UPDATE or DELETE operations are allowed.
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
    String,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class VoteEvent(Base):
    """Append-only vote event log.

    Records every vote action with full traceability.
    Enforced append-only via PostgreSQL rules (see migration).
    """

    __tablename__ = "vote_events"
    __table_args__ = (
        CheckConstraint(
            "target_type IN ('model', 'orchestrator')",
            name="ck_vote_events_target_type",
        ),
        CheckConstraint(
            "action IN ('vote', 'change', 'revoke')",
            name="ck_vote_events_action",
        ),
        CheckConstraint("weight >= 0", name="ck_vote_events_weight_nonneg"),
        Index("idx_vote_events_user", "user_id"),
        Index("idx_vote_events_target", "target_type", "target_id"),
        Index("idx_vote_events_category", "category_id"),
        Index("idx_vote_events_created", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=_uuid
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[str] = mapped_column(String(36), nullable=False)
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    taxonomy_version: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("taxonomy_versions.version", ondelete="RESTRICT"),
        nullable=False,
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("1.0")
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    device_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    previous_target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
