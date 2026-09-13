"""UserVoteRepository — data access for materialized vote state."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.voting.models.user_vote import UserVote


class UserVoteRepository:
    """Data access for user_votes table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        user_id: str,
        category_id: str,
        target_type: str,
    ) -> UserVote | None:
        """Get user's active vote in a category for a target type."""
        result = await self.session.execute(
            select(UserVote).where(
                UserVote.user_id == user_id,
                UserVote.category_id == category_id,
                UserVote.target_type == target_type,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[UserVote]:
        """List all active votes for a user."""
        result = await self.session.execute(
            select(UserVote)
            .where(UserVote.user_id == user_id)
            .order_by(UserVote.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_target(
        self, target_type: str, target_id: str
    ) -> list[UserVote]:
        """List all votes for a target."""
        result = await self.session.execute(
            select(UserVote).where(
                UserVote.target_type == target_type,
                UserVote.target_id == target_id,
            )
        )
        return list(result.scalars().all())

    async def count_by_target(
        self, target_type: str, target_id: str
    ) -> int:
        """Count votes for a target."""
        votes = await self.list_by_target(target_type, target_id)
        return len(votes)

    async def create(self, data: dict) -> UserVote:
        """Create a new user vote."""
        vote = UserVote(**data)
        self.session.add(vote)
        await self.session.flush()
        return vote

    async def update(self, vote: UserVote, data: dict) -> UserVote:
        """Update an existing user vote."""
        for key, value in data.items():
            setattr(vote, key, value)
        await self.session.flush()
        return vote

    async def delete(self, vote: UserVote) -> None:
        """Delete a user vote."""
        await self.session.delete(vote)
        await self.session.flush()
