"""Coverage boost for public.py — locale validation, page>10, orchestrator endpoints, domains."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.taxonomy.api.public import router as public_router, _validate_locale
from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    TaxonomyVersion,
    LocaleMeta,
    Orchestrator,
    OrchestratorTranslation,
    OrchestratorProvider,
    Domain,
    DomainTranslation,
)


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")

    @sa_event.listens_for(eng.sync_engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with eng.begin() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys=ON"))
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


def make_app(engine):
    app = FastAPI()
    app.include_router(public_router, prefix="/api/v1")

    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    return app


async def seed_api(session):
    prov = Provider(id=str(uuid.uuid4()), slug="anthropic", name="Anthropic", status="active")
    session.add(prov)
    await session.flush()
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()
    cat = Category(id=str(uuid.uuid4()), slug="coding", taxonomy_version="v1", status="active")
    session.add(cat)
    await session.flush()
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="en", name="Coding"))
    await session.flush()
    for loc, native in [("en", "English"), ("es", "Español"), ("pt", "Português"), ("fr", "Français"), ("zh", "中文")]:
        session.add(LocaleMeta(locale=loc, native_name=native, direction="ltr", plural_categories=["one", "other"]))
    await session.flush()
    m1 = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov.id,
        slug="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        modality=["text"],
        status="approved",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m1)
    await session.flush()
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m1.id, provider_id=prov.id, is_primary=True))
    session.add(ModelCategory(model_id=m1.id, category_id=cat.id, taxonomy_version="v1"))
    await session.commit()
    return {"m1": m1}


async def seed_orchestrators(session):
    prov = Provider(id=str(uuid.uuid4()), slug="testprov", name="TestProv", status="active")
    session.add(prov)
    await session.flush()
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()
    orch = Orchestrator(
        id=str(uuid.uuid4()),
        slug="test-orch",
        name="Test Orchestrator",
        status="approved",
    )
    session.add(orch)
    await session.flush()
    session.add(OrchestratorTranslation(
        id=str(uuid.uuid4()), orchestrator_id=orch.id, locale="en", name="Test Orch"
    ))
    session.add(OrchestratorProvider(orchestrator_id=orch.id, provider_id=prov.id))
    await session.commit()
    return {"orch": orch}


async def seed_domains(session):
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()
    domain = Domain(
        id=str(uuid.uuid4()),
        slug="nlp",
        taxonomy_version="v1",
        status="active",
    )
    session.add(domain)
    await session.flush()
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=domain.id, locale="en", name="NLP"))
    await session.commit()
    return {"domain": domain}


# ---------------------------------------------------------------------------
# _validate_locale function (lines 47-50)
# ---------------------------------------------------------------------------

def test_validate_locale_valid():
    assert _validate_locale("en") == "en"
    assert _validate_locale("ES") == "es"


def test_validate_locale_invalid():
    with pytest.raises(Exception) as exc_info:
        _validate_locale("xx")
    assert exc_info.value.status_code == 406


# ---------------------------------------------------------------------------
# list_models: page > 10 returns 422 (line 75)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_page_gt_10(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?page=11")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# list_models: exception from _get_current_version (lines 122-123)
# Uses a side_effect that succeeds on the first call (inside service)
# and fails on the second call (in endpoint try/except)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_version_exception(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    call_count = 0

    async def mock_version(session):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise RuntimeError("db fail")
        return "v1"

    with patch("app.taxonomy.services.public._get_current_version", side_effect=mock_version):
        resp = client.get("/api/v1/models")
    assert resp.status_code == 200
    assert resp.json()["meta"]["taxonomy_version"] == "v1"


# ---------------------------------------------------------------------------
# get_model: unsupported locale (line 149)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models/claude-3-5-sonnet?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# list_categories: unsupported locale (line 180)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/categories?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# list_providers: unsupported locale (line 197)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_providers_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/providers?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# list_orchestrators: unsupported locale (line 234)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# list_orchestrators: page > 10 (line 238)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_page_gt_10(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators?page=11")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


# ---------------------------------------------------------------------------
# list_orchestrators: empty results (lines 262-263)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_empty(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        pass
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators?category=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["data"] == []


# ---------------------------------------------------------------------------
# list_orchestrators: successful with results (lines 264-269)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_with_results(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators?limit=20")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) >= 1
    assert "has_more" in body["meta"]
    assert "next_cursor" in body["meta"]


# ---------------------------------------------------------------------------
# list_orchestrators: exception from _get_current_version (lines 280-281)
# Uses side_effect that succeeds first call (service) and fails second (endpoint)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_version_exception(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    call_count = 0

    async def mock_version(session):
        nonlocal call_count
        call_count += 1
        if call_count >= 2:
            raise RuntimeError("db fail")
        return "v1"

    with patch("app.taxonomy.services.public._get_current_version", side_effect=mock_version):
        resp = client.get("/api/v1/orchestrators")
    assert resp.status_code == 200
    assert resp.json()["meta"]["taxonomy_version"] == "v1"


# ---------------------------------------------------------------------------
# get_orchestrator: unsupported locale (line 310)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_orchestrator_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators/test-orch?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# get_orchestrator: successful (lines 312-330)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_orchestrator_success(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators/test-orch?lang=en")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "test-orch"


# ---------------------------------------------------------------------------
# get_orchestrator: not found
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_orchestrator_not_found(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators/nonexistent?lang=en")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# list_domains: unsupported locale (lines 342-351)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_domains_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_domains(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/domains?lang=xx")
    assert resp.status_code == 406


# ---------------------------------------------------------------------------
# list_domains: successful (lines 342-351 happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_domains_success(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_domains(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/domains?lang=en")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert body["total"] >= 1
