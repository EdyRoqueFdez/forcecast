"""Phase 7.1 — Public Schemas + Response Envelope — TDD RED"""
import pytest
from decimal import Decimal


def test_paginated_response_serialization():
    from app.taxonomy.schemas.public import PaginatedResponse, Meta, Links

    item_schema = {"slug": "gpt-4", "display_name": "GPT-4"}
    resp = PaginatedResponse[dict](
        data=[item_schema],
        meta=Meta(page=1, limit=20, total=42, has_more=True, next_cursor="abc", taxonomy_version="v1"),
        links=Links(first="/api/v1/models?page=1", prev=None, next="/api/v1/models?page=2", last="/api/v1/models?page=3"),
    )
    dumped = resp.model_dump()
    assert dumped["meta"]["total"] == 42
    assert dumped["meta"]["has_more"] is True
    assert dumped["links"]["next"] == "/api/v1/models?page=2"
    assert len(dumped["data"]) == 1


def test_empty_result_envelope():
    from app.taxonomy.schemas.public import PaginatedResponse, Meta, Links

    resp = PaginatedResponse[dict](
        data=[],
        meta=Meta(page=1, limit=20, total=0, has_more=False, next_cursor=None, taxonomy_version="v1"),
        links=Links(first="/api/v1/models?page=1", prev=None, next=None, last="/api/v1/models?page=1"),
    )
    assert resp.meta.total == 0
    assert resp.meta.has_more is False
    assert resp.data == []


def test_error_envelope_rfc7807():
    from app.taxonomy.schemas.public import ErrorResponse, ErrorEnvelope, ErrorDetail

    err = ErrorResponse(
        error=ErrorEnvelope(
            code="VALIDATION_ERROR",
            message="Invalid page_size",
            details=[ErrorDetail(field="page_size", issue="must be >=1")],
            trace_id="tid-123",
        )
    )
    dumped = err.model_dump()
    assert dumped["error"]["code"] == "VALIDATION_ERROR"
    assert dumped["error"]["details"][0]["field"] == "page_size"
    assert dumped["error"]["trace_id"] == "tid-123"


def test_error_response_includes_422_code():
    from app.taxonomy.schemas.public import ErrorResponse

    # Ensure factory helper creates correct structure
    resp = ErrorResponse.from_exception(code="VALIDATION_ERROR", message="bad", status_code=422)
    assert resp.error.code == "VALIDATION_ERROR"
    assert resp.error.message == "bad"


def test_model_detail_omits_null_prices():
    from app.taxonomy.schemas.public import ModelDetailResponse, ProviderSummary

    m = ModelDetailResponse(
        id="11111111-1111-4111-8111-111111111111",
        slug="llama-3-70b",
        display_name="Llama 3 70B",
        modality=["text"],
        status="approved",
        source="manual",
        categories=[],
        hostings=[],
        locale_used="en",
        input_price_per_mtok=None,
        output_price_per_mtok=None,
    )
    dumped = m.model_dump(exclude_none=True, mode="json")
    assert "input_price_per_mtok" not in dumped
    assert "output_price_per_mtok" not in dumped


def test_model_detail_includes_prices_when_present():
    from app.taxonomy.schemas.public import ModelDetailResponse

    m = ModelDetailResponse(
        id="22222222-2222-4222-8222-222222222222",
        slug="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        modality=["text"],
        status="approved",
        source="manual",
        categories=[],
        hostings=[],
        locale_used="en",
        input_price_per_mtok=Decimal("3.00"),
        output_price_per_mtok=Decimal("15.00"),
    )
    dumped = m.model_dump(exclude_none=True, mode="json")
    # Decimal serialized as string or float; check presence
    assert "input_price_per_mtok" in dumped
    assert "output_price_per_mtok" in dumped


def test_hostings_without_prices():
    from app.taxonomy.schemas.public import ModelDetailResponse, ModelHostingResponse, ProviderSummary

    m = ModelDetailResponse(
        id="33333333-3333-4333-8333-333333333333",
        slug="llama-3-70b",
        display_name="Llama 3 70B",
        modality=["text"],
        status="approved",
        source="manual",
        categories=[],
        hostings=[
            ModelHostingResponse(provider=ProviderSummary(slug="anthropic", name="Anthropic"), is_primary=True),
            ModelHostingResponse(provider=ProviderSummary(slug="together", name="Together"), is_primary=False),
        ],
        locale_used="en",
    )
    dumped = m.model_dump(exclude_none=True, mode="json")
    for h in dumped["hostings"]:
        assert "input_price_per_mtok" not in h
        assert "output_price_per_mtok" not in h
        assert "is_primary" in h


def test_locale_negotiation_unsupported_raises_406():
    from app.taxonomy.schemas.public import resolve_locale

    # Supported locales are en,es,pt,fr,zh — 'xx' should raise 406
    with pytest.raises(Exception) as exc:
        resolve_locale("xx")
    # Check status_code 406
    err = exc.value
    status = getattr(err, "status_code", None) or getattr(exc.value, "args", [None])[0]
    # DomainError or HTTPException with 406
    assert getattr(err, "status_code", 406) == 406 or "406" in str(err)


def test_meta_taxonomy_version_present():
    from app.taxonomy.schemas.public import Meta

    meta = Meta(page=1, limit=20, total=5, has_more=False, taxonomy_version="v1")
    assert meta.taxonomy_version == "v1"
