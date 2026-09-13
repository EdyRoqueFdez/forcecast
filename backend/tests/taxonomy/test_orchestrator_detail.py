"""Tests for HU-T09 — View Orchestrator Details."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestGetOrchestrator:
    """Test GET /api/v1/orchestrators/{slug} endpoint."""

    @pytest.mark.asyncio
    async def test_get_orchestrator_not_found(self, client):
        """Should return 404 for non-existent slug."""
        response = await client.get("/api/v1/orchestrators/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_get_orchestrator_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/orchestrators/langchain?lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"

    @pytest.mark.asyncio
    async def test_get_orchestrator_has_cache_headers(self, client):
        """Response should have cache headers."""
        response = await client.get("/api/v1/orchestrators/nonexistent")
        assert "Cache-Control" in response.headers

    @pytest.mark.asyncio
    async def test_get_orchestrator_content_language(self, client):
        """Response should have Content-Language header."""
        response = await client.get("/api/v1/orchestrators/nonexistent")
        assert response.headers.get("Content-Language") == "en"

    @pytest.mark.asyncio
    async def test_get_orchestrator_spanish_locale(self, client):
        """Should support Spanish locale."""
        response = await client.get("/api/v1/orchestrators/nonexistent?lang=es")
        assert response.headers.get("Content-Language") == "es"
