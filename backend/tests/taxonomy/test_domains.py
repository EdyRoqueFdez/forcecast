"""Tests for HU-T05 — List Problem Domains."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListDomains:
    """Test GET /api/v1/domains endpoint."""

    @pytest.mark.asyncio
    async def test_list_domains_returns_200(self, client):
        """Endpoint should return 200 OK."""
        response = await client.get("/api/v1/domains")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_domains_has_data_key(self, client):
        """Response should have data key."""
        response = await client.get("/api/v1/domains")
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_list_domains_has_total(self, client):
        """Response should have total count."""
        response = await client.get("/api/v1/domains")
        data = response.json()
        assert "total" in data

    @pytest.mark.asyncio
    async def test_list_domains_default_locale(self, client):
        """Default locale should be en."""
        response = await client.get("/api/v1/domains")
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "en"

    @pytest.mark.asyncio
    async def test_list_domains_spanish_locale(self, client):
        """Should support Spanish locale."""
        response = await client.get("/api/v1/domains?lang=es")
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "es"

    @pytest.mark.asyncio
    async def test_list_domains_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/domains?lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"

    @pytest.mark.asyncio
    async def test_list_domains_item_structure(self, client):
        """Each item should have required fields."""
        response = await client.get("/api/v1/domains")
        data = response.json()
        if data["data"]:
            item = data["data"][0]
            assert "id" in item
            assert "slug" in item
            assert "name" in item
            assert "description" in item
            assert "locale_used" in item

    @pytest.mark.asyncio
    async def test_list_domains_cache_headers(self, client):
        """Response should have cache headers."""
        response = await client.get("/api/v1/domains")
        assert "Cache-Control" in response.headers
