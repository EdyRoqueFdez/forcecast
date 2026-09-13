"""Tests for Turnstile integration — HU-A08 CAPTCHA."""

from unittest.mock import AsyncMock, patch, MagicMock
import pytest


class TestTurnstileMiddleware:
    """Tests for Turnstile middleware."""

    @pytest.mark.asyncio
    async def test_verify_turnstile_token_valid(self):
        """Test valid Turnstile token verification."""
        from app.auth.middleware.turnstile import verify_turnstile_token

        mock_response = MagicMock()
        mock_response.json.return_value = {"success": True}

        mock_post = AsyncMock(return_value=mock_response)
        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_client_instance
        mock_context_manager.__aexit__.return_value = False

        with patch("app.auth.middleware.turnstile.httpx.AsyncClient", return_value=mock_context_manager), \
             patch("app.auth.middleware.turnstile.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = "test-secret-key"
            result = await verify_turnstile_token("valid-token", "127.0.0.1")

        assert result is True
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_verify_turnstile_token_invalid(self):
        """Test invalid Turnstile token verification."""
        from app.auth.middleware.turnstile import verify_turnstile_token

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "success": False,
            "error-codes": ["invalid-input-response"],
        }

        mock_post = AsyncMock(return_value=mock_response)
        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        mock_context_manager = AsyncMock()
        mock_context_manager.__aenter__.return_value = mock_client_instance
        mock_context_manager.__aexit__.return_value = False

        with patch("app.auth.middleware.turnstile.httpx.AsyncClient", return_value=mock_context_manager), \
             patch("app.auth.middleware.turnstile.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = "test-secret-key"
            result = await verify_turnstile_token("invalid-token", "127.0.0.1")

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_turnstile_token_exception(self):
        """Test Turnstile verification handles exceptions."""
        from app.auth.middleware.turnstile import verify_turnstile_token

        with patch("app.auth.middleware.turnstile.httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = Exception("Network error")
            result = await verify_turnstile_token("token", "127.0.0.1")

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_turnstile_token_no_secret_key(self):
        """Test Turnstile verification with missing secret key."""
        from app.auth.middleware.turnstile import verify_turnstile_token

        with patch("app.auth.middleware.turnstile.settings") as mock_settings:
            mock_settings.TURNSTILE_SECRET_KEY = ""
            result = await verify_turnstile_token("token", "127.0.0.1")

        assert result is False


class TestBurstDetection:
    """Tests for BurstDetector."""

    @pytest.mark.asyncio
    async def test_is_burst_no_votes(self):
        """Test burst detection with no votes."""
        from app.voting.services.burst_detection import BurstDetector

        detector = BurstDetector(redis_client={})
        result = await detector.is_burst("user123")

        assert result is False

    @pytest.mark.asyncio
    async def test_is_burst_below_threshold(self):
        """Test burst detection below threshold."""
        from app.voting.services.burst_detection import BurstDetector

        import time

        redis_dict = {"vote_burst:user123": [time.time()]}
        detector = BurstDetector(redis_client=redis_dict)
        result = await detector.is_burst("user123", threshold=3)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_burst_above_threshold(self):
        """Test burst detection above threshold."""
        from app.voting.services.burst_detection import BurstDetector

        import time

        now = time.time()
        redis_dict = {
            "vote_burst:user123": [now, now - 1, now - 2]  # 3 votes in 3 seconds
        }
        detector = BurstDetector(redis_client=redis_dict)
        result = await detector.is_burst("user123", threshold=3)

        assert result is True

    @pytest.mark.asyncio
    async def test_record_vote(self):
        """Test recording a vote."""
        from app.voting.services.burst_detection import BurstDetector

        redis_dict = {}
        detector = BurstDetector(redis_client=redis_dict)

        await detector.record_vote("user123")

        assert "vote_burst:user123" in redis_dict
        assert len(redis_dict["vote_burst:user123"]) == 1
        # Timestamp should be recent
        import time
        assert redis_dict["vote_burst:user123"][0] > time.time() - 1

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing burst data."""
        from app.voting.services.burst_detection import BurstDetector

        redis_dict = {"vote_burst:user123": [1.0, 2.0, 3.0]}
        detector = BurstDetector(redis_client=redis_dict)

        await detector.clear("user123")

        assert "vote_burst:user123" not in redis_dict


class TestFeatureFlags:
    """Tests for FeatureFlags service."""

    @pytest.mark.asyncio
    async def test_is_enabled_local_config(self):
        """Test feature flag from local config."""
        from app.core.feature_flags import FeatureFlags

        with patch("app.core.feature_flags.settings") as mock_settings:
            mock_settings.FEATURE_CAPTCHA_REGISTRATION = True
            ff = FeatureFlags(posthog_client=None)
            result = await ff.is_enabled("FEATURE_CAPTCHA_REGISTRATION")

        assert result is True

    @pytest.mark.asyncio
    async def test_is_enabled_default(self):
        """Test feature flag default value."""
        from app.core.feature_flags import FeatureFlags

        with patch("app.core.feature_flags.settings") as mock_settings:
            # Remove the attribute
            if hasattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION"):
                delattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION")
            ff = FeatureFlags(posthog_client=None)
            result = await ff.is_enabled("FEATURE_CAPTCHA_REGISTRATION", default=False)

        assert result is False

    @pytest.mark.asyncio
    async def test_is_enabled_posthog_success(self):
        """Test feature flag from PostHog."""
        from app.core.feature_flags import FeatureFlags

        mock_client = MagicMock()
        mock_client.feature_enabled.return_value = True

        with patch("app.core.feature_flags.settings") as mock_settings:
            if hasattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION"):
                delattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION")
            ff = FeatureFlags(posthog_client=mock_client)
            result = await ff.is_enabled("FEATURE_CAPTCHA_REGISTRATION", user_id="user123")

        assert result is True
        mock_client.feature_enabled.assert_called_once()

    @pytest.mark.asyncio
    async def test_is_enabled_posthog_exception(self):
        """Test feature flag handles PostHog exceptions."""
        from app.core.feature_flags import FeatureFlags

        mock_client = MagicMock()
        mock_client.feature_enabled.side_effect = Exception("PostHog error")

        with patch("app.core.feature_flags.settings") as mock_settings:
            if hasattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION"):
                delattr(mock_settings, "FEATURE_CAPTCHA_REGISTRATION")
            ff = FeatureFlags(posthog_client=mock_client)
            result = await ff.is_enabled("FEATURE_CAPTCHA_REGISTRATION", default=False)

        assert result is False
