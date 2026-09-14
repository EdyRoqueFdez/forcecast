"""Phase 4.3 — Taxonomy Versioning Service (TDD RED)."""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from sqlalchemy import event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import TaxonomyVersion, Category

@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    @event.listens_for(eng.sync_engine, "connect")
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
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        yield s
        await s.rollback()


class TestVersioningService:
    @pytest.mark.asyncio
    async def test_create_version_copies_current_tree(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        # Setup: create v1 current with 3 categories
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        # Add categories for v1
        c1 = Category(slug="coding", taxonomy_version="v1")
        session.add(c1)
        await session.flush()
        await session.commit()
        await session.refresh(c1)
        c2 = Category(slug="debugging", parent_id=None, taxonomy_version="v1")
        session.add(c2)
        await session.flush()
        await session.commit()
        # Create version v2 copying from v1
        v2 = await svc.create_version(version="v2", notes="Added agentic_workflows")
        assert v2.version == "v2"
        assert v2.is_current is False
        # v2 should have copied categories from v1
        from sqlalchemy import select
        v2_cats = (await session.execute(select(Category).where(Category.taxonomy_version == "v2"))).scalars().all()
        v1_cats = (await session.execute(select(Category).where(Category.taxonomy_version == "v1"))).scalars().all()
        assert len(v2_cats) == len(v1_cats), f"Expected {len(v1_cats)} copied categories, got {len(v2_cats)}"
        # Check that translations were also copied (if any) - at least structure preserved
        slugs_v1 = {c.slug for c in v1_cats}
        slugs_v2 = {c.slug for c in v2_cats}
        assert slugs_v1 == slugs_v2

    @pytest.mark.asyncio
    async def test_activate_version_atomic_swap(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        v2 = TaxonomyVersion(version="v2", released_at=datetime.now(timezone.utc), is_current=False)
        session.add_all([v1, v2])
        await session.commit()
        await session.refresh(v1)
        await session.refresh(v2)
        # Activate v2
        activated = await svc.activate_version(v2.id)
        assert activated.is_current is True
        assert activated.version == "v2"
        # v1 must be deactivated atomically
        await session.refresh(v1)
        assert v1.is_current is False
        # Verify exactly one current
        from sqlalchemy import select
        currents = (await session.execute(select(TaxonomyVersion).where(TaxonomyVersion.is_current == True))).scalars().all()  # noqa: E712
        assert len(currents) == 1
        assert currents[0].version == "v2"

    @pytest.mark.asyncio
    async def test_activate_already_current_idempotent(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.commit()
        await session.refresh(v1)
        result = await svc.activate_version(v1.id)
        assert result.is_current is True
        # Second activation should still succeed idempotently
        result2 = await svc.activate_version(v1.id)
        assert result2.is_current is True
        assert result2.id == v1.id

    @pytest.mark.asyncio
    async def test_create_duplicate_version_rejected_409(self, session):
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.commit()
        with pytest.raises(DomainError) as exc:
            await svc.create_version(version="v1", notes="dup")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_activate_not_found_404(self, session):
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        with pytest.raises(DomainError) as exc:
            await svc.activate_version("00000000-0000-0000-0000-000000000000")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_historical_version_immutability(self, session):
        """Updating categories of non-current version should be blocked (409)."""
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        cat = Category(slug="coding", taxonomy_version="v1")
        session.add(cat)
        await session.flush()
        await session.commit()
        # Create v2 and activate it, making v1 historical
        v2 = await svc.create_version(version="v2", notes="new")
        await svc.activate_version(v2.id)
        # Attempt to update historical category - should be blocked by service layer check
        with pytest.raises(DomainError) as exc:
            await svc.update_category(cat.id, slug="coding-updated")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_copy_tree_preserves_translations(self, session):
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.models.entities import CategoryTranslation
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        cat = Category(slug="coding", taxonomy_version="v1")
        session.add(cat)
        await session.flush()
        await session.commit()
        await session.refresh(cat)
        trans = CategoryTranslation(category_id=cat.id, locale="es", name="Programación", description="Desc")
        session.add(trans)
        await session.flush()
        await session.commit()
        v2 = await svc.create_version(version="v2", notes="copy trans")
        # v2 should have a category with same slug and translation copied
        from sqlalchemy import select
        v2_cats = (await session.execute(select(Category).where(Category.taxonomy_version == "v2", Category.slug == "coding"))).scalars().all()
        assert len(v2_cats) == 1
        v2_cat = v2_cats[0]
        v2_trans = (await session.execute(select(CategoryTranslation).where(CategoryTranslation.category_id == v2_cat.id, CategoryTranslation.locale == "es"))).scalars().all()
        assert len(v2_trans) == 1
        assert v2_trans[0].name == "Programación"


class TestVersioningEdgeCases:
    @pytest.mark.asyncio
    async def test_create_version_flush_integrity_error(self, session):
        from unittest.mock import AsyncMock, patch
        from sqlalchemy.exc import IntegrityError
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        with patch.object(session, 'flush', new_callable=AsyncMock, side_effect=IntegrityError("dup", None, None)):
            with pytest.raises(DomainError) as exc:
                await svc.create_version(version="v1", notes="flush error")
            assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_version_commit_integrity_error(self, session):
        from unittest.mock import AsyncMock
        from sqlalchemy.exc import IntegrityError
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        original_flush = session.flush
        original_commit = session.commit

        async def mock_commit():
            raise IntegrityError("dup", None, None)

        session.commit = mock_commit
        with pytest.raises(DomainError) as exc:
            await svc.create_version(version="v1", notes="commit error")
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_version_no_current_no_tree_copy(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = await svc.create_version(version="v1", notes="first")
        assert v1.version == "v1"
        from sqlalchemy import select
        cats = (await session.execute(select(Category).where(Category.taxonomy_version == "v1"))).scalars().all()
        assert len(cats) == 0

    @pytest.mark.asyncio
    async def test_copy_tree_empty_categories(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        v2 = await svc.create_version(version="v2", notes="copy empty")
        assert v2.version == "v2"
        from sqlalchemy import select
        v2_cats = (await session.execute(select(Category).where(Category.taxonomy_version == "v2"))).scalars().all()
        assert len(v2_cats) == 0

    @pytest.mark.asyncio
    async def test_copy_tree_with_parent_id_mapping(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        parent = Category(slug="parent", taxonomy_version="v1")
        session.add(parent)
        await session.flush()
        await session.commit()
        await session.refresh(parent)
        child = Category(slug="child", parent_id=parent.id, taxonomy_version="v1")
        session.add(child)
        await session.flush()
        await session.commit()
        v2 = await svc.create_version(version="v2", notes="with parent")
        from sqlalchemy import select
        v2_parent = (await session.execute(select(Category).where(Category.taxonomy_version == "v2", Category.slug == "parent"))).scalar_one()
        v2_child = (await session.execute(select(Category).where(Category.taxonomy_version == "v2", Category.slug == "child"))).scalar_one()
        assert v2_child.parent_id == v2_parent.id

    @pytest.mark.asyncio
    async def test_activate_version_integrity_error(self, session):
        from unittest.mock import AsyncMock
        from sqlalchemy.exc import IntegrityError
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        v2 = TaxonomyVersion(version="v2", released_at=datetime.now(timezone.utc), is_current=False)
        session.add_all([v1, v2])
        await session.commit()
        await session.refresh(v2)

        original_execute = session.execute
        call_count = 0

        async def mock_execute(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return await original_execute(*args, **kwargs)
            raise IntegrityError("conflict", None, None)

        session.execute = mock_execute
        with pytest.raises(DomainError) as exc:
            await svc.activate_version(v2.id)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, session):
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        with pytest.raises(DomainError) as exc:
            await svc.update_category("00000000-0000-0000-0000-000000000000", slug="x")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_category_no_current_version(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v99 = TaxonomyVersion(version="v99", released_at=datetime.now(timezone.utc), is_current=False)
        session.add(v99)
        await session.flush()
        await session.commit()
        cat = Category(slug="coding", taxonomy_version="v99")
        session.add(cat)
        await session.flush()
        await session.commit()
        await session.refresh(cat)
        updated = await svc.update_category(cat.id, slug="New Slug!")
        assert updated.slug == "new-slug"

    @pytest.mark.asyncio
    async def test_update_category_with_status_and_parent(self, session):
        from app.taxonomy.services.versioning import VersioningService
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        parent = Category(slug="parent", taxonomy_version="v1")
        session.add(parent)
        await session.flush()
        await session.commit()
        await session.refresh(parent)
        child = Category(slug="child", taxonomy_version="v1")
        session.add(child)
        await session.flush()
        await session.commit()
        await session.refresh(child)
        updated = await svc.update_category(child.id, slug="child-updated", status="deprecated", parent_id=parent.id)
        assert updated.slug == "child-updated"
        assert updated.status == "deprecated"
        assert updated.parent_id == parent.id

    @pytest.mark.asyncio
    async def test_update_category_integrity_error(self, session):
        from unittest.mock import AsyncMock
        from sqlalchemy.exc import IntegrityError
        from app.taxonomy.services.versioning import VersioningService
        from app.taxonomy.services.core import DomainError
        svc = VersioningService(session)
        v1 = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        session.add(v1)
        await session.flush()
        await session.commit()
        cat = Category(slug="coding", taxonomy_version="v1")
        session.add(cat)
        await session.flush()
        await session.commit()
        await session.refresh(cat)

        original_flush = session.flush
        async def mock_flush():
            raise IntegrityError("conflict", None, None)
        session.flush = mock_flush
        with pytest.raises(DomainError) as exc:
            await svc.update_category(cat.id, slug="new-slug")
        assert exc.value.status_code == 409
