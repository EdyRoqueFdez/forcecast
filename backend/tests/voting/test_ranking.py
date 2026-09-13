"""Tests for HU-V06 — Model Ranking Endpoint."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestModelRanking:
    """Test GET /api/v1/rankings/models endpoint."""

    @pytest.mark.asyncio
    async def test_ranking_requires_category(self, client):
        """Endpoint should require category parameter."""
        response = await client.get("/api/v1/rankings/models")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ranking_returns_200(self, client):
        """Endpoint should return 200 OK."""
        response = await client.get("/api/v1/rankings/models?category=coding")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ranking_has_data_key(self, client):
        """Response should have data key."""
        response = await client.get("/api/v1/rankings/models?category=coding")
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_ranking_has_meta(self, client):
        """Response should have meta."""
        response = await client.get("/api/v1/rankings/models?category=coding")
        data = response.json()
        assert "meta" in data
        assert "total" in data["meta"]
        assert "category" in data["meta"]

    @pytest.mark.asyncio
    async def test_ranking_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/rankings/models?category=coding&lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"

    @pytest.mark.asyncio
    async def test_ranking_has_cache_headers(self, client):
        """Response should have cache headers."""
        response = await client.get("/api/v1/rankings/models?category=coding")
        assert "Cache-Control" in response.headers

    @pytest.mark.asyncio
    async def test_ranking_with_min_votes(self, client):
        """Should support min_votes parameter."""
        response = await client.get("/api/v1/rankings/models?category=coding&min_votes=10")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_ranking_with_limit(self, client):
        """Should support limit parameter."""
        response = await client.get("/api/v1/rankings/models?category=coding&limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 5


class TestOrchestratorRanking:
    """Test GET /api/v1/rankings/orchestrators endpoint."""

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_requires_category(self, client):
        """Endpoint should require category parameter."""
        response = await client.get("/api/v1/rankings/orchestrators")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_returns_200(self, client):
        """Endpoint should return 200 OK."""
        response = await client.get("/api/v1/rankings/orchestrators?category=multi_agent")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_has_data_key(self, client):
        """Response should have data key."""
        response = await client.get("/api/v1/rankings/orchestrators?category=multi_agent")
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_has_meta(self, client):
        """Response should have meta."""
        response = await client.get("/api/v1/rankings/orchestrators?category=multi_agent")
        data = response.json()
        assert "meta" in data
        assert "total" in data["meta"]
        assert "category" in data["meta"]

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/rankings/orchestrators?category=multi_agent&lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"

    @pytest.mark.asyncio
    async def test_orchestrator_ranking_has_cache_headers(self, client):
        """Response should have cache headers."""
        response = await client.get("/api/v1/rankings/orchestrators?category=multi_agent")
        assert "Cache-Control" in response.headers
