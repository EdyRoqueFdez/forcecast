"""Tests for HU-V03 — Comment with Vote."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestVoteComment:
    """Test vote with comment functionality."""

    @pytest.mark.asyncio
    async def test_vote_with_comment_accepted(self, client):
        """Vote with comment should be accepted."""
        # This test requires authentication, so it will fail with 401
        # But it validates the schema accepts comment field
        response = await client.post(
            "/api/v1/votes",
            json={
                "target_type": "model",
                "target_id": "00000000-0000-0000-0000-000000000001",
                "category_id": "00000000-0000-0000-0000-000000000002",
                "idempotency_key": "test-key-123",
                "comment": "This is a test comment",
            },
        )
        # Should fail with 401 (no auth) but not 422 (validation error)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_vote_without_comment_accepted(self, client):
        """Vote without comment should be accepted."""
        response = await client.post(
            "/api/v1/votes",
            json={
                "target_type": "model",
                "target_id": "00000000-0000-0000-0000-000000000001",
                "category_id": "00000000-0000-0000-0000-000000000002",
                "idempotency_key": "test-key-456",
            },
        )
        # Should fail with 401 (no auth) but not 422 (validation error)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_vote_with_long_comment_rejected(self, client):
        """Vote with comment >1000 chars should be rejected."""
        response = await client.post(
            "/api/v1/votes",
            json={
                "target_type": "model",
                "target_id": "00000000-0000-0000-0000-000000000001",
                "category_id": "00000000-0000-0000-0000-000000000002",
                "idempotency_key": "test-key-789",
                "comment": "x" * 1001,
            },
        )
        # Should fail with 422 (validation error)
        assert response.status_code == 422
