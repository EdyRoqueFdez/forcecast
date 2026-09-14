"""Coverage boost for admin.py — error paths, deprecate endpoint, exception handlers."""
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio
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
            email="admin_cov@test.com",
            display_name="Admin Cov",
            role=RoleEnum.ADMIN,
            reputation_score=5.0,
            email_verified=True,
        )
        s.add(user)
        await s.commit()
        await s.refresh(user)
        token = create_access_token(str(user.id), "admin")
        yield token, user


def make_admin_app(engine):
    app = FastAPI()
    app.include_router(admin_router, prefix="/api/v1")

    async def override_get_session():
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with async_session() as s:
            yield s

    app.dependency_overrides[get_session] = override_get_session
    return app


# ---------------------------------------------------------------------------
# approve_model error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_approve_model_not_found(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{uuid.uuid4()}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_approve_model_not_pending_review(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-approve-ntpr", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-approve-ntpr",
                "display_name": "Model NTPR",
                "modality": ["text"],
                "status": "approved",
                "source": "manual",
                "source_payload_hash": f"hash-ntpr-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{model_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approve_model_missing_required_fields(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-mrf", name="Prov MRF")
        model = AIModel(
            id=str(uuid.uuid4()),
            provider_id=provider.id,
            slug="model-mrf",
            display_name="MRF",
            modality=[],
            status="pending_review",
            source="manual",
            source_payload_hash=f"hash-mrf-{uuid.uuid4()}",
        )
        s.add(model)
        await s.commit()
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{model_id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_approve_model_clear_cache_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-cc-err", name="Prov CC")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-cc-err",
                "display_name": "Model CC",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-cc-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.services.public.clear_cache", side_effect=RuntimeError("cache fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_approve_model_webhook_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-wh-err", name="Prov WH")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-wh-err",
                "display_name": "Model WH",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-wh-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.admin.WebhookService", side_effect=RuntimeError("webhook fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/approve",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# reject_model error paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reject_model_not_found(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{uuid.uuid4()}/reject",
        json={"reason": "test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_reject_model_not_pending_review(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-rej-ntpr", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-rej-ntpr",
                "display_name": "Reject NTPR",
                "modality": ["text"],
                "status": "approved",
                "source": "manual",
                "source_payload_hash": f"hash-rej-ntpr-{uuid.uuid4()}",
            }
        )
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{model_id}/reject",
        json={"reason": "no"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reject_model_clear_cache_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-rej-cc", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-rej-cc",
                "display_name": "Reject CC",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-rej-cc-{uuid.uuid4()}",
            }
        )
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.services.public.clear_cache", side_effect=RuntimeError("cache fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/reject",
            json={"reason": "bad"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_reject_model_webhook_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-rej-wh", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-rej-wh",
                "display_name": "Reject WH",
                "modality": ["text"],
                "status": "pending_review",
                "source": "manual",
                "source_payload_hash": f"hash-rej-wh-{uuid.uuid4()}",
            }
        )
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.admin.WebhookService", side_effect=RuntimeError("webhook fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/reject",
            json={"reason": "bad"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# deprecate_model — entirely untested (lines 199-230)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deprecate_model_success(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-dep", name="Prov Dep")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-dep",
                "display_name": "Model Dep",
                "modality": ["text"],
                "status": "approved",
                "source": "manual",
                "source_payload_hash": f"hash-dep-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{model_id}/deprecate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_deprecate_model_not_found(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{uuid.uuid4()}/deprecate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_deprecate_model_not_approved(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-dep-na", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-dep-na",
                "display_name": "Dep NA",
                "modality": ["text"],
                "status": "draft",
                "source": "manual",
                "source_payload_hash": f"hash-dep-na-{uuid.uuid4()}",
            }
        )
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/models/{model_id}/deprecate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_deprecate_model_clear_cache_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-dep-cc", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-dep-cc",
                "display_name": "Dep CC",
                "modality": ["text"],
                "status": "approved",
                "source": "manual",
                "source_payload_hash": f"hash-dep-cc-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.services.public.clear_cache", side_effect=RuntimeError("cache fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/deprecate",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_deprecate_model_webhook_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        from app.taxonomy.repositories.provider import ProviderRepository
        from app.taxonomy.repositories.ai_model import AIModelRepository
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository

        prov_repo = ProviderRepository(s)
        provider = await prov_repo.create(slug="prov-dep-wh", name="Prov")
        ai_repo = AIModelRepository(s)
        model, _ = await ai_repo.upsert(
            {
                "provider_id": provider.id,
                "slug": "model-dep-wh",
                "display_name": "Dep WH",
                "modality": ["text"],
                "status": "approved",
                "source": "manual",
                "source_payload_hash": f"hash-dep-wh-{uuid.uuid4()}",
            }
        )
        host_repo = ModelHostingRepository(s)
        await host_repo.create(model_id=model.id, provider_id=provider.id, is_primary=True)
        model_id = model.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.admin.WebhookService", side_effect=RuntimeError("webhook fail")):
        resp = client.post(
            f"/api/v1/admin/models/{model_id}/deprecate",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# create_version DomainError (lines 246-247)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_version_duplicate(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp1 = client.post(
        "/api/v1/admin/taxonomy/versions",
        json={"version": "v-dup", "notes": "first"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp1.status_code in (200, 201)
    resp2 = client.post(
        "/api/v1/admin/taxonomy/versions",
        json={"version": "v-dup", "notes": "second"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 409


# ---------------------------------------------------------------------------
# activate_version DomainError (lines 264-265)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_activate_version_not_found(engine, admin_token):
    token, _ = admin_token
    app = make_admin_app(engine)
    client = TestClient(app)
    resp = client.post(
        f"/api/v1/admin/taxonomy/versions/{uuid.uuid4()}/activate",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_activate_version_clear_cache_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        tv1 = TaxonomyVersion(id=str(uuid.uuid4()), version="v1-act-cc", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(tv1)
        await s.commit()
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(s)
        v2 = await repo.create(version="v2-act-cc", notes="test")
        v2_id = v2.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.services.public.clear_cache", side_effect=RuntimeError("cache fail")):
        resp = client.post(
            f"/api/v1/admin/taxonomy/versions/{v2_id}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_activate_version_webhook_exception(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        tv1 = TaxonomyVersion(id=str(uuid.uuid4()), version="v1-act-wh", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(tv1)
        await s.commit()
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(s)
        v2 = await repo.create(version="v2-act-wh", notes="test")
        v2_id = v2.id

    app = make_admin_app(engine)
    client = TestClient(app)
    with patch("app.taxonomy.api.admin.WebhookService", side_effect=RuntimeError("webhook fail")):
        resp = client.post(
            f"/api/v1/admin/taxonomy/versions/{v2_id}/activate",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# trigger_ingestion DomainError from create_run (lines 76-77)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_trigger_ingestion_domain_error(engine, admin_token):
    token, _ = admin_token
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        src = IngestionSource(code="err-src", name="Err", parser_class="P", rate_limit_rpm=60)
        s.add(src)
        await s.commit()

    app = make_admin_app(engine)
    client = TestClient(app)
    from app.taxonomy.services.core import DomainError as DE

    with patch(
        "app.taxonomy.api.admin.IngestionRepository.create_run",
        side_effect=DE("lock busy", status_code=409),
    ):
        resp = client.post(
            "/api/v1/admin/ingestion/run",
            json={"source": "err-src"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409
