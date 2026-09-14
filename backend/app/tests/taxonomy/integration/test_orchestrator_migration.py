"""Phase 6.1 — Orchestrator Migration Tests (TDD RED).

Covers:
- Migration file exists for orchestrator tables
- Migration creates orchestrators, orchestrator_translations, orchestrator_providers tables
- Migration creates indexes (idx_orchestrators_slug, idx_orchestrators_status, idx_orchestrator_translations_orchestrator)
- Upgrade/downgrade roundtrip (via Base.metadata)
"""

from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import Base


def _find_orchestrator_migration():
    """Find the orchestrator migration file."""
    candidates = list(Path("app/db/migrations/versions").glob("*orchestrator*.py"))
    candidates += list(Path("alembic/versions").glob("*orchestrator*.py"))
    if candidates:
        return candidates[0]

    # Fallback: search all migration files for orchestrator content
    all_migrations = list(Path("app/db/migrations/versions").glob("*.py"))
    all_migrations += list(Path("alembic/versions").glob("*.py"))
    for p in all_migrations:
        try:
            if "orchestrator" in p.read_text().lower():
                return p
        except Exception:
            continue
    return None


def test_orchestrator_migration_file_exists():
    """Migration file for orchestrators must exist."""
    mig = _find_orchestrator_migration()
    assert mig is not None, "No orchestrator migration file found"


def test_orchestrator_migration_creates_tables():
    """Migration must create orchestrators, orchestrator_translations, orchestrator_providers."""
    mig = _find_orchestrator_migration()
    assert mig is not None
    content = mig.read_text()

    for table in ["orchestrators", "orchestrator_translations", "orchestrator_providers"]:
        assert table in content, f"Table {table} not found in orchestrator migration"


def test_orchestrator_migration_creates_indexes():
    """Migration must create required indexes."""
    mig = _find_orchestrator_migration()
    assert mig is not None
    content = mig.read_text()

    for idx in ["idx_orchestrators_slug", "idx_orchestrators_status", "idx_orchestrator_translations_orchestrator"]:
        assert idx in content, f"Index {idx} not found in orchestrator migration"


def test_orchestrator_migration_has_downgrade():
    """Migration must have a downgrade function."""
    mig = _find_orchestrator_migration()
    assert mig is not None
    content = mig.read_text()

    assert "def downgrade" in content, "downgrade function not found"
    # Downgrade should drop the tables
    assert "drop_table" in content or "drop" in content.lower(), "downgrade should drop tables"


def test_orchestrator_migration_revision_chain():
    """Migration must have valid revision chain."""
    mig = _find_orchestrator_migration()
    assert mig is not None
    content = mig.read_text()

    assert "revision" in content, "revision not defined"
    assert "down_revision" in content, "down_revision not defined"


@pytest.mark.asyncio
async def test_orchestrator_tables_exist_via_metadata():
    """Verify orchestrator tables are in Base.metadata and can be created."""
    import app.taxonomy.models.entities  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def check(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            assert "orchestrators" in tables
            assert "orchestrator_translations" in tables
            assert "orchestrator_providers" in tables

            # Check indexes on orchestrators
            idxs = insp.get_indexes("orchestrators")
            idx_names = [idx["name"] for idx in idxs]
            assert "idx_orchestrators_slug" in idx_names
            assert "idx_orchestrators_status" in idx_names

            # Check FK on orchestrator_translations
            fks = insp.get_foreign_keys("orchestrator_translations")
            assert any(fk["referred_table"] == "orchestrators" for fk in fks)

            # Check FK on orchestrator_providers
            fks_p = insp.get_foreign_keys("orchestrator_providers")
            assert any(fk["referred_table"] == "orchestrators" for fk in fks_p)

        await conn.run_sync(check)
    await engine.dispose()


@pytest.mark.asyncio
async def test_orchestrator_tables_drop_on_downgrade():
    """Verify orchestrator tables are dropped when Base.metadata.drop_all is called."""
    import app.taxonomy.models.entities  # noqa: F401

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Base.metadata.drop_all)

        def check_dropped(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            assert "orchestrators" not in tables
            assert "orchestrator_translations" not in tables
            assert "orchestrator_providers" not in tables

        await conn.run_sync(check_dropped)
    await engine.dispose()
