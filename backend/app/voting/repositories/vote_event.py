"""VoteEventRepository — append-only data access for vote events."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.voting.models.vote_event import VoteEvent


class VoteEventRepository:
    """Data access for vote_events table (append-only)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, event_id: str) -> VoteEvent | None:
        """Get vote event by ID."""
        result = await self.session.execute(
            select(VoteEvent).where(VoteEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def get_by_idempotency_key(self, key: str) -> VoteEvent | None:
        """Get vote event by idempotency key."""
        result = await self.session.execute(
            select(VoteEvent).where(VoteEvent.idempotency_key == key)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> list[VoteEvent]:
        """List all vote events for a user."""
        result = await self.session.execute(
            select(VoteEvent)
            .where(VoteEvent.user_id == user_id)
            .order_by(VoteEvent.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_target(
        self, target_type: str, target_id: str
    ) -> list[VoteEvent]:
        """List all vote events for a target."""
        result = await self.session.execute(
            select(VoteEvent)
            .where(
                VoteEvent.target_type == target_type,
                VoteEvent.target_id == target_id,
            )
            .order_by(VoteEvent.created_at.desc())
        )
        return list(result.scalars().all())

    async def create(self, data: dict) -> VoteEvent:
        """Create a new vote event (append-only)."""
        event = VoteEvent(**data)
        self.session.add(event)
        await self.session.flush()
        return event
