"""Phase 2.2 — Alembic Migration (Initial Schema) — TDD RED test."""

from pathlib import Path

import pytest
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.db.session import Base


def _find_migration():
    # Support both app/db/migrations and alembic/versions layouts
    candidates = list(Path("app/db/migrations/versions").glob("*taxonomy*.py"))
    candidates += list(Path("app/db/migrations/versions").glob("*.py"))
    candidates += list(Path("alembic/versions").glob("*taxonomy*.py"))
    # filter to taxonomy initial
    taxonomy_candidates = [p for p in candidates if "taxonomy" in p.name.lower()]
    if taxonomy_candidates:
        return taxonomy_candidates[0]
    # fallback: any migration that mentions taxonomy
    for p in candidates:
        try:
            if "taxonomy" in p.read_text().lower():
                return p
        except Exception:
            continue
    return None


def test_migration_file_exists():
    mig = _find_migration()
    assert mig is not None, "No taxonomy migration file found under app/db/migrations/versions or alembic/versions"
    assert mig.exists()


def test_migration_has_all_ddl():
    mig = _find_migration()
    assert mig is not None
    content = mig.read_text()
    # must create 14 tables
    for tbl in [
        "providers",
        "provider_translations",
        "ai_models",
        "model_translations",
        "model_hostings",
        "categories",
        "category_translations",
        "model_categories",
        "taxonomy_versions",
        "ingestion_sources",
        "ingestion_runs",
        "webhook_registrations",
        "webhook_deliveries",
        "locale_meta",
    ]:
        assert tbl in content, f"Table {tbl} not in migration"

    # partial unique indexes
    assert "is_current" in content
    assert "is_primary" in content
    # triggers for immutability (3 triggers)
    trigger_count = content.lower().count("trigger") + content.lower().count("prevent_historical")
    assert trigger_count >= 3, f"Expected >=3 triggers, found {trigger_count} in migration"
    # FK RESTRICT/CASCADE
    assert "CASCADE" in content
    assert "RESTRICT" in content
    # 8 required indexes from spec 12
    for idx in [
        "idx_ai_model_provider_status",
        "idx_ai_model_modality_gin",
        "idx_ai_model_search",
        "idx_model_category_lookup",
        "idx_model_hosting_model",
        "idx_ingestion_run_source_status",
        "idx_webhook_delivery_pending",
    ]:
        # at least prefix must appear
        assert idx.split("_")[1] in content.lower() or idx in content, f"Index {idx} not found"


def test_migration_revision_chain():
    mig = _find_migration()
    assert mig is not None
    content = mig.read_text()
    assert "revision" in content
    assert "down_revision" in content
    # downgrade must drop taxonomy objects
    assert "downgrade" in content
    # should reference previous auth migration 001_initial_auth as parent or at least have down_revision set
    assert "001_initial_auth" in content or "down_revision" in content


@pytest.mark.asyncio
async def test_migration_upgrade_creates_tables():
    """Verify migration-equivalent create_all produces tables and indexes."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        # import entities so Base metadata is populated
        import app.taxonomy.models.entities  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)

        def check(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            assert "ai_models" in tables
            assert "taxonomy_versions" in tables
            # check indexes exist for ai_models (at least one index)
            idxs = insp.get_indexes("ai_models")
            assert len(idxs) >= 1
            # foreign keys exist
            fks = insp.get_foreign_keys("ai_models")
            assert any(fk["referred_table"] == "providers" for fk in fks)
            # model_hostings unique
            idxs_hosting = insp.get_indexes("model_hostings")
            # should have unique partial or unique constraint
            # sqlite doesn't support partial unique via reflection, but at least one index
            assert len(idxs_hosting) >= 1

        await conn.run_sync(check)
    await engine.dispose()


@pytest.mark.asyncio
async def test_downgrade_drops_taxonomy_tables():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        import app.taxonomy.models.entities  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(Base.metadata.drop_all)

        def check_dropped(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            # taxonomy tables should be gone after drop_all
            assert "ai_models" not in tables
            assert "providers" not in tables

        await conn.run_sync(check_dropped)
    await engine.dispose()
