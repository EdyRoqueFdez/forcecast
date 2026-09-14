"""Phase 5.3 — Orchestrator API Performance Test (p95 < 200ms).

Covers:
- Test endpoint returns 200 (basic)
- Test pagination works
- Test i18n works
- Test 406 for unsupported locale
- Test p95 < 200ms (performance gate)
"""

import statistics
import time
import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.taxonomy.api.public import router as public_router
from app.taxonomy.models.entities import (
    Orchestrator,
    OrchestratorProvider,
    OrchestratorTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
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


async def seed_orchestrators(session: AsyncSession, count: int = 10):
    """Seed orchestrators with translations and providers."""
    prov = Provider(id=str(uuid.uuid4()), slug="openai", name="OpenAI", status="active")
    session.add(prov)
    await session.flush()

    session.add(ProviderTranslation(
        id=str(uuid.uuid4()), provider_id=prov.id, locale="en", name="OpenAI EN",
    ))
    await session.flush()

    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()

    for i in range(count):
        orch = Orchestrator(
            id=str(uuid.uuid4()),
            slug=f"orch-{i:03d}",
            name=f"Orchestrator {i}",
            version=f"1.{i}.0",
            status="approved",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(orch)
        await session.flush()

        for loc, name_suf in [("en", "EN"), ("es", "ES"), ("fr", "FR")]:
            session.add(OrchestratorTranslation(
                id=str(uuid.uuid4()),
                orchestrator_id=orch.id,
                locale=loc,
                name=f"Orchestrator {i} {name_suf}",
                description=f"Description {name_suf} for orch-{i:03d}",
            ))

        session.add(OrchestratorProvider(
            orchestrator_id=orch.id,
            provider_id=prov.id,
            created_at=datetime.now(timezone.utc),
        ))
    await session.commit()


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_list_orchestrators_returns_200(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=5)

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators")
    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "meta" in body
    assert len(body["data"]) == 5


@pytest.mark.asyncio
async def test_list_orchestrators_pagination(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=10)

    app = make_app(engine)
    client = TestClient(app)

    resp1 = client.get("/api/v1/orchestrators?limit=3")
    assert resp1.status_code == 200
    body1 = resp1.json()
    assert len(body1["data"]) == 3
    assert body1["meta"]["total"] == 10
    assert body1["meta"]["has_more"] is True
    assert body1["meta"]["next_cursor"] is not None


@pytest.mark.asyncio
async def test_list_orchestrators_i18n(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=2)

    app = make_app(engine)
    client = TestClient(app)

    resp_en = client.get("/api/v1/orchestrators?lang=en")
    resp_es = client.get("/api/v1/orchestrators?lang=es")

    assert resp_en.status_code == 200
    assert resp_es.status_code == 200

    names_en = [o["name"] for o in resp_en.json()["data"]]
    names_es = [o["name"] for o in resp_es.json()["data"]]
    assert names_en != names_es
    assert all("EN" in n for n in names_en)
    assert all("ES" in n for n in names_es)


@pytest.mark.asyncio
async def test_list_orchestrators_unsupported_locale_406(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=1)

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators?lang=xx")
    assert resp.status_code == 406
    body = resp.json()
    assert body["error"]["code"] == "UNSUPPORTED_LOCALE"


@pytest.mark.asyncio
async def test_get_orchestrator_detail(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=3)

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators/orch-000")
    assert resp.status_code == 200
    body = resp.json()
    assert body["slug"] == "orch-000"
    assert "providers" in body


@pytest.mark.asyncio
async def test_get_orchestrator_not_found(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=1)

    app = make_app(engine)
    client = TestClient(app)
    resp = client.get("/api/v1/orchestrators/nonexistent")
    assert resp.status_code == 404
    body = resp.json()
    assert body["error"]["code"] == "NOT_FOUND"


@pytest.mark.asyncio
async def test_p95_latency_under_200ms(engine):
    """Performance gate: p95 of 20 list requests must be < 200ms."""
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        await seed_orchestrators(s, count=20)

    app = make_app(engine)
    client = TestClient(app)

    latencies = []
    for _ in range(20):
        start = time.perf_counter()
        resp = client.get("/api/v1/orchestrators?limit=10")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        latencies.append(elapsed_ms)

    p95 = sorted(latencies)[int(len(latencies) * 0.95)]
    assert p95 < 200, f"p95 latency {p95:.1f}ms exceeds 200ms SLO"
