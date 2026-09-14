"""Rate limiting service for voting operations.

Implements HU-V04: Max 10 changes per hour per user.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.voting.models.vote_event import VoteEvent


class RateLimitService:
    """Rate limiting for vote operations."""

    # Default limits
    MAX_CHANGES_PER_HOUR = 10
    MAX_VOTES_PER_MINUTE = 30

    def __init__(self, session: AsyncSession):
        self.session = session

    async def check_change_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded change rate limit.

        Args:
            user_id: User ID to check.

        Returns:
            True if within limit, False if exceeded.
        """
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        result = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.user_id == user_id,
                VoteEvent.action == "change",
                VoteEvent.created_at >= one_hour_ago,
            )
        )
        change_count = result.scalar() or 0

        return change_count < self.MAX_CHANGES_PER_HOUR

    async def check_vote_rate_limit(self, user_id: str) -> bool:
        """Check if user has exceeded vote rate limit.

        Args:
            user_id: User ID to check.

        Returns:
            True if within limit, False if exceeded.
        """
        one_minute_ago = datetime.now(UTC) - timedelta(minutes=1)

        result = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.user_id == user_id,
                VoteEvent.created_at >= one_minute_ago,
            )
        )
        vote_count = result.scalar() or 0

        return vote_count < self.MAX_VOTES_PER_MINUTE

    async def get_change_rate_limit_info(self, user_id: str) -> dict:
        """Get rate limit info for user.

        Args:
            user_id: User ID to check.

        Returns:
            Dict with rate limit info.
        """
        one_hour_ago = datetime.now(UTC) - timedelta(hours=1)

        result = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.user_id == user_id,
                VoteEvent.action == "change",
                VoteEvent.created_at >= one_hour_ago,
            )
        )
        change_count = result.scalar() or 0

        return {
            "limit": self.MAX_CHANGES_PER_HOUR,
            "remaining": max(0, self.MAX_CHANGES_PER_HOUR - change_count),
            "reset_at": (one_hour_ago + timedelta(hours=1)).isoformat(),
        }
