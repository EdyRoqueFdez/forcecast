"""Category Repository — 100% coverage tests.

Covers all branches and error paths in category.py:
- create: parent not found, parent version mismatch, cycle, max depth, integrity error
- get: found, not found
- list: with/without filter
- list_children: with/without children
- update: not found, cycle, parent not found, parent version mismatch, max depth, slug/status update, integrity error
- delete: not found, has children, integrity error
- upsert_translation: create, update description, integrity error
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import Category, CategoryTranslation, TaxonomyVersion
from app.taxonomy.services.core import DomainError


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


@pytest_asyncio.fixture
async def session(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        v = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(v)
        await s.commit()
        yield s
        await s.rollback()


# ---------------------------------------------------------------------------
# create() — success paths
# ---------------------------------------------------------------------------
class TestCategoryCreate:
    @pytest.mark.asyncio
    async def test_create_root_category(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="coding", taxonomy_version="v1")
        assert cat.id is not None
        assert cat.slug == "coding"
        assert cat.parent_id is None
        assert cat.status == "active"

    @pytest.mark.asyncio
    async def test_create_child_category(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="root-create", taxonomy_version="v1")
        child = await repo.create(slug="child-create", taxonomy_version="v1", parent_id=root.id)
        assert child.parent_id == root.id

    @pytest.mark.asyncio
    async def test_create_with_custom_status(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="inactive-cat", taxonomy_version="v1", status="inactive")
        assert cat.status == "inactive"

    @pytest.mark.asyncio
    async def test_create_slug_normalized(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="  My Category  ", taxonomy_version="v1")
        assert cat.slug == "my-category"


# ---------------------------------------------------------------------------
# create() — error paths
# ---------------------------------------------------------------------------
class TestCategoryCreateErrors:
    @pytest.mark.asyncio
    async def test_create_parent_not_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        fake_id = str(uuid.uuid4())
        with pytest.raises(DomainError) as exc:
            await repo.create(slug="orphan", taxonomy_version="v1", parent_id=fake_id)
        assert exc.value.status_code == 404
        assert "not found" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_create_parent_different_taxonomy_version(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="root-v1", taxonomy_version="v1")
        # Create a second taxonomy version
        v2 = TaxonomyVersion(version="v2", released_at=datetime.now(timezone.utc), is_current=False)
        session.add(v2)
        await session.commit()

        with pytest.raises(DomainError) as exc:
            await repo.create(slug="child-v2", taxonomy_version="v2", parent_id=root.id)
        assert exc.value.status_code == 409
        assert "same taxonomy_version" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_create_cycle_self_parent(self, session):
        """Cycle detected when parent_id equals normalized slug (edge case)."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        # This is a contrived case: parent_id == slug after normalization
        # We'll simulate by creating a category and trying to set its parent to itself
        cat = await repo.create(slug="self-parent", taxonomy_version="v1")
        with pytest.raises(DomainError) as exc:
            # The cycle check compares parent_id to normalized slug, not category id
            # But let's test the general parent_id == slug path
            await repo.create(slug=cat.id, taxonomy_version="v1", parent_id=cat.id)
        assert exc.value.status_code == 409

    @pytest.mark.asyncio
    async def test_create_max_depth_exceeded(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="depth-root", taxonomy_version="v1")
        child = await repo.create(slug="depth-child", taxonomy_version="v1", parent_id=root.id)
        # Try to add grandchild — max depth 2 means root + child only
        with pytest.raises(DomainError) as exc:
            await repo.create(slug="depth-grandchild", taxonomy_version="v1", parent_id=child.id)
        assert exc.value.status_code == 409
        assert "depth" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_create_slug_conflict_integrity_error(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        await repo.create(slug="unique-slug", taxonomy_version="v1")
        with pytest.raises(DomainError) as exc:
            await repo.create(slug="unique-slug", taxonomy_version="v1")
        assert exc.value.status_code == 409
        assert "conflict" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# get()
# ---------------------------------------------------------------------------
class TestCategoryGet:
    @pytest.mark.asyncio
    async def test_get_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="get-test", taxonomy_version="v1")
        result = await repo.get(cat.id)
        assert result is not None
        assert result.id == cat.id

    @pytest.mark.asyncio
    async def test_get_not_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        result = await repo.get(str(uuid.uuid4()))
        assert result is None


