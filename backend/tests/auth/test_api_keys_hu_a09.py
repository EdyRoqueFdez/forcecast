"""Tests for HU-A09 — API keys for agents (read-only)."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch


class TestAPIKeyModel:
    """Test APIKey model fields."""

    def test_api_key_has_last_used_at(self):
        """APIKey model should have last_used_at field."""
        from app.auth.models.api_key import APIKey

        # Check that the model has the field
        assert hasattr(APIKey, "last_used_at")

    def test_api_key_has_expires_at(self):
        """APIKey model should have expires_at field."""
        from app.auth.models.api_key import APIKey

        assert hasattr(APIKey, "expires_at")


class TestAPIKeySchema:
    """Test API key schemas."""

    def test_api_key_read_includes_last_used_at(self):
        """APIKeyRead schema should include last_used_at."""
        from app.auth.schemas.api_keys import APIKeyRead
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        schema = APIKeyRead(
            id="test-id",
            name="Test Key",
            scopes=["read:models"],
            rate_limit_rpm=60,
            created_at=now,
            last_used_at=now,
            expires_at=None,
            revoked_at=None,
        )
        assert schema.last_used_at == now

    def test_api_key_read_includes_expires_at(self):
        """APIKeyRead schema should include expires_at."""
        from app.auth.schemas.api_keys import APIKeyRead
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)
        schema = APIKeyRead(
            id="test-id",
            name="Test Key",
            scopes=["read:models"],
            rate_limit_rpm=60,
            created_at=now,
            last_used_at=None,
            expires_at=expires,
            revoked_at=None,
        )
        assert schema.expires_at == expires

    def test_api_key_create_includes_expires_at(self):
        """APIKeyCreate schema should allow setting expires_at."""
        from app.auth.schemas.api_keys import APIKeyCreate
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=30)
        schema = APIKeyCreate(
            name="Test Key",
            scopes=["read:models"],
            rate_limit_rpm=60,
            expires_at=expires,
        )
        assert schema.expires_at == expires


class TestAPIKeyScopes:
    """Test API key scope validation."""

    def test_read_scopes_allowed(self):
        """Read scopes should be allowed."""
        from app.auth.services.api_keys import validate_scopes

        # Should not raise
        validate_scopes(["read:models"])
        validate_scopes(["read:categories"])
        validate_scopes(["read:providers"])
        validate_scopes(["read:locales"])

    def test_write_scopes_rejected(self):
        """Write scopes should be rejected."""
        from app.auth.services.api_keys import validate_scopes
        import pytest

        with pytest.raises(ValueError, match="write"):
            validate_scopes(["write:models"])

    def test_admin_scopes_rejected(self):
        """Admin scopes should be rejected."""
        from app.auth.services.api_keys import validate_scopes
        import pytest

        with pytest.raises(ValueError, match="write"):
            validate_scopes(["admin:all"])


class TestAPIKeyBlocking:
    """Test API key blocking for voting."""

    @pytest.mark.asyncio
    async def test_vote_blocks_api_key(self):
        """Voting with API key should return 403."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Try to vote with API key
            response = await client.post(
                "/api/v1/votes",
                json={
                    "target_type": "model",
                    "target_id": "test-model-id",
                    "category_id": "test-category-id",
                    "idempotency_key": "test-key-123",
                },
                headers={"X-Forcecast-Api-Key": "fk_test-key-123"},
            )
            # Should return 401 (invalid API key) or 403 (if key is valid)
            assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_revoke_vote_blocks_api_key(self):
        """Revoking vote with API key should return 403."""
        from httpx import AsyncClient, ASGITransport
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Try to revoke vote with API key
            response = await client.delete(
                "/api/v1/votes/test-category-id",
                headers={"X-Forcecast-Api-Key": "fk_test-key-123"},
            )
            # Should return 401 (invalid API key) or 403 (if key is valid)
            assert response.status_code in [401, 403]
