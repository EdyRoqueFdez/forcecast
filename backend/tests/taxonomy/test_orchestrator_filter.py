"""Tests for HU-T11 — Filter Orchestrators by Category."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestFilterOrchestratorsByCategory:
    """Test GET /api/v1/orchestrators?category=xxx endpoint."""

    @pytest.mark.asyncio
    async def test_filter_by_category_returns_200(self, client):
        """Filtering by category should return 200."""
        response = await client.get("/api/v1/orchestrators?category=multi_agent")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_category_has_data_key(self, client):
        """Response should have data key."""
        response = await client.get("/api/v1/orchestrators?category=multi_agent")
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_filter_by_category_empty_result(self, client):
        """Non-existent category should return empty list."""
        response = await client.get("/api/v1/orchestrators?category=nonexistent")
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    @pytest.mark.asyncio
    async def test_filter_by_category_with_search(self, client):
        """Category filter should work with search."""
        response = await client.get("/api/v1/orchestrators?category=multi_agent&search=lang")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_by_category_pagination(self, client):
        """Category filter should work with pagination."""
        response = await client.get("/api/v1/orchestrators?category=multi_agent&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2

    @pytest.mark.asyncio
    async def test_filter_by_category_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/orchestrators?category=multi_agent&lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"
