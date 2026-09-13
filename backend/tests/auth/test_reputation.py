"""Tests for reputation service — HU-A07."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock


class TestReputationService:
    """Tests for ReputationService."""

    @pytest.mark.asyncio
    async def test_calculate_reputation_new_user(self):
        """Test reputation for new user."""
        from app.auth.services.reputation import ReputationService

        user = MagicMock()
        user.created_at = datetime.now(timezone.utc)
        user.id = "user123"

        service = ReputationService(db=None)
        reputation = await service.calculate_reputation(user)

        # New user: base (1.0) + tenure (~0) + votes (0) + consistency (0) - reports (0)
        assert reputation >= 1.0

    @pytest.mark.asyncio
    async def test_tenure_score(self):
        """Test tenure score calculation."""
        from app.auth.services.reputation import ReputationService

        user = MagicMock()
        user.created_at = datetime.now(timezone.utc) - timedelta(days=365)

        service = ReputationService(db=None)
        score = await service._tenure_score(user)

        # 1 year = 1.0 tenure score
        assert score == 1.0

    @pytest.mark.asyncio
    async def test_tenure_score_max(self):
        """Test tenure score max at 2.0."""
        from app.auth.services.reputation import ReputationService

        user = MagicMock()
        user.created_at = datetime.now(timezone.utc) - timedelta(days=730)

        service = ReputationService(db=None)
        score = await service._tenure_score(user)

        # 2+ years = max 2.0
        assert score == 2.0

    @pytest.mark.asyncio
    async def test_get_vote_weight(self):
        """Test vote weight calculation."""
        from app.auth.services.reputation import ReputationService

        service = ReputationService(db=None)

        # High reputation
        weight = service.get_vote_weight(2.0)
        assert weight == 2.0

        # Low reputation (minimum 0.1)
        weight = service.get_vote_weight(0.05)
        assert weight == 0.1

    @pytest.mark.asyncio
    async def test_is_bot_like(self):
        """Test bot detection."""
        from app.auth.services.reputation import ReputationService

        service = ReputationService(db=None)

        # Below threshold
        assert service.is_bot_like(0.3) is True

        # Above threshold
        assert service.is_bot_like(0.6) is False

        # At threshold
        assert service.is_bot_like(0.5) is False

    @pytest.mark.asyncio
    async def test_is_strict_mode_integration(self):
        """Test is_strict_mode with new threshold."""
        from app.auth.services.anti_bot import is_strict_mode

        user_low = MagicMock()
        user_low.reputation_score = 0.3
        assert is_strict_mode(user_low) is True

        user_high = MagicMock()
        user_high.reputation_score = 0.7
        assert is_strict_mode(user_high) is False

    @pytest.mark.asyncio
    async def test_consistency_score_no_votes(self):
        """Test consistency score with no votes."""
        from app.auth.services.reputation import ReputationService

        user = MagicMock()
        user.id = "user123"

        service = ReputationService(db=None)
        score = await service._consistency_score(user)

        # No db = no consistency bonus
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_reports_penalty_no_reports(self):
        """Test reports penalty with no reports."""
        from app.auth.services.reputation import ReputationService

        user = MagicMock()
        user.id = "user123"

        service = ReputationService(db=None)
        penalty = await service._reports_penalty(user)

        # No db = no penalty
        assert penalty == 0.0
