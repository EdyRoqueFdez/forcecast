"""MVP Tests - FastAPI TestClient"""
import pytest
from fastapi.testclient import TestClient
from app.main import app, MODELS_DATA, MODELS_BY_SLUG

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["models_loaded"] == len(MODELS_DATA)


def test_meta():
    r = client.get("/api/v1/meta")
    assert r.status_code == 200
    data = r.json()
    assert "categories" in data
    assert "providers" in data
    assert "modalities" in data
    assert data["total_models"] == len(MODELS_DATA)
    assert "coding" in data["categories"]
    assert "openai" in data["providers"]


def test_list_models_default():
    r = client.get("/api/v1/models")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == len(MODELS_DATA)
    assert len(data["data"]) <= data["limit"]
    assert data["limit"] == 20
    assert data["offset"] == 0


def test_list_models_filter_category():
    r = client.get("/api/v1/models?category=coding")
    assert r.status_code == 200
    data = r.json()
    for model in data["data"]:
        assert "coding" in model["categories"]


def test_list_models_filter_provider():
    r = client.get("/api/v1/models?provider=openai")
    assert r.status_code == 200
    data = r.json()
    for model in data["data"]:
        assert model["provider"]["slug"] == "openai"


def test_list_models_search():
    r = client.get("/api/v1/models?search=gpt")
    assert r.status_code == 200
    data = r.json()
    for model in data["data"]:
        assert "gpt" in model["slug"].lower() or "gpt" in model["display_name"].lower()


def test_list_models_pagination():
    r = client.get("/api/v1/models?limit=2&offset=0")
    assert r.status_code == 200
    data = r.json()
    assert len(data["data"]) == 2
    assert data["limit"] == 2
    assert data["offset"] == 0

    r2 = client.get("/api/v1/models?limit=2&offset=2")
    assert r2.status_code == 200
    data2 = r2.json()
    assert len(data2["data"]) == 2
    # Different models
    assert data["data"][0]["slug"] != data2["data"][0]["slug"]


def test_list_models_sort_price_asc():
    r = client.get("/api/v1/models?sort=input_price_per_mtok&order=asc")
    assert r.status_code == 200
    data = r.json()
    prices = [m["input_price_per_mtok"] for m in data["data"] if m["input_price_per_mtok"] is not None]
    assert prices == sorted(prices)


def test_get_model():
    r = client.get("/api/v1/models/gpt-4o")
    assert r.status_code == 200
    model = r.json()
    assert model["slug"] == "gpt-4o"
    assert model["provider"]["slug"] == "openai"


def test_get_model_not_found():
    r = client.get("/api/v1/models/nonexistent")
    assert r.status_code == 404


def test_compare_models():
    r = client.get("/api/v1/models/compare?slugs=gpt-4o&slugs=claude-3-5-sonnet")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 2
    assert len(data["models"]) == 2
    assert data["missing"] == []
    slugs = {m["slug"] for m in data["models"]}
    assert slugs == {"gpt-4o", "claude-3-5-sonnet"}


def test_compare_models_missing():
    r = client.get("/api/v1/models/compare?slugs=gpt-4o&slugs=nonexistent")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["missing"] == ["nonexistent"]


def test_compare_models_too_few():
    r = client.get("/api/v1/models/compare?slugs=gpt-4o")
    assert r.status_code == 400


def test_compare_models_too_many():
    r = client.get("/api/v1/models/compare?slugs=a&slugs=b&slugs=c&slugs=d&slugs=e")
    assert r.status_code == 400


def test_categories():
    r = client.get("/api/v1/categories")
    assert r.status_code == 200
    data = r.json()
    assert "coding" in data["data"]
    assert "debugging" in data["data"]
    assert "architecture" in data["data"]


def test_providers():
    r = client.get("/api/v1/providers")
    assert r.status_code == 200
    data = r.json()
    provider_slugs = {p["slug"] for p in data["data"]}
    assert "openai" in provider_slugs
    assert "anthropic" in provider_slugs


def test_modalities():
    r = client.get("/api/v1/modalities")
    assert r.status_code == 200
    data = r.json()
    assert "text" in data["data"]
    assert "vision" in data["data"]
    assert "reasoning" in data["data"]


def test_models_by_slug_lookup():
    assert "gpt-4o" in MODELS_BY_SLUG
    assert MODELS_BY_SLUG["gpt-4o"]["provider"]["slug"] == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])