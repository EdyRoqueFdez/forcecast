from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_catalog_filters_models_by_category() -> None:
    response = client.get("/api/v1/catalog/models", params={"category": "coding"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 5
    assert all("coding" in item["categories"] for item in payload["items"])


def test_catalog_search_is_case_insensitive() -> None:
    response = client.get("/api/v1/catalog/models", params={"query": "OPENAI"})

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["gpt-4.1"]


def test_compare_returns_known_and_missing_models() -> None:
    response = client.get(
        "/api/v1/catalog/models/compare",
        params=[("slugs", "gpt-4.1"), ("slugs", "unknown-model")],
    )

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["gpt-4.1"]
    assert response.json()["missing_slugs"] == ["unknown-model"]
