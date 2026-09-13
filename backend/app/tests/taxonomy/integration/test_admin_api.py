"""Phase 6.3 — Admin API Endpoints (7 endpoints) — TDD RED"""
import pytest
import pytest_asyncio
import uuid
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base, get_session
from app.auth.services.jwt import create_access_token
from app.auth.models.user import User, RoleEnum
from app.taxonomy.api.admin import router as admin_router
from app.taxonomy.models.entities import IngestionSource, AIModel, TaxonomyVersion


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


@pytest_asyncio.fixture
async def admin_token(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="admin_api@test.com",
            display_name="Admin API",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        token = create_access_token(str(user.id), "admin")
        yield token, user


@pytest_asyncio.fixture
async def user_token(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        user = User(
            id=str(uuid.uuid4()),
            email="user_api@test.com",
            display_name="User API",
            role=RoleEnum.USER,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        token = create_access_token(str(user.id), "user")
        yield token


def make_admin_app(engine):
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")

    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    return app


@pytest.mark.asyncio
async def test_trigger_ingestion_success(engine, admin_token):
    token, _ = admin_token
    # Seed source
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        src = IngestionSource(code="openrouter", name="OpenRouter", parser_class="OpenRouterParser", rate_limit_rpm=60)
        s.add(src)
        await s.commit()

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post("/api/v1/admin/ingestion/run", json={"source": "openrouter"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    body = resp.json()
    # Expect run id and status running
    assert "id" in body or "run_id" in body or "source" in body
    # if response wraps under data
    if "id" not in body:
        assert "data" in body or "run" in body


@pytest.mark.asyncio
async def test_trigger_ingestion_invalid_source_returns_422(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post("/api/v1/admin/ingestion/run", json={"source": "nonexistent"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approve_model_success(engine, admin_token):
    token, admin_user = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-approve", name="Prov Approve")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-approve",
                "display_name": "Model Approve",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-approve-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(f"/api/v1/admin/models/{model_id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved" or resp.json().get("data", {}).get("status") == "approved"


@pytest.mark.asyncio
async def test_approve_model_without_hosting_returns_422(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-approve2", name="Prov Approve2")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-approve-fail",
                "display_name": "Model Fail",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-fail-{uuid.uuid4()}",
            }
        )
        model_id = model.id
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(f"/api/v1/admin/models/{model_id}/approve", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reject_model_success(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-reject", name="Prov Reject")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-reject",
                "display_name": "Model Reject",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-reject-{uuid.uuid4()}",
            }
        )
        model_id = model.id
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(f"/api/v1/admin/models/{model_id}/reject", json={"reason": "Duplicate of claude"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    status = data.get("status") or data.get("data", {}).get("status")
    assert status == "rejected"


@pytest.mark.asyncio
async def test_create_version_success(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post("/api/v1/admin/taxonomy/versions", json={"version": "v2", "notes": "test notes"}, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code in (200, 201)
    body = resp.json()
    version = body.get("version") or body.get("data", {}).get("version")
    assert version == "v2"
    assert body.get("is_current") is False or body.get("data", {}).get("is_current") is False


@pytest.mark.asyncio
async def test_activate_version_success(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        # Ensure v1 is_current True (fixture seeds v1? Our engine fixture doesn't seed v1 except our previous tests. We'll create both)
        existing = await s.execute(sa_text("SELECT version FROM taxonomy_versions WHERE version='v1'"))
        rows = existing.fetchall()
        if not rows:
            tv1 = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", released_at=datetime.now(timezone.utc), is_current=True)
            s.add(tv1)
            await s.commit()
        # Create v2 via repo
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository

        repo = TaxonomyVersionRepository(s)
        v2 = await repo.create(version="v2-activate", notes="to activate")
        v2_id = v2.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(f"/api/v1/admin/taxonomy/versions/{v2_id}/activate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    # Should be current now
    is_current = body.get("is_current") or body.get("data", {}).get("is_current")
    assert is_current is True


@pytest.mark.asyncio
async def test_register_webhook_success(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/hook", "events": ["model.approved"], "secret": "supersecret"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert body.get("url") == "https://example.com/hook" or body.get("data", {}).get("url") == "https://example.com/hook"
    assert body.get("is_active") is True or body.get("data", {}).get("is_active") is True


@pytest.mark.asyncio
async def test_register_webhook_invalid_events_returns_422(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        "/api/v1/admin/webhooks",
        json={"url": "https://example.com/bad", "events": ["invalid.event"], "secret": "s"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_auth_missing_returns_401(engine):
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post("/api/v1/admin/ingestion/run", json={"source": "openrouter"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_auth_non_admin_returns_403(engine, user_token):
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post("/api/v1/admin/ingestion/run", json={"source": "openrouter"}, headers={"Authorization": f"Bearer {user_token}"})
    assert resp.status_code == 403
