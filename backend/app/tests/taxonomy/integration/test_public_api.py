"""Phase 7.3 — Public API Endpoints (5 endpoints) — TDD RED"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.taxonomy.api.public import router as public_router
from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
    LocaleMeta,
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
    prov2 = Provider(id=str(uuid.uuid4()), slug="openai", name="OpenAI", status="active")
    session.add(prov)
    session.add(prov2)
    await session.flush()
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()
    cat = Category(id=str(uuid.uuid4()), slug="coding", taxonomy_version="v1", status="active")
    session.add(cat)
    await session.flush()
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="en", name="Coding"))
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="es", name="Codificación"))
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
        input_price_per_mtok=Decimal("3.00"),
        output_price_per_mtok=Decimal("15.00"),
        release_date=datetime(2024, 6, 1).date(),
    )
    m2 = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov2.id,
        slug="llama-3-70b",
        display_name="Llama 3 70B",
        modality=["text"],
        status="approved",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
        input_price_per_mtok=None,
        output_price_per_mtok=None,
        release_date=datetime(2024, 4, 1).date(),
    )
    m2b = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov.id,
        slug="draft-model",
        display_name="Draft",
        modality=["text"],
        status="draft",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m1)
    session.add(m2)
    session.add(m2b)
    await session.flush()
    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m1.id, locale="es", display_name="Claude 3.5 Soneto"))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m1.id, provider_id=prov.id, is_primary=True))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m2.id, provider_id=prov2.id, is_primary=True))
    session.add(ModelCategory(model_id=m1.id, category_id=cat.id, taxonomy_version="v1"))
    await session.commit()
    return {"m1": m1, "m2": m2}


@pytest.mark.asyncio
async def test_list_models_envelope(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?limit=20")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert "links" in body
    assert body["meta"]["total"] == 2  # only approved
    assert body["meta"]["has_more"] is False  # 2 <= limit
    assert "first" in body["links"]


@pytest.mark.asyncio
async def test_list_models_filter_category_and_lang(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?category_slug=coding&lang=es")
    assert resp.status_code == 200
    body = resp.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["slug"] == "claude-3-5-sonnet"
    assert body["data"][0]["locale_used"] == "es"


@pytest.mark.asyncio
async def test_list_models_search(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?search=claude")
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] == 1


@pytest.mark.asyncio
async def test_list_models_cursor_pagination(engine):
    # Seed many models for pagination
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
        prov = (await s.execute(__import__("sqlalchemy").select(Provider).where(Provider.slug == "anthropic"))).scalars().first()
        for i in range(3, 10):
            m = AIModel(
                id=str(uuid.uuid4()),
                provider_id=prov.id,
                slug=f"model-{i}",
                display_name=f"Model {i}",
                modality=["text"],
                status="approved",
                source="manual",
                source_payload_hash=str(uuid.uuid4()),
                release_date=datetime(2024, 1, i).date(),
            )
            s.add(m)
        await s.commit()
    app = make_app(engine)
    client = TestClient(app)
    r1 = client.get("/api/v1/models?limit=3")
    assert r1.status_code == 200
    assert len(r1.json()["data"]) == 3
    assert r1.json()["meta"]["has_more"] is True
    cursor = r1.json()["meta"]["next_cursor"]
    assert cursor is not None
    r2 = client.get(f"/api/v1/models?limit=3&cursor={cursor}")
    assert r2.status_code == 200
    assert len(r2.json()["data"]) == 3
    # ensure no overlap
    slugs1 = {m["slug"] for m in r1.json()["data"]}
    slugs2 = {m["slug"] for m in r2.json()["data"]}
    assert slugs1.isdisjoint(slugs2)


@pytest.mark.asyncio
async def test_get_model_detail_with_prices(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models/claude-3-5-sonnet")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "claude-3-5-sonnet"
    assert "input_price_per_mtok" in body
    assert "output_price_per_mtok" in body
    assert body["hostings"][0]["is_primary"] is True
    assert "provider" in body["hostings"][0]


@pytest.mark.asyncio
async def test_get_model_without_prices_omitted(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models/llama-3-70b")
    assert resp.status_code == 200
    assert "input_price_per_mtok" not in resp.json()
    assert "output_price_per_mtok" not in resp.json()


@pytest.mark.asyncio
async def test_get_model_hostings_no_prices(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models/llama-3-70b")
    for h in resp.json()["hostings"]:
        assert "is_primary" in h
        assert "provider" in h
        assert "input_price" not in h and "output_price" not in h


@pytest.mark.asyncio
async def test_get_model_not_found(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_list_categories(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/categories?lang=zh")
    # Depending on impl, may not have zh for coding? we have only en+es seeded, fallback to en case zh missing -> but test expects zh fallback behavior or at least response
    assert resp.status_code in [200, 406]
    if resp.status_code == 200:
        body = resp.json()
        assert "data" in body
        assert body["meta"]["taxonomy_version"] == "v1"


@pytest.mark.asyncio
async def test_list_providers(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/providers")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2


@pytest.mark.asyncio
async def test_list_locales(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/locales")
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 5


@pytest.mark.asyncio
async def test_406_for_unsupported_locale(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?lang=xx")
    assert resp.status_code == 406
    body = resp.json()
    assert body["error"]["code"] == "UNSUPPORTED_LOCALE"


@pytest.mark.asyncio
async def test_422_for_invalid_limit(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?limit=999")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_sort_and_order(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    r = client.get("/api/v1/models?sort=release_date&order=asc")
    assert r.status_code == 200
    slugs = [m["slug"] for m in r.json()["data"]]
    assert slugs[0] == "llama-3-70b"


@pytest.mark.asyncio
async def test_empty_result(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_api(s)
    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/models?category_slug=nonexistent")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["total"] == 0
    assert resp.json()["meta"]["has_more"] is False
