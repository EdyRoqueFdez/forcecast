"""VoteService — core voting business logic.

Implements RG-08, RG-09, RG-13, RG-14, RG-29, RG-35, RG-36.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.auth.services.anti_bot import is_strict_mode
from app.reputation.services.reputation import ReputationService
from app.taxonomy.models.entities import AIModel, Category, TaxonomyVersion
from app.taxonomy.services.core import DomainError
from app.voting.models.enums import TargetType, VoteAction
from app.voting.models.user_vote import UserVote
from app.voting.repositories.user_vote import UserVoteRepository
from app.voting.repositories.vote_event import VoteEventRepository
from app.voting.services.anomaly import AnomalyDetectionService
from app.voting.services.audit_service import AuditService


class VoteService:
    """Orchestrates vote operations with business rule enforcement."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.vote_event_repo = VoteEventRepository(session)
        self.user_vote_repo = UserVoteRepository(session)
        self.audit_service = AuditService(session)
        self.reputation_service = ReputationService(session)
        self.anomaly_service = AnomalyDetectionService(session)

    async def cast_vote(
        self,
        user: User,
        target_type: str,
        target_id: str,
        category_id: str,
        idempotency_key: str,
        comment: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> dict:
        """Cast a new vote.

        Args:
            user: Authenticated user.
            target_type: 'model' or 'orchestrator'.
            target_id: ID of the target to vote for.
            category_id: ID of the category.
            idempotency_key: Unique key for idempotency.
            comment: Optional comment (0-1000 chars).
            request_id: Request ID for tracing.
            ip_address: Client IP.
            device_fingerprint: Client device fingerprint.

        Returns:
            Dict with vote event data.

        Raises:
            DomainError: On validation failure.
        """
        # Validate idempotency key
        existing = await self.vote_event_repo.get_by_idempotency_key(
            idempotency_key
        )
        if existing:
            return self._event_to_dict(existing)

        # Validate authentication (RG-03)
        self._validate_user(user)

        # Validate target type
        self._validate_target_type(target_type)

        # Validate target exists and is votable (RG-36)
        await self._validate_target(target_type, target_id)

        # Validate category
        await self._validate_category(category_id)

        # Check no active vote in category (RG-08)
        existing_vote = await self.user_vote_repo.get(
            user.id, category_id, target_type
        )
        if existing_vote:
            raise DomainError(
                "Active vote exists in this category. Use change_vote instead.",
                status_code=409,
            )

        # Get current taxonomy version (RG-35)
        taxonomy_version = await self._get_current_taxonomy_version()

        # Get vote weight based on reputation (HU-V12)
        vote_weight = await self.reputation_service.get_vote_weight(user)

        # Create vote event (append-only)
        event = await self.vote_event_repo.create(
            {
                "user_id": user.id,
                "target_type": target_type,
                "target_id": target_id,
                "category_id": category_id,
                "taxonomy_version": taxonomy_version,
                "action": VoteAction.VOTE,
                "weight": vote_weight,
                "idempotency_key": idempotency_key,
                "device_fingerprint": device_fingerprint,
                "ip_address": ip_address,
                "comment": comment,
            }
        )

        # Create materialized user vote
        await self.user_vote_repo.create(
            {
                "user_id": user.id,
                "category_id": category_id,
                "target_type": target_type,
                "target_id": target_id,
                "weight": vote_weight,
                "vote_event_id": event.id,
            }
        )

        # Audit log (RG-07)
        await self.audit_service.log(
            actor_id=user.id,
            action="vote.cast",
            entity_type="vote",
            entity_id=event.id,
            details={
                "target_type": target_type,
                "target_id": target_id,
                "category_id": category_id,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        # HU-V09: Check for anomalous voting patterns
        anomaly_result = await self.anomaly_service.detect_anomalies(user.id)
        if anomaly_result["is_anomalous"]:
            # Log anomaly detection
            await self.audit_service.log(
                actor_id=user.id,
                action="vote.anomaly_detected",
                entity_type="user",
                entity_id=user.id,
                details={
                    "anomalies": anomaly_result["anomalies"],
                    "risk_score": await self.anomaly_service.get_user_risk_score(user.id),
                },
                request_id=request_id,
                ip_address=ip_address,
            )

        await self.session.commit()
        return self._event_to_dict(event)

    async def change_vote(
        self,
        user: User,
        target_type: str,
        target_id: str,
        category_id: str,
        idempotency_key: str,
        comment: str | None = None,
        request_id: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> dict:
        """Change an existing vote (atomic -1/+1).

        Args:
            user: Authenticated user.
            target_type: 'model' or 'orchestrator'.
            target_id: New target ID.
            category_id: Category ID.
            idempotency_key: Unique key for idempotency.
            comment: Optional comment (0-1000 chars).
            request_id: Request ID for tracing.
            ip_address: Client IP.
            device_fingerprint: Client device fingerprint.

        Returns:
            Dict with vote event data.

        Raises:
            DomainError: On validation failure.
        """
        # Validate idempotency key
        existing = await self.vote_event_repo.get_by_idempotency_key(
            idempotency_key
        )
        if existing:
            return self._event_to_dict(existing)

        # Validate authentication (RG-03)
        self._validate_user(user)

        # Validate target type
        self._validate_target_type(target_type)

        # Validate target exists and is votable (RG-36)
        await self._validate_target(target_type, target_id)

        # Validate category
        await self._validate_category(category_id)

        # Check active vote exists
        existing_vote = await self.user_vote_repo.get(
            user.id, category_id, target_type
        )
        if not existing_vote:
            raise DomainError(
                "No active vote in this category. Use cast_vote instead.",
                status_code=404,
            )

        # Check not changing to same target
        if existing_vote.target_id == target_id:
            # HU-V04: Same target is idempotent, return 204 No Content
            return None  # Signal to API layer to return 204

        # Get current taxonomy version (RG-35)
        taxonomy_version = await self._get_current_taxonomy_version()

        # Get vote weight based on reputation (HU-V12)
        vote_weight = await self.reputation_service.get_vote_weight(user)

        # Create vote event (append-only)
        event = await self.vote_event_repo.create(
            {
                "user_id": user.id,
                "target_type": target_type,
                "target_id": target_id,
                "category_id": category_id,
                "taxonomy_version": taxonomy_version,
                "action": VoteAction.CHANGE,
                "weight": vote_weight,
                "idempotency_key": idempotency_key,
                "device_fingerprint": device_fingerprint,
                "ip_address": ip_address,
                "comment": comment,
            }
        )

        # Update materialized user vote (RG-09 atomic)
        await self.user_vote_repo.update(
            existing_vote,
            {
                "target_id": target_id,
                "weight": vote_weight,
                "vote_event_id": event.id,
            },
        )

        # Audit log (RG-07)
        await self.audit_service.log(
            actor_id=user.id,
            action="vote.change",
            entity_type="vote",
            entity_id=event.id,
            details={
                "target_type": target_type,
                "old_target_id": existing_vote.target_id,
                "new_target_id": target_id,
                "category_id": category_id,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        # HU-V09: Check for anomalous voting patterns
        anomaly_result = await self.anomaly_service.detect_anomalies(user.id)
        if anomaly_result["is_anomalous"]:
            # Log anomaly detection
            await self.audit_service.log(
                actor_id=user.id,
                action="vote.anomaly_detected",
                entity_type="user",
                entity_id=user.id,
                details={
                    "anomalies": anomaly_result["anomalies"],
                    "risk_score": await self.anomaly_service.get_user_risk_score(user.id),
                },
                request_id=request_id,
                ip_address=ip_address,
            )

        await self.session.commit()
        return self._event_to_dict(event)

    async def revoke_vote(
        self,
        user: User,
        target_type: str,
        category_id: str,
        idempotency_key: str,
        request_id: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> dict:
        """Revoke an active vote (RG-14).

        Args:
            user: Authenticated user.
            target_type: 'model' or 'orchestrator'.
            category_id: Category ID.
            idempotency_key: Unique key for idempotency.
            request_id: Request ID for tracing.
            ip_address: Client IP.
            device_fingerprint: Client device fingerprint.

        Returns:
            Dict with vote event data.

        Raises:
            DomainError: On validation failure.
        """
        # Validate idempotency key
        existing = await self.vote_event_repo.get_by_idempotency_key(
            idempotency_key
        )
        if existing:
            return self._event_to_dict(existing)

        # Validate authentication (RG-03)
        self._validate_user(user)

        # Validate target type
        self._validate_target_type(target_type)

        # Check active vote exists
        existing_vote = await self.user_vote_repo.get(
            user.id, category_id, target_type
        )
        if not existing_vote:
            raise DomainError(
                "No active vote in this category.",
                status_code=404,
            )

        # Get current taxonomy version (RG-35)
        taxonomy_version = await self._get_current_taxonomy_version()

        # Create vote event (append-only)
        event = await self.vote_event_repo.create(
            {
                "user_id": user.id,
                "target_type": target_type,
                "target_id": existing_vote.target_id,
                "category_id": category_id,
                "taxonomy_version": taxonomy_version,
                "action": VoteAction.REVOKE,
                "weight": Decimal("0"),
                "idempotency_key": idempotency_key,
                "device_fingerprint": device_fingerprint,
                "ip_address": ip_address,
            }
        )

        # Delete materialized user vote (RG-14)
        await self.user_vote_repo.delete(existing_vote)

        # Audit log (RG-07)
        await self.audit_service.log(
            actor_id=user.id,
            action="vote.revoke",
            entity_type="vote",
            entity_id=event.id,
            details={
                "target_type": target_type,
                "target_id": existing_vote.target_id,
                "category_id": category_id,
            },
            request_id=request_id,
            ip_address=ip_address,
        )

        await self.session.commit()
        return self._event_to_dict(event)

    async def get_user_votes(self, user: User) -> list[dict]:
        """Get all active votes for a user."""
        votes = await self.user_vote_repo.list_by_user(user.id)
        return [self._vote_to_dict(v) for v in votes]

    async def is_first_vote(self, user_id: str) -> bool:
        """Check if user has never voted before.

        Args:
            user_id: The user ID to check

        Returns:
            True if user has no votes, False otherwise
        """
        votes = await self.user_vote_repo.list_by_user(user_id)
        return len(votes) == 0

    async def get_target_votes(
        self, target_type: str, target_id: str
    ) -> dict:
        """Get vote count for a target."""
        votes = await self.user_vote_repo.list_by_target(
            target_type, target_id
        )
        total = len(votes)
        weighted = sum(float(v.weight) for v in votes)
        return {
            "target_type": target_type,
            "target_id": target_id,
            "total_votes": total,
            "weighted_score": round(weighted, 4),
        }

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _validate_user(self, user: User) -> None:
        """Validate user can vote (RG-03)."""
        if not user.email_verified:
            raise DomainError(
                "Email verification required to vote.",
                status_code=403,
            )
        if is_strict_mode(user):
            raise DomainError(
                "Bot signals detected. Voting restricted.",
                status_code=403,
            )

    def _validate_target_type(self, target_type: str) -> None:
        """Validate target type is supported."""
        try:
            TargetType(target_type)
        except ValueError:
            raise DomainError(
                f"Invalid target type: {target_type}. "
                f"Must be one of: {[t.value for t in TargetType]}",
                status_code=422,
            )

    async def _validate_target(
        self, target_type: str, target_id: str
    ) -> None:
        """Validate target exists and is votable (RG-36)."""
        if target_type == TargetType.MODEL:
            result = await self.session.execute(
                select(AIModel).where(AIModel.id == target_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                raise DomainError(
                    "Model not found.",
                    status_code=404,
                )
            if model.status != "approved":
                raise DomainError(
                    f"Model not votable. Status: {model.status}",
                    status_code=403,
                )
        # Orchestrator validation deferred to Phase 2

    async def _validate_category(self, category_id: str) -> None:
        """Validate category exists and is active."""
        result = await self.session.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        if not category:
            raise DomainError(
                "Category not found.",
                status_code=404,
            )
        if category.status != "active":
            raise DomainError(
                f"Category not active. Status: {category.status}",
                status_code=403,
            )

    async def _get_current_taxonomy_version(self) -> str:
        """Get the current taxonomy version (RG-35)."""
        result = await self.session.execute(
            select(TaxonomyVersion).where(
                TaxonomyVersion.is_current == True  # noqa: E712
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise DomainError(
                "No current taxonomy version.",
                status_code=500,
            )
        return version.version

    def _event_to_dict(self, event) -> dict:
        """Convert VoteEvent to dict."""
        return {
            "id": event.id,
            "user_id": event.user_id,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "category_id": event.category_id,
            "action": event.action,
            "weight": float(event.weight),
            "comment": getattr(event, "comment", None),
            "created_at": event.created_at.isoformat()
            if event.created_at
            else None,
        }

    def _vote_to_dict(self, vote: UserVote) -> dict:
        """Convert UserVote to dict."""
        return {
            "user_id": vote.user_id,
            "category_id": vote.category_id,
            "target_type": vote.target_type,
            "target_id": vote.target_id,
            "weight": float(vote.weight),
            "created_at": vote.created_at.isoformat()
            if vote.created_at
            else None,
            "updated_at": vote.updated_at.isoformat()
            if vote.updated_at
            else None,
        }
