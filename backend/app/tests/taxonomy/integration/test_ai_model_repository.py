import uuid
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import AIModel, Provider, TaxonomyVersion
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


# ---------------------------------------------------------------------------
# get_by_slug
# ---------------------------------------------------------------------------
class TestAIModelGetBySlug:
    @pytest.mark.asyncio
    async def test_get_by_slug_found(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        data = {
            "provider_id": provider.id,
            "slug": "my-model",
            "display_name": "My Model",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "slug-hash-1",
        }
        model, _ = await repo.upsert(data)
        found = await repo.get_by_slug("my-model")
        assert found is not None
        assert found.id == model.id

    @pytest.mark.asyncio
    async def test_get_by_slug_not_found(self, session):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        found = await repo.get_by_slug("nonexistent")
        assert found is None


# ---------------------------------------------------------------------------
# list — with filters
# ---------------------------------------------------------------------------
class TestAIModelList:
    @pytest.mark.asyncio
    async def test_list_all(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        for i in range(3):
            await repo.upsert({
                "provider_id": provider.id,
                "slug": f"list-m-{i}",
                "display_name": f"List M {i}",
                "modality": [],
                "status": "draft",
                "source": "manual",
                "source_payload_hash": f"list-hash-{i}",
            })
        all_models = await repo.list()
        assert len(all_models) >= 3

    @pytest.mark.asyncio
    async def test_list_by_provider_id(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        await repo.upsert({
            "provider_id": provider.id,
            "slug": "list-p-m1",
            "display_name": "List P M1",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "list-p-hash-1",
        })
        filtered = await repo.list(provider_id=provider.id)
        assert all(m.provider_id == provider.id for m in filtered)

    @pytest.mark.asyncio
    async def test_list_by_status(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        await repo.upsert({
            "provider_id": provider.id,
            "slug": "list-s-m1",
            "display_name": "List S M1",
            "modality": [],
            "status": "approved",
            "source": "manual",
            "source_payload_hash": "list-s-hash-1",
        })
        filtered = await repo.list(status="approved")
        assert all(m.status == "approved" for m in filtered)


# ---------------------------------------------------------------------------
# upsert — skip 'id' key + IntegrityError paths
# ---------------------------------------------------------------------------
class TestAIModelUpsertEdgeCases:
    @pytest.mark.asyncio
    async def test_upsert_skips_id_key(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        data = {
            "provider_id": provider.id,
            "slug": "skip-id-m",
            "display_name": "Skip ID",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "skip-id-hash",
            "id": "should-be-ignored",
        }
        model, created = await repo.upsert(data)
        assert created is True
        assert model.id != "should-be-ignored"

    @pytest.mark.asyncio
    async def test_upsert_existing_integrity_error(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        data = {
            "provider_id": provider.id,
            "slug": "integrity-existing",
            "display_name": "Integrity Existing",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "integrity-existing-hash",
        }
        model, _ = await repo.upsert(data)

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.upsert({**data, "display_name": "Updated"})
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_upsert_create_race_condition_finds_existing(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        data = {
            "provider_id": provider.id,
            "slug": "race-model",
            "display_name": "Race Model",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "race-hash",
        }
        # Create the model first so _find_existing can find it
        model1, _ = await repo.upsert(data)

        find_call = 0
        original_find = repo._find_existing
        original_flush = session.flush
        flush_call = 0

        async def race_find_existing(d):
            nonlocal find_call
            find_call += 1
            if find_call == 1:
                # First call in upsert() at line 75 — return None to go to create branch
                return None
            # Second call at line 128 (after IntegrityError) — return existing
            return await original_find(d)

        async def fail_first_flush():
            nonlocal flush_call
            flush_call += 1
            if flush_call == 1:
                raise SAIntegrityError("stmt", "params", Exception())
            return await original_flush()

        with patch.object(repo, "_find_existing", side_effect=race_find_existing):
            with patch.object(session, "flush", side_effect=fail_first_flush):
                model2, created = await repo.upsert(data)
                assert created is False
                assert model2.id == model1.id

    @pytest.mark.asyncio
    async def test_upsert_create_conflict_no_existing(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        data = {
            "provider_id": provider.id,
            "slug": "conflict-noexist",
            "display_name": "Conflict NoExist",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "conflict-noexist-hash",
        }

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with patch.object(repo, "_find_existing", return_value=None):
                with pytest.raises(DomainError) as exc:
                    await repo.upsert(data)
                assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------
class TestAIModelDelete:
    @pytest.mark.asyncio
    async def test_delete_success(self, session, provider):
        from app.taxonomy.repositories.ai_model import AIModelRepository
        repo = AIModelRepository(session)
        model, _ = await repo.upsert({
            "provider_id": provider.id,
            "slug": "del-model",
            "display_name": "Del Model",
            "modality": [],
            "status": "draft",
            "source": "manual",
            "source_payload_hash": "del-hash",
        })
        await repo.delete(model)
        found = await repo.get(model.id)
        assert found is None