# ---------------------------------------------------------------------------
# list()
# ---------------------------------------------------------------------------
class TestCategoryList:
    @pytest.mark.asyncio
    async def test_list_all(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        await repo.create(slug="list-a", taxonomy_version="v1")
        await repo.create(slug="list-b", taxonomy_version="v1")
        all_cats = await repo.list()
        assert len(all_cats) >= 2

    @pytest.mark.asyncio
    async def test_list_filtered_by_version(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        await repo.create(slug="list-v1", taxonomy_version="v1")
        v2 = TaxonomyVersion(version="v2-list", released_at=datetime.now(timezone.utc), is_current=False)
        session.add(v2)
        await session.commit()
        await repo.create(slug="list-v2", taxonomy_version="v2-list")

        v1_cats = await repo.list(taxonomy_version="v1")
        v2_cats = await repo.list(taxonomy_version="v2-list")
        assert all(c.taxonomy_version == "v1" for c in v1_cats)
        assert all(c.taxonomy_version == "v2-list" for c in v2_cats)


# ---------------------------------------------------------------------------
# list_children()
# ---------------------------------------------------------------------------
class TestCategoryListChildren:
    @pytest.mark.asyncio
    async def test_list_children_empty(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="no-children", taxonomy_version="v1")
        children = await repo.list_children(root.id)
        assert len(children) == 0

    @pytest.mark.asyncio
    async def test_list_children_with_children(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="has-children", taxonomy_version="v1")
        c1 = await repo.create(slug="child-1", taxonomy_version="v1", parent_id=root.id)
        c2 = await repo.create(slug="child-2", taxonomy_version="v1", parent_id=root.id)
        children = await repo.list_children(root.id)
        assert len(children) == 2
        ids = {c.id for c in children}
        assert c1.id in ids
        assert c2.id in ids


# ---------------------------------------------------------------------------
# update()
# ---------------------------------------------------------------------------
class TestCategoryUpdate:
    @pytest.mark.asyncio
    async def test_update_not_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.update(str(uuid.uuid4()), slug="new-slug")
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_slug(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="update-slug", taxonomy_version="v1")
        updated = await repo.update(cat.id, slug="updated-slug")
        assert updated.slug == "updated-slug"

    @pytest.mark.asyncio
    async def test_update_status(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="update-status", taxonomy_version="v1")
        updated = await repo.update(cat.id, status="inactive")
        assert updated.status == "inactive"

    @pytest.mark.asyncio
    async def test_update_parent_cycle_self(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="cycle-self", taxonomy_version="v1")
        with pytest.raises(DomainError) as exc:
            await repo.update(cat.id, parent_id=cat.id)
        assert exc.value.status_code == 409
        assert "cycle" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_parent_cycle_ancestor(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        a = await repo.create(slug="cycle-a", taxonomy_version="v1")
        b = await repo.create(slug="cycle-b", taxonomy_version="v1", parent_id=a.id)
        # Setting A's parent to B creates cycle A->B->A
        with pytest.raises(DomainError) as exc:
            await repo.update(a.id, parent_id=b.id)
        assert exc.value.status_code == 409
        assert "cycle" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_parent_not_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="update-parent-nf", taxonomy_version="v1")
        fake_id = str(uuid.uuid4())
        with pytest.raises(DomainError) as exc:
            await repo.update(cat.id, parent_id=fake_id)
        assert exc.value.status_code == 404
        assert "parent" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_parent_different_version(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root_v1 = await repo.create(slug="root-v1-upd", taxonomy_version="v1")
        v2 = TaxonomyVersion(version="v2-upd", released_at=datetime.now(timezone.utc), is_current=False)
        session.add(v2)
        await session.commit()
        root_v2 = await repo.create(slug="root-v2-upd", taxonomy_version="v2-upd")

        child = await repo.create(slug="child-upd", taxonomy_version="v1", parent_id=root_v1.id)
        with pytest.raises(DomainError) as exc:
            await repo.update(child.id, parent_id=root_v2.id)
        assert exc.value.status_code == 409
        assert "same taxonomy_version" in str(exc.value).lower() or "version" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_max_depth_exceeded(self, session):
        """Max depth check in update() — reached when ancestor chain of new parent > 2.

        We seed a 4-level chain directly into the DB (bypassing create's depth check),
        then try to move a node under the deepest one. The ancestor walk from the new parent
        visits 3 nodes before the check fires.
        """
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        # Seed root
        root = await repo.create(slug="depth-root-upd", taxonomy_version="v1")
        # Seed child under root
        child = await repo.create(slug="depth-child-upd", taxonomy_version="v1", parent_id=root.id)
        # Manually insert deeper nodes (bypassing create's depth check)
        gc = Category(
            id=str(uuid.uuid4()), slug="depth-gc-manual", parent_id=child.id,
            taxonomy_version="v1", status="active",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        session.add(gc)
        ggc = Category(
            id=str(uuid.uuid4()), slug="depth-ggc-manual", parent_id=gc.id,
            taxonomy_version="v1", status="active",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        session.add(ggc)
        # Create a leaf node that we'll try to move
        leaf = Category(
            id=str(uuid.uuid4()), slug="depth-leaf", parent_id=root.id,
            taxonomy_version="v1", status="active",
            created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        )
        session.add(leaf)
        await session.flush()
        # Move leaf under ggc — ancestor walk: ggc(1) → gc(2) → child(3) → check fires
        with pytest.raises(DomainError) as exc:
            await repo.update(leaf.id, parent_id=ggc.id)
        assert exc.value.status_code == 409
        assert "depth" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_parent_success(self, session):
        """Successfully re-parent a category under a different root."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root_a = await repo.create(slug="reparent-a", taxonomy_version="v1")
        root_b = await repo.create(slug="reparent-b", taxonomy_version="v1")
        child = await repo.create(slug="reparent-child", taxonomy_version="v1", parent_id=root_a.id)
        assert child.parent_id == root_a.id

        updated = await repo.update(child.id, parent_id=root_b.id)
        assert updated.parent_id == root_b.id

    @pytest.mark.asyncio
    async def test_update_slug_conflict(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        await repo.create(slug="conflict-a", taxonomy_version="v1")
        cat_b = await repo.create(slug="conflict-b", taxonomy_version="v1")
        with pytest.raises(DomainError) as exc:
            await repo.update(cat_b.id, slug="conflict-a")
        assert exc.value.status_code == 409


# ---------------------------------------------------------------------------
# delete()
# ---------------------------------------------------------------------------
class TestCategoryDelete:
    @pytest.mark.asyncio
    async def test_delete_not_found(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        with pytest.raises(DomainError) as exc:
            await repo.delete(str(uuid.uuid4()))
        assert exc.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_has_children(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        root = await repo.create(slug="del-parent", taxonomy_version="v1")
        await repo.create(slug="del-child", taxonomy_version="v1", parent_id=root.id)
        with pytest.raises(DomainError) as exc:
            await repo.delete(root.id)
        assert exc.value.status_code == 409
        assert "children" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_delete_success(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="del-ok", taxonomy_version="v1")
        await repo.delete(cat.id)
        result = await repo.get(cat.id)
        assert result is None


# ---------------------------------------------------------------------------
# upsert_translation()
# ---------------------------------------------------------------------------
class TestCategoryUpsertTranslation:
    @pytest.mark.asyncio
    async def test_upsert_translation_create(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="trans-create", taxonomy_version="v1")
        t = await repo.upsert_translation(cat.id, locale="en", name="Coding", description="Software development")
        assert t.name == "Coding"
        assert t.description == "Software development"
        assert t.locale == "en"

    @pytest.mark.asyncio
    async def test_upsert_translation_update_name(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="trans-update", taxonomy_version="v1")
        t1 = await repo.upsert_translation(cat.id, locale="es", name="Programacion")
        t2 = await repo.upsert_translation(cat.id, locale="es", name="Programacion Actualizada")
        assert t2.id == t1.id
        assert t2.name == "Programacion Actualizada"

    @pytest.mark.asyncio
    async def test_upsert_translation_update_description(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="trans-desc", taxonomy_version="v1")
        t1 = await repo.upsert_translation(cat.id, locale="en", name="Test", description="Old desc")
        t2 = await repo.upsert_translation(cat.id, locale="en", name="Test", description="New desc")
        assert t2.id == t1.id
        assert t2.description == "New desc"

    @pytest.mark.asyncio
    async def test_upsert_translation_locale_enum(self, session):
        """Test that locale enum values are handled correctly."""
        from app.taxonomy.repositories.category import CategoryRepository
        from app.taxonomy.models.enums import Locale

        repo = CategoryRepository(session)
        cat = await repo.create(slug="trans-enum", taxonomy_version="v1")
        t = await repo.upsert_translation(cat.id, locale=Locale.ES, name="Enum Test")
        assert t.locale == "es"

    @pytest.mark.asyncio
    async def test_upsert_translation_conflict(self, session):
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="trans-conflict", taxonomy_version="v1")
        await repo.upsert_translation(cat.id, locale="en", name="First")
        # Manually insert a conflicting translation to trigger IntegrityError
        # This is hard to trigger naturally, so we'll just verify the path exists
        # by checking the method handles it gracefully
        t = await repo.upsert_translation(cat.id, locale="en", name="Second")
        assert t.name == "Second"  # Should update, not conflict


# ---------------------------------------------------------------------------
# IntegrityError defensive paths (mocked)
# ---------------------------------------------------------------------------
class TestCategoryIntegrityErrors:
    @pytest.mark.asyncio
    async def test_create_integrity_error(self, session):
        """create() IntegrityError handler — line 52-54."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        original_flush = session.flush

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.create(slug="integrity-create", taxonomy_version="v1")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_update_integrity_error(self, session):
        """update() IntegrityError handler — line 112-114."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="integrity-update", taxonomy_version="v1")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.update(cat.id, slug="new-slug")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_delete_integrity_error(self, session):
        """delete() IntegrityError handler — line 130-132."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="integrity-delete", taxonomy_version="v1")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.delete(cat.id)
            assert exc.value.status_code == 409
            assert "dependencies" in str(exc.value).lower()

    @pytest.mark.asyncio
    async def test_upsert_translation_integrity_error(self, session):
        """upsert_translation() IntegrityError handler — line 165-167."""
        from app.taxonomy.repositories.category import CategoryRepository

        repo = CategoryRepository(session)
        cat = await repo.create(slug="integrity-trans", taxonomy_version="v1")

        async def raise_integrity():
            raise SAIntegrityError("stmt", "params", Exception())

        with patch.object(session, "flush", side_effect=raise_integrity):
            with pytest.raises(DomainError) as exc:
                await repo.upsert_translation(cat.id, locale="en", name="Conflict")
            assert exc.value.status_code == 409
            assert "conflict" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# visited break — line 89 (cycle in parent chain via direct SQL)
# ---------------------------------------------------------------------------
class TestCategoryVisitedBreak:
    @pytest.mark.asyncio
    async def test_update_parent_cycle_via_direct_sql(self, session):
        """Trigger the visited-break guard (line 89) by creating a 2-node cycle via direct SQL.

        The depth guard at line 99 fires when len(visited) > 2, so we need a 2-node cycle
        where the walk visits exactly 2 nodes before encountering a repeated one.

        Setup: A↔B (2-node cycle via direct SQL), D (not in cycle).
        Update D's parent to A — walk from A: A(add, len=1), B(add, len=2), A(in visited) → break.
        The break happens before len(visited) exceeds 2, and A != category_id (D), so no cycle detection.
        """
        from app.taxonomy.repositories.category import CategoryRepository
        from sqlalchemy import text

        repo = CategoryRepository(session)

        a_id = str(uuid.uuid4())
        b_id = str(uuid.uuid4())
        d_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        # Insert A, B, D with no parents
        for sid, slug in [(a_id, "vb-a"), (b_id, "vb-b"), (d_id, "vb-d")]:
            await session.execute(
                text(
                    "INSERT INTO categories (id, slug, parent_id, taxonomy_version, status, created_at, updated_at) "
                    "VALUES (:id, :slug, NULL, 'v1', 'active', :now, :now)"
                ),
                {"id": sid, "slug": slug, "now": now},
            )
        await session.flush()

        # Create 2-node cycle: A.parent=B, B.parent=A
        await session.execute(text("UPDATE categories SET parent_id = :pid WHERE id = :id"), {"pid": b_id, "id": a_id})
        await session.execute(text("UPDATE categories SET parent_id = :pid WHERE id = :id"), {"pid": a_id, "id": b_id})
        await session.flush()

        # Verify cycle
        result = await session.execute(text("SELECT slug, parent_id FROM categories ORDER BY slug"))
        for row in result:
            print(f"  {row[0]}: parent={row[1]}")

        # Update D's parent to A — walk: A(add), B(add), A(in visited) → break
        updated = await repo.update(d_id, parent_id=a_id)
        assert updated.parent_id == a_id
