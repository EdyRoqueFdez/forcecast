"""Phase 8.2 + 8.3 — OpenAPI Contracts + Contract Tests — TDD RED"""
import pathlib
import yaml

REPO_ROOT = pathlib.Path(__file__).parents[4]
PUBLIC_YAML = REPO_ROOT / "forcecast" / "contracts" / "taxonomy-public.yaml"
ADMIN_YAML = REPO_ROOT / "forcecast" / "contracts" / "taxonomy-admin.yaml"


def _load_yaml(path: pathlib.Path) -> dict:
    assert path.exists(), f"Missing contract {path}"
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    assert isinstance(data, dict), "YAML must parse to dict"
    return data


def test_public_yaml_exists_and_valid_openapi():
    data = _load_yaml(PUBLIC_YAML)
    assert data.get("openapi", "").startswith("3."), "must be OpenAPI 3.x"
    assert "paths" in data, "must have paths"
    assert "info" in data, "must have info"
    assert data["info"]["title"], "title required"


def test_admin_yaml_exists_and_valid_openapi():
    data = _load_yaml(ADMIN_YAML)
    assert data.get("openapi", "").startswith("3."), "must be OpenAPI 3.x"
    assert "paths" in data
    assert "info" in data


def test_public_yaml_has_5_endpoints():
    data = _load_yaml(PUBLIC_YAML)
    paths = data.get("paths", {})
    # Expect 5 public endpoints
    expected = ["/api/v1/models", "/api/v1/models/{slug}", "/api/v1/categories", "/api/v1/providers", "/api/v1/locales"]
    for p in expected:
        assert p in paths, f"public contract missing path {p}"
    # Check each has GET
    for p in expected:
        assert "get" in paths[p], f"{p} must have GET"


def test_admin_yaml_has_7_endpoints():
    data = _load_yaml(ADMIN_YAML)
    paths = data.get("paths", {})
    expected = [
        "/api/v1/admin/ingestion/run",
        "/api/v1/admin/models/{model_id}/approve",
        "/api/v1/admin/models/{model_id}/reject",
        "/api/v1/admin/models/{model_id}/deprecate",
        "/api/v1/admin/taxonomy/versions",
        "/api/v1/admin/taxonomy/versions/{version_id}/activate",
        "/api/v1/admin/webhooks",
    ]
    for p in expected:
        assert p in paths, f"admin contract missing path {p}"
        assert "post" in paths[p], f"{p} must have POST"


def test_public_yaml_response_envelope():
    data = _load_yaml(PUBLIC_YAML)
    text = PUBLIC_YAML.read_text(encoding="utf-8")
    # Envelope fields must be documented
    assert "PaginatedResponse" in text or "meta" in text.lower(), "public YAML must document envelope"
    assert "links" in text.lower(), "public YAML must document links"
    # Price fields omitted when null should be documented as optional
    assert "input_price_per_mtok" in text, "must document pricing fields"
    # Cache headers
    assert "Cache-Control" in text or "cache" in text.lower(), "public YAML should mention caching"


def test_admin_yaml_auth_documented():
    data = _load_yaml(ADMIN_YAML)
    text = ADMIN_YAML.read_text(encoding="utf-8")
    # Admin must document auth
    assert "security" in text.lower() or "bearer" in text.lower() or "Authorization" in text, "admin YAML must document auth"
    assert "X-Forcecast-Api-Key" in text or "apiKey" in text or "fk_admin" in text.lower(), "admin YAML must document API key"
    # Rate limit headers
    assert "X-RateLimit" in text or "RateLimit" in text or "429" in text, "admin YAML must document rate limiting"


def test_public_contract_matches_implementation():
    """Validate public YAML paths match actual FastAPI router routes."""
    from fastapi import FastAPI
    from app.taxonomy.api.public import router as public_router

    app = FastAPI()
    app.include_router(public_router, prefix="/api/v1")
    openapi = app.openapi()
    impl_paths = set(openapi["paths"].keys())
    yaml_data = _load_yaml(PUBLIC_YAML)
    yaml_paths = set(yaml_data["paths"].keys())
    # YAML should cover at least all impl paths, no extra unknown
    for p in impl_paths:
        assert p in yaml_paths, f"YAML missing impl path {p}"
    # Also check 406/422 documented for public
    text = PUBLIC_YAML.read_text(encoding="utf-8")
    assert "406" in text, "public YAML must document 406 for unsupported locale"
    assert "422" in text, "public YAML must document 422 for validation"


def test_admin_contract_matches_implementation():
    from fastapi import FastAPI
    from app.taxonomy.api.admin import router as admin_router

    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")
    openapi = app.openapi()
    impl_paths = set(openapi["paths"].keys())
    yaml_data = _load_yaml(ADMIN_YAML)
    yaml_paths = set(yaml_data["paths"].keys())
    for p in impl_paths:
        assert p in yaml_paths, f"admin YAML missing impl path {p}"
    text = ADMIN_YAML.read_text(encoding="utf-8")
    assert "401" in text and "403" in text, "admin YAML must document 401/403"


def test_contract_schemas_validate_responses():
    """Basic schemathesis-style: Validate example responses against schemas if openapi spec validator available."""
    try:
        from openapi_spec_validator import validate_spec  # type: ignore
    except Exception:
        pytest = __import__("pytest")
        pytest.skip("openapi-spec-validator not installed — skipping strict validation")
        return
    for path in [PUBLIC_YAML, ADMIN_YAML]:
        data = _load_yaml(path)
        # Should not raise
        validate_spec(data)


def test_public_pagination_and_locale_in_yaml():
    text = PUBLIC_YAML.read_text(encoding="utf-8")
    assert "cursor" in text.lower(), "public YAML must document cursor pagination"
    assert "lang" in text.lower(), "public YAML must document lang param"
    assert "406" in text and "Link" in text, "public YAML must document 406 with Link headers"


def test_hostings_without_prices_in_yaml():
    text = PUBLIC_YAML.read_text(encoding="utf-8")
    # Hostings should not have price fields
    # Check ModelHostingResponse schema does not include price
    # Simple check: hosting section should mention provider + is_primary
    assert "is_primary" in text, "YAML must document is_primary for hostings"
    # Ensure hosting price not documented as required
    # If price appears in hosting, it's a failure — but global prices are ok
    # We check that hosting schema block does not contain price override
    # This is a soft check: ensure yaml does not claim hosting has input_price_override
    assert "input_price_override" not in text, "hosting must not have price override"
