"""Reputation service — calculate and update user reputation."""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


class ReputationService:
    """Calculate and update user reputation."""

    # Default values (can be overridden by config)
    BASE_REPUTATION = 1.0
    MAX_TENURE_SCORE = 2.0
    MAX_VOTES_SCORE = 2.0
    CONSISTENCY_BONUS = 0.5
    REPORT_PENALTY = 0.5
    MIN_REPUTATION = 0.1
    BOT_THRESHOLD = 0.5

    def __init__(self, db: AsyncSession | None = None):
        self.db = db

    async def calculate_reputation(self, user: Any) -> float:
        """Calculate user's reputation score.

        Formula: base + tenure + votes + consistency - reports
        """
        tenure = await self._tenure_score(user)
        votes = await self._votes_score(user)
        consistency = await self._consistency_score(user)
        reports = await self._reports_penalty(user)

        reputation = self.BASE_REPUTATION + tenure + votes + consistency - reports
        return max(reputation, self.MIN_REPUTATION)

    async def _tenure_score(self, user: Any) -> float:
        """Score based on account age (max 2.0)."""
        created_at = getattr(user, "created_at", None)
        if not created_at:
            return 0.0

        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        days = (datetime.now(timezone.utc) - created_at).days
        return min(days / 365, self.MAX_TENURE_SCORE)

    async def _votes_score(self, user: Any) -> float:
        """Score based on votes cast (max 2.0)."""
        if not self.db:
            return 0.0

        try:
            from app.voting.models.user_vote import UserVote

            result = await self.db.execute(
                select(func.count(UserVote.id)).where(UserVote.user_id == user.id)
            )
            votes_count = result.scalar() or 0
            return min(votes_count / 50, self.MAX_VOTES_SCORE)
        except Exception as e:
            logger.warning(f"votes_score error: {e}")
            return 0.0

    async def _consistency_score(self, user: Any) -> float:
        """Bonus for regular voting patterns (0.5 if voted in 7+ of last 30 days)."""
        if not self.db:
            return 0.0

        try:
            from app.voting.models.vote_event import VoteEvent

            thirty_days_ago = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            ) - __import__("datetime").timedelta(days=30)

            result = await self.db.execute(
                select(func.count(func.distinct(func.date(VoteEvent.created_at)))).where(
                    VoteEvent.user_id == user.id,
                    VoteEvent.created_at >= thirty_days_ago,
                )
            )
            active_days = result.scalar() or 0
            return self.CONSISTENCY_BONUS if active_days >= 7 else 0.0
        except Exception as e:
            logger.warning(f"consistency_score error: {e}")
            return 0.0

    async def _reports_penalty(self, user: Any) -> float:
        """Penalty for reports received."""
        if not self.db:
            return 0.0

        try:
            from app.voting.models.audit_log import AuditLog

            result = await self.db.execute(
                select(func.count(AuditLog.id)).where(
                    AuditLog.actor_id == user.id,
                    AuditLog.action == "report.received",
                )
            )
            reports_count = result.scalar() or 0
            return reports_count * self.REPORT_PENALTY
        except Exception as e:
            logger.warning(f"reports_penalty error: {e}")
            return 0.0

    def get_vote_weight(self, reputation: float) -> float:
        """Calculate vote weight from reputation.

        Weight = max(reputation, 0.1)
        """
        return max(reputation, self.MIN_REPUTATION)

    def is_bot_like(self, reputation: float) -> bool:
        """Check if reputation indicates bot behavior."""
        return reputation < self.BOT_THRESHOLD

    async def update_user_reputation(self, user: Any) -> float:
        """Calculate and update user's reputation in database.

        Returns new reputation score.
        """
        new_reputation = await self.calculate_reputation(user)

        # Update user object
        user.reputation_score = round(new_reputation, 2)

        # Persist if we have a db session
        if self.db:
            try:
                await self.db.commit()
            except Exception as e:
                logger.warning(f"reputation update commit error: {e}")

        return new_reputation
