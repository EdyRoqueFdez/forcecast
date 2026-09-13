"""VoteService unit tests."""

from __future__ import annotations

import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User
from app.taxonomy.models.entities import AIModel, Category, TaxonomyVersion
from app.taxonomy.services.core import DomainError
from app.voting.repositories.vote_event import VoteEventRepository
from app.voting.repositories.user_vote import UserVoteRepository
from app.voting.services.vote_service import VoteService


@pytest.mark.asyncio
class TestCastVote:
    """Tests for VoteService.cast_vote()."""

    async def test_cast_vote_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Successful vote cast."""
        service = VoteService(db_session)

        result = await service.cast_vote(
            user=test_user,
            target_type="model",
            target_id=test_model.id,
            category_id=test_category.id,
            idempotency_key=str(uuid.uuid4()),
        )

        assert result["action"] == "vote"
        assert result["target_type"] == "model"
        assert result["target_id"] == test_model.id
        assert result["category_id"] == test_category.id
        assert result["user_id"] == test_user.id

    async def test_cast_vote_idempotent(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Same idempotency key returns existing event."""
        service = VoteService(db_session)
        key = str(uuid.uuid4())

        result1 = await service.cast_vote(
            user=test_user,
            target_type="model",
            target_id=test_model.id,
            category_id=test_category.id,
            idempotency_key=key,
        )

        result2 = await service.cast_vote(
            user=test_user,
            target_type="model",
            target_id=test_model.id,
            category_id=test_category.id,
            idempotency_key=key,
        )

        assert result1["id"] == result2["id"]

    async def test_cast_vote_unverified_email(
        self,
        db_session: AsyncSession,
        test_user_unverified: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Unverified email raises 403."""
        service = VoteService(db_session)

        with pytest.raises(DomainError) as exc_info:
            await service.cast_vote(
                user=test_user_unverified,
                target_type="model",
                target_id=test_model.id,
                category_id=test_category.id,
                idempotency_key=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 403
        assert "Email verification required" in exc_info.value.message

    async def test_cast_vote_bot_detected(
        self,
        db_session: AsyncSession,
        test_user_bot: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Bot signals raise 403."""
        service = VoteService(db_session)

        with pytest.raises(DomainError) as exc_info:
            await service.cast_vote(
                user=test_user_bot,
                target_type="model",
                target_id=test_model.id,
                category_id=test_category.id,
                idempotency_key=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 403
        assert "Bot signals detected" in exc_info.value.message

    async def test_cast_vote_unapproved_model(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """Voting on unapproved model raises 403."""
        # Create draft model
        model = AIModel(
            id=str(uuid.uuid4()),
            provider_id=str(uuid.uuid4()),
            slug="draft-model",
            display_name="Draft Model",
            status="draft",
            source="manual",
            source_payload_hash="draft-hash",
            modality=["text"],
        )
        db_session.add(model)
        await db_session.commit()

        service = VoteService(db_session)

        with pytest.raises(DomainError) as exc_info:
            await service.cast_vote(
                user=test_user,
                target_type="model",
                target_id=model.id,
                category_id=test_category.id,
                idempotency_key=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 403
        assert "Model not votable" in exc_info.value.message


@pytest.mark.asyncio
class TestChangeVote:
    """Tests for VoteService.change_vote()."""

    async def test_change_vote_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Successful vote change."""
        service = VoteService(db_session)

        # Cast initial vote
        await service.cast_vote(
            user=test_user,
            target_type="model",
            target_id=test_model.id,
            category_id=test_category.id,
            idempotency_key=str(uuid.uuid4()),
        )

        # Create second model
        model2 = AIModel(
            id=str(uuid.uuid4()),
            provider_id=str(uuid.uuid4()),
            slug="model-2",
            display_name="Model 2",
            status="approved",
            source="manual",
            source_payload_hash="hash-2",
            modality=["text"],
        )
        db_session.add(model2)
        await db_session.commit()

        # Change vote
        result = await service.change_vote(
            user=test_user,
            target_type="model",
            target_id=model2.id,
            category_id=test_category.id,
            idempotency_key=str(uuid.uuid4()),
        )

        assert result["action"] == "change"
        assert result["target_id"] == model2.id

    async def test_change_vote_no_active_vote(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Change vote with no active vote raises 404."""
        service = VoteService(db_session)

        with pytest.raises(DomainError) as exc_info:
            await service.change_vote(
                user=test_user,
                target_type="model",
                target_id=test_model.id,
                category_id=test_category.id,
                idempotency_key=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 404
        assert "No active vote" in exc_info.value.message


@pytest.mark.asyncio
class TestRevokeVote:
    """Tests for VoteService.revoke_vote()."""

    async def test_revoke_vote_success(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_model: AIModel,
        test_category: Category,
    ):
        """Successful vote revocation."""
        service = VoteService(db_session)

        # Cast initial vote
        await service.cast_vote(
            user=test_user,
            target_type="model",
            target_id=test_model.id,
            category_id=test_category.id,
            idempotency_key=str(uuid.uuid4()),
        )

        # Revoke vote
        result = await service.revoke_vote(
            user=test_user,
            target_type="model",
            category_id=test_category.id,
            idempotency_key=str(uuid.uuid4()),
        )

        assert result["action"] == "revoke"
        assert result["weight"] == 0

    async def test_revoke_vote_no_active_vote(
        self,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """Revoke with no active vote raises 404."""
        service = VoteService(db_session)

        with pytest.raises(DomainError) as exc_info:
            await service.revoke_vote(
                user=test_user,
                target_type="model",
                category_id=test_category.id,
                idempotency_key=str(uuid.uuid4()),
            )

        assert exc_info.value.status_code == 404
        assert "No active vote" in exc_info.value.message
