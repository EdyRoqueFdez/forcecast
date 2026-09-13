"""Tests for HU-V08 — Report abusive vote/comment."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestReportVote:
    """Test POST /api/v1/votes/report endpoint."""

    @pytest.mark.asyncio
    async def test_report_requires_auth(self, client):
        """Endpoint should require authentication."""
        response = await client.post(
            "/api/v1/votes/report",
            json={"target_id": "vote-1", "target_type": "vote", "reason": "spam"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_report_requires_body(self, client):
        """Endpoint should require body."""
        response = await client.post(
            "/api/v1/votes/report",
            headers={"Authorization": "Bearer fake-token"},
            json={},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_report_invalid_reason(self, client):
        """Endpoint should reject invalid reason."""
        response = await client.post(
            "/api/v1/votes/report",
            headers={"Authorization": "Bearer fake-token"},
            json={
                "target_id": "vote-1",
                "target_type": "vote",
                "reason": "invalid_reason",
            },
        )
        assert response.status_code == 422


class TestAdminReports:
    """Test GET /api/v1/admin/votes/reports endpoint."""

    @pytest.mark.asyncio
    async def test_reports_requires_auth(self, client):
        """Endpoint should require authentication."""
        response = await client.get("/api/v1/admin/votes/reports")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_reports_returns_200(self, client):
        """Endpoint should return 200 OK."""
        response = await client.get(
            "/api/v1/admin/votes/reports",
            headers={"Authorization": "Bearer fake-token"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reports_has_reports_key(self, client):
        """Response should have reports key."""
        response = await client.get(
            "/api/v1/admin/votes/reports",
            headers={"Authorization": "Bearer fake-token"},
        )
        data = response.json()
        assert "reports" in data
        assert "total" in data


class TestReviewReport:
    """Test PUT /api/v1/admin/votes/reports/{report_id} endpoint."""

    @pytest.mark.asyncio
    async def test_review_requires_auth(self, client):
        """Endpoint should require authentication."""
        response = await client.put(
            "/api/v1/admin/votes/reports/report-123",
            json={"action": "approve"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_review_invalid_action(self, client):
        """Endpoint should reject invalid action."""
        response = await client.put(
            "/api/v1/admin/votes/reports/report-123",
            headers={"Authorization": "Bearer fake-token"},
            json={"action": "invalid"},
        )
        assert response.status_code == 422
