"""Tests for HU-T10 — List Orchestrator Categories."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListOrchestratorCategories:
    """Test GET /api/v1/categories?scope=orchestrators endpoint."""

    @pytest.mark.asyncio
    async def test_list_categories_default_scope(self, client):
        """Default scope should be models."""
        response = await client.get("/api/v1/categories")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["scope"] == "models"

    @pytest.mark.asyncio
    async def test_list_categories_orchestrators_scope(self, client):
        """Should support orchestrators scope."""
        response = await client.get("/api/v1/categories?scope=orchestrators")
        assert response.status_code == 200
        data = response.json()
        assert data["meta"]["scope"] == "orchestrators"

    @pytest.mark.asyncio
    async def test_list_categories_invalid_scope(self, client):
        """Should return 422 for invalid scope."""
        response = await client.get("/api/v1/categories?scope=invalid")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_categories_has_taxonomy_version(self, client):
        """Response should have taxonomy_version."""
        response = await client.get("/api/v1/categories?scope=orchestrators")
        data = response.json()
        assert "taxonomy_version" in data["meta"]

    @pytest.mark.asyncio
    async def test_list_categories_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/categories?scope=orchestrators&lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"
