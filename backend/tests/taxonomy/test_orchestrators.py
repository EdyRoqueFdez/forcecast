"""Tests for HU-T08 — List Orchestrators."""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestListOrchestrators:
    """Test GET /api/v1/orchestrators endpoint."""

    @pytest.mark.asyncio
    async def test_list_orchestrators_returns_200(self, client):
        """Endpoint should return 200 OK."""
        response = await client.get("/api/v1/orchestrators")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_orchestrators_has_data_key(self, client):
        """Response should have data key."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        assert "data" in data

    @pytest.mark.asyncio
    async def test_list_orchestrators_has_meta(self, client):
        """Response should have meta with pagination info."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        assert "meta" in data
        assert "total" in data["meta"]
        assert "has_more" in data["meta"]

    @pytest.mark.asyncio
    async def test_list_orchestrators_has_links(self, client):
        """Response should have links for pagination."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        assert "links" in data
        assert "first" in data["links"]

    @pytest.mark.asyncio
    async def test_list_orchestrators_default_locale(self, client):
        """Default locale should be en."""
        response = await client.get("/api/v1/orchestrators")
        assert response.status_code == 200
        # Check Content-Language header
        assert response.headers.get("Content-Language") == "en"

    @pytest.mark.asyncio
    async def test_list_orchestrators_spanish_locale(self, client):
        """Should support Spanish locale."""
        response = await client.get("/api/v1/orchestrators?lang=es")
        assert response.status_code == 200
        assert response.headers.get("Content-Language") == "es"

    @pytest.mark.asyncio
    async def test_list_orchestrators_unsupported_locale(self, client):
        """Should return 406 for unsupported locale."""
        response = await client.get("/api/v1/orchestrators?lang=xx")
        assert response.status_code == 406
        data = response.json()
        assert data["error"]["code"] == "UNSUPPORTED_LOCALE"

    @pytest.mark.asyncio
    async def test_list_orchestrators_pagination(self, client):
        """Should support limit parameter."""
        response = await client.get("/api/v1/orchestrators?limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data["data"]) <= 2

    @pytest.mark.asyncio
    async def test_list_orchestrators_sort_by_name(self, client):
        """Should sort by name by default."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        names = [item["name"] for item in data["data"]]
        assert names == sorted(names)

    @pytest.mark.asyncio
    async def test_list_orchestrators_sort_desc(self, client):
        """Should support descending sort."""
        response = await client.get("/api/v1/orchestrators?sort=name&order=desc")
        data = response.json()
        names = [item["name"] for item in data["data"]]
        assert names == sorted(names, reverse=True)

    @pytest.mark.asyncio
    async def test_list_orchestrators_item_structure(self, client):
        """Each item should have required fields."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        if data["data"]:
            item = data["data"][0]
            assert "id" in item
            assert "slug" in item
            assert "name" in item
            assert "version" in item
            assert "maintainer" in item
            assert "website" in item
            assert "repo_url" in item
            assert "status" in item
            assert "providers" in item

    @pytest.mark.asyncio
    async def test_list_orchestrators_providers_structure(self, client):
        """Providers should have slug and name."""
        response = await client.get("/api/v1/orchestrators")
        data = response.json()
        for item in data["data"]:
            for provider in item["providers"]:
                assert "slug" in provider
                assert "name" in provider

    @pytest.mark.asyncio
    async def test_list_orchestrators_page_limit(self, client):
        """Page >10 should return 422."""
        response = await client.get("/api/v1/orchestrators?page=11")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_list_orchestrators_cache_headers(self, client):
        """Response should have cache headers."""
        response = await client.get("/api/v1/orchestrators")
        assert "Cache-Control" in response.headers
        assert "max-age" in response.headers["Cache-Control"]
