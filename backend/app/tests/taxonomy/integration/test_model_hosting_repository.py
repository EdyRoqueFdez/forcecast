import uuid
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import (
    AIModel,
    ModelHosting,
    Provider,
    TaxonomyVersion,
)
from app.taxonomy.services.core import DomainError


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
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


@pytest_asyncio.fixture
async def provider(session):
    p = Provider(
        id=str(uuid.uuid4()), slug="test-prov", name="Test Prov",
        status="active", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    session.add(p)
    await session.commit()
    return p


@pytest_asyncio.fixture
async def model(session, provider):
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=provider.id, slug="test-model",
        display_name="Test Model", modality=[], status="draft", source="manual",
        source_payload_hash="hash-test", created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
    )
    session.add(m)
    await session.commit()
    return m


# ---------------------------------------------------------------------------
# create() — IntegrityError
# ---------------------------------------------------------------------------
class TestModelHostingCreateErrors:
    @pytest.mark.asyncio
    async def test_create_integrity_error(self, session, model, provider):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        repo = ModelHostingRepository(session)

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.create(model_id=model.id, provider_id=provider.id)
            assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------
class TestModelHostingUpdate:
    @pytest.mark.asyncio
    async def test_update_success(self, session, model, provider):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        repo = ModelHostingRepository(session)
        hosting = await repo.create(model_id=model.id, provider_id=provider.id, is_primary=False)
        updated = await repo.update(hosting, endpoint_url="https://new-endpoint.com", is_primary=True)
        assert updated.endpoint_url == "https://new-endpoint.com"
        assert updated.is_primary is True
        assert updated.updated_at is not None

    @pytest.mark.asyncio
    async def test_update_integrity_error(self, session, model, provider):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        repo = ModelHostingRepository(session)
        hosting = await repo.create(model_id=model.id, provider_id=provider.id, is_primary=False)

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.update(hosting, endpoint_url="https://fail.com")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------
class TestModelHostingDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, session, model, provider):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        repo = ModelHostingRepository(session)
        hosting = await repo.create(model_id=model.id, provider_id=provider.id, is_primary=False)
        await repo.delete(hosting)
        fetched = await repo.get(hosting.id)
        assert fetched is None


# ---------------------------------------------------------------------------
# set_primary — IntegrityError
# ---------------------------------------------------------------------------
class TestModelHostingSetPrimaryErrors:
    @pytest.mark.asyncio
    async def test_set_primary_integrity_error(self, session, model, provider):
        from app.taxonomy.repositories.model_hosting import ModelHostingRepository
        repo = ModelHostingRepository(session)
        hosting = await repo.create(model_id=model.id, provider_id=provider.id, is_primary=False)

        original_flush = session.flush

        async def fail_on_second_flush():
            """Let first execute calls succeed (SELECT), fail on flush inside try block."""
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=fail_on_second_flush):
            with pytest.raises(DomainError) as exc:
                await repo.set_primary(model.id, hosting.id)
            assert exc.value.status_code == 409
