"""AuditService — append-only audit logging (RG-07)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.voting.repositories.audit_log import AuditLogRepository


class AuditService:
    """Service for creating audit log entries."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = AuditLogRepository(session)

    async def log(
        self,
        actor_id: str,
        action: str,
        entity_type: str,
        entity_id: str | None = None,
        details: dict[str, Any] | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Create an audit log entry.

        Args:
            actor_id: ID of the user performing the action.
            action: Action name (e.g., 'vote.cast', 'user.login').
            entity_type: Type of entity (e.g., 'vote', 'model').
            entity_id: ID of the entity (optional).
            details: Additional details (optional).
            request_id: Request ID for tracing (optional).
            ip_address: Client IP address (optional).
            user_agent: Client user agent (optional).
        """
        await self.repo.create(
            {
                "actor_id": actor_id,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "details": details,
                "request_id": request_id,
                "ip_address": ip_address,
                "user_agent": user_agent,
            }
        )
