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
from app.taxonomy.models.entities import TaxonomyVersion
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
# create — IntegrityError
# ---------------------------------------------------------------------------
class TestTaxonomyVersionCreateErrors:
    @pytest.mark.asyncio
    async def test_create_integrity_error(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(session)

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.create(version="v-dup")
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_duplicate_version(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(session)
        await repo.create(version="v-dup-2")
        with pytest.raises(DomainError) as exc:
            await repo.create(version="v-dup-2")
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# activate — not found
# ---------------------------------------------------------------------------
class TestTaxonomyVersionActivateErrors:
    @pytest.mark.asyncio
    async def test_activate_not_found(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.activate(str(uuid.uuid4()))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_activate_integrity_error(self, session):
        from app.taxonomy.repositories.taxonomy_version import TaxonomyVersionRepository
        repo = TaxonomyVersionRepository(session)
        v2 = await repo.create(version="v-int-act")

        original_flush = session.flush

        async def fail_flush():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=fail_flush):
            with pytest.raises(DomainError) as exc:
                await repo.activate(v2.id)
            assert exc.value.status_code == 409
