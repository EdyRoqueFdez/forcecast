"""ReputationService — calculates vote weight based on user reputation.

Implements HU-V12: Weight votes by reputation.
"""

from __future__ import annotations

from decimal import Decimal
from datetime import UTC, datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.voting.models.vote_event import VoteEvent


class ReputationService:
    """Calculates user reputation and vote weight."""

    # Base weight for new users
    BASE_WEIGHT = Decimal("0.5")
    # Maximum weight for verified, experienced users
    MAX_WEIGHT = Decimal("2.0")
    # Weight for detected bots/fanboys
    BOT_WEIGHT = Decimal("0.0")

    def __init__(self, session: AsyncSession):
        self.session = session

    async def calculate_reputation(self, user: User) -> Decimal:
        """Calculate user reputation based on various factors.

        Args:
            user: The user to calculate reputation for.

        Returns:
            Reputation score (0.0 to 1.0).
        """
        # Start with base reputation
        reputation = Decimal("0.5")

        # Factor 1: Account tenure (older = more trusted)
        tenure_days = self._get_tenure_days(user)
        if tenure_days > 365:
            reputation += Decimal("0.2")
        elif tenure_days > 90:
            reputation += Decimal("0.1")

        # Factor 2: Voting activity (more votes = more engaged)
        vote_count = await self._get_vote_count(user.id)
        if vote_count > 100:
            reputation += Decimal("0.2")
        elif vote_count > 20:
            reputation += Decimal("0.1")

        # Factor 3: Consistency (votes across categories)
        category_count = await self._get_category_count(user.id)
        if category_count > 5:
            reputation += Decimal("0.1")

        # Factor 4: Reports against user (penalty)
        report_count = await self._get_report_count(user.id)
        if report_count > 0:
            reputation -= Decimal("0.1") * report_count

        # Clamp between 0 and 1
        reputation = max(Decimal("0.0"), min(Decimal("1.0"), reputation))

        return reputation

    async def get_vote_weight(self, user: User) -> Decimal:
        """Calculate vote weight for a user.

        Args:
            user: The user to calculate weight for.

        Returns:
            Vote weight (0.0 to 2.0).
        """
        # Check if user is detected as bot/fanboy
        if await self._is_bot_like(user.id):
            return self.BOT_WEIGHT

        # Calculate reputation
        reputation = await self.calculate_reputation(user)

        # Map reputation to weight
        # reputation 0.0 -> weight 0.5 (base)
        # reputation 1.0 -> weight 2.0 (max)
        weight = self.BASE_WEIGHT + (reputation * (self.MAX_WEIGHT - self.BASE_WEIGHT))

        return weight

    async def _is_bot_like(self, user_id: str) -> bool:
        """Check if user exhibits bot-like behavior.

        Args:
            user_id: User ID to check.

        Returns:
            True if user appears to be a bot.
        """
        # Check for rapid-fire voting (more than 10 votes in 1 minute)
        from datetime import timedelta

        one_minute_ago = datetime.now(UTC) - timedelta(minutes=1)

        result = await self.session.execute(
            select(func.count(VoteEvent.id)).where(
                VoteEvent.user_id == user_id,
                VoteEvent.created_at >= one_minute_ago,
            )
        )
        recent_votes = result.scalar() or 0

        return recent_votes > 10

    def _get_tenure_days(self, user: User) -> int:
        """Calculate account tenure in days.

        Args:
            user: User to calculate tenure for.

        Returns:
            Number of days since account creation.
        """
        if hasattr(user, "created_at") and user.created_at:
            created_at = user.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=UTC)
            return (datetime.now(UTC) - created_at).days
        return 0

    async def _get_vote_count(self, user_id: str) -> int:
        """Get total number of votes cast by user.

        Args:
            user_id: User ID.

        Returns:
            Number of votes.
        """
        result = await self.session.execute(
            select(func.count(VoteEvent.id)).where(VoteEvent.user_id == user_id)
        )
        return result.scalar() or 0

    async def _get_category_count(self, user_id: str) -> int:
        """Get number of distinct categories user has voted in.

        Args:
            user_id: User ID.

        Returns:
            Number of distinct categories.
        """
        result = await self.session.execute(
            select(func.count(func.distinct(VoteEvent.category_id))).where(
                VoteEvent.user_id == user_id
            )
        )
        return result.scalar() or 0

    async def _get_report_count(self, user_id: str) -> int:
        """Get number of reports against user.

        Args:
            user_id: User ID.

        Returns:
            Number of reports.
        """
        from app.voting.models.report import Report

        result = await self.session.execute(
            select(func.count(Report.id)).where(
                Report.target_id == user_id,
                Report.status == "approved",
            )
        )
        return result.scalar() or 0
