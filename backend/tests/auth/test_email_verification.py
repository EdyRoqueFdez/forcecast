"""Tests for email verification service — HU-A03."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta, timezone


class TestEmailVerificationService:
    """Tests for EmailVerificationService."""

    @pytest.mark.asyncio
    async def test_generate_token(self):
        """Test token generation."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        token = await service.generate_token("user123")

        assert token is not None
        assert len(token) > 0
        assert "email_verify:" + token in redis_dict

    @pytest.mark.asyncio
    async def test_verify_token_valid(self):
        """Test valid token verification."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        token = await service.generate_token("user123")
        user_id = await service.verify_token(token)

        assert user_id == "user123"

    @pytest.mark.asyncio
    async def test_verify_token_used(self):
        """Test token cannot be used twice."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        token = await service.generate_token("user123")
        await service.verify_token(token)
        user_id = await service.verify_token(token)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_verify_token_expired(self):
        """Test expired token verification."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        token = await service.generate_token("user123")
        
        # Manually expire the token
        key = f"email_verify:{token}"
        data = redis_dict[key]
        data["expires_at"] = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        redis_dict[key] = data

        user_id = await service.verify_token(token)

        assert user_id is None

    @pytest.mark.asyncio
    async def test_verify_token_invalid(self):
        """Test invalid token verification."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        user_id = await service.verify_token("invalid-token")

        assert user_id is None

    @pytest.mark.asyncio
    async def test_can_resend(self):
        """Test can resend verification email."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        can_resend = await service.can_resend("user123")

        assert can_resend is True

    @pytest.mark.asyncio
    async def test_can_resend_rate_limited(self):
        """Test rate limiting for resend."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        # Simulate 3 resends
        for _ in range(3):
            await service.record_resend("user123")

        can_resend = await service.can_resend("user123")

        assert can_resend is False

    @pytest.mark.asyncio
    async def test_record_resend(self):
        """Test recording resend attempt."""
        from app.auth.services.email_verification import EmailVerificationService

        redis_dict = {}
        service = EmailVerificationService(redis_client=redis_dict)

        await service.record_resend("user123")
        await service.record_resend("user123")

        key = "email_resend:user123"
        assert redis_dict[key] == 2


class TestEmailService:
    """Tests for EmailService."""

    @pytest.mark.asyncio
    async def test_send_verification(self):
        """Test sending verification email."""
        from app.auth.services.email import EmailService

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response

        with patch("app.auth.services.email.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = "test-key"
            mock_settings.EMAIL_FROM = "test@example.com"
            mock_settings.FRONTEND_URL = "http://localhost:5173"

            with patch("httpx.AsyncClient") as mock_httpx:
                mock_httpx.return_value.__aenter__.return_value = mock_client

                service = EmailService()
                result = await service.send_verification("user@example.com", "test-token")

        assert result is True
        mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_verification_no_api_key(self):
        """Test sending verification email without API key."""
        from app.auth.services.email import EmailService

        with patch("app.auth.services.email.settings") as mock_settings:
            mock_settings.RESEND_API_KEY = ""

            service = EmailService()
            result = await service.send_verification("user@example.com", "test-token")

        assert result is False
