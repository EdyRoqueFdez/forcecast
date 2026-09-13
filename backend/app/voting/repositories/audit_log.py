"""AuditLogRepository — append-only data access for audit logs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.voting.models.audit_log import AuditLog


class AuditLogRepository:
    """Data access for audit_logs table (append-only)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: dict) -> AuditLog:
        """Create a new audit log entry (append-only)."""
        log = AuditLog(**data)
        self.session.add(log)
        await self.session.flush()
        return log

    async def list_by_actor(self, actor_id: str) -> list[AuditLog]:
        """List all audit logs for an actor."""
        result = await self.session.execute(
            select(AuditLog)
            .where(AuditLog.actor_id == actor_id)
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_entity(
        self, entity_type: str, entity_id: str
    ) -> list[AuditLog]:
        """List all audit logs for an entity."""
        result = await self.session.execute(
            select(AuditLog)
            .where(
                AuditLog.entity_type == entity_type,
                AuditLog.entity_id == entity_id,
            )
            .order_by(AuditLog.created_at.desc())
        )
        return list(result.scalars().all())
