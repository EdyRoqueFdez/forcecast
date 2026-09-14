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
from app.taxonomy.models.entities import Provider, ProviderTranslation, TaxonomyVersion
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


# ---------------------------------------------------------------------------
# list — with status filter
# ---------------------------------------------------------------------------
class TestProviderList:
    @pytest.mark.asyncio
    async def test_list_all(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        await repo.create(slug="prov-a", name="Prov A")
        await repo.create(slug="prov-b", name="Prov B")
        all_providers = await repo.list()
        assert len(all_providers) >= 2

    @pytest.mark.asyncio
    async def test_list_by_status(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        await repo.create(slug="prov-active", name="Prov Active", status="active")
        await repo.create(slug="prov-deprecated", name="Prov Deprecated", status="deprecated")
        active = await repo.list(status="active")
        assert all(p.status == "active" for p in active)
        deprecated = await repo.list(status="deprecated")
        assert all(p.status == "deprecated" for p in deprecated)


# ---------------------------------------------------------------------------
# update — slug normalization + IntegrityError
# ---------------------------------------------------------------------------
class TestProviderUpdate:
    @pytest.mark.asyncio
    async def test_update_slug_normalized(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-upd", name="Prov Upd")
        updated = await repo.update(provider, slug="  My New Slug  ")
        assert updated.slug == "my-new-slug"

    @pytest.mark.asyncio
    async def test_update_integrity_error(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-int", name="Prov Int")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.update(provider, name="Prov Int Updated")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# delete — IntegrityError
# ---------------------------------------------------------------------------
class TestProviderDelete:
    @pytest.mark.asyncio
    async def test_delete_integrity_error(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-del-int", name="Prov Del Int")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.delete(provider)
            assert exc.value.status_code == 409
            assert "delete" in str(exc.value).lower() or "associated" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# upsert_translation — IntegrityError on new translation
# ---------------------------------------------------------------------------
class TestProviderUpsertTranslationErrors:
    @pytest.mark.asyncio
    async def test_upsert_translation_new_integrity_error(self, session):
        from app.taxonomy.repositories.provider import ProviderRepository
        repo = ProviderRepository(session)
        provider = await repo.create(slug="prov-trans-int", name="Prov Trans Int")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.upsert_translation(provider.id, locale="fr", name="French Name")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()
