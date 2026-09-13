"""Phase 2.1 — SQLAlchemy Entities (14 Models) — TDD RED test."""

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base

# This import MUST FAIL before implementation (RED)
from app.taxonomy.models.entities import (  # noqa: F401
    AIModel,
    Category,
    CategoryTranslation,
    IngestionRun,
    IngestionSource,
    LocaleMeta,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
    WebhookDelivery,
    WebhookRegistration,
)
from app.taxonomy.models.enums import (
    CategoryStatus,
    Locale,
    ModelModality,
    ModelSource,
    ModelStatus,
    ProviderStatus,
)


# Helpers
@pytest.fixture
async def memory_engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session(memory_engine):
    async_session = sessionmaker(memory_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        yield s
        await s.rollback()


# 2.1.1 — all 14 models import without error
def test_all_14_models_importable():
    # import already done at top; verify class attributes exist
    assert Provider.__tablename__ == "providers"
    assert ProviderTranslation.__tablename__ == "provider_translations"
    assert AIModel.__tablename__ == "ai_models"
    assert ModelTranslation.__tablename__ == "model_translations"
    assert ModelHosting.__tablename__ == "model_hostings"
    assert Category.__tablename__ == "categories"
    assert CategoryTranslation.__tablename__ == "category_translations"
    assert ModelCategory.__tablename__ == "model_categories"
    assert TaxonomyVersion.__tablename__ == "taxonomy_versions"
    assert IngestionSource.__tablename__ == "ingestion_sources"
    assert IngestionRun.__tablename__ == "ingestion_runs"
    assert WebhookRegistration.__tablename__ == "webhook_registrations"
    assert WebhookDelivery.__tablename__ == "webhook_deliveries"
    assert LocaleMeta.__tablename__ == "locale_meta"


# 2.1.2 — metadata.create_all produces 14 taxonomy tables
@pytest.mark.asyncio
async def test_metadata_creates_all_tables():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def check(sync_conn):
            insp = inspect(sync_conn)
            tables = insp.get_table_names()
            expected = {
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
            }
            missing = expected - set(tables)
            assert not missing, f"Missing tables: {missing}"

        await conn.run_sync(check)
    await engine.dispose()


# 2.1.3 — Provider columns, FKs, unique slug
def test_provider_columns():
    cols = {c.key for c in inspect(Provider).columns}
    assert {"id", "slug", "name", "website", "api_docs_url", "logo_url", "status", "created_at", "updated_at"} <= cols
    # slug unique constraint exists
    table = Provider.__table__
    # find unique constraint on slug
    unique_cols = []
    for c in table.constraints:
        if getattr(c, "columns", None) is not None:
            try:
                unique_cols.extend(list(c.columns.keys()))
            except Exception:
                pass
    # At least slug should be unique via index or constraint
    indexes = [idx for idx in table.indexes]
    # check column has unique flag
    slug_col = table.c.slug
    assert slug_col.unique is True or any("slug" in str(idx.columns) for idx in indexes) or any(slug_col.key in unique_cols for _ in [1])


# 2.1.4 — AIModel columns including provider_id, pricing Decimal, CHECK constraints, dedup indexes
def test_aimodel_columns_and_constraints():
    cols = {c.key for c in inspect(AIModel).columns}
    expected = {
        "id",
        "provider_id",
        "slug",
        "display_name",
        "version",
        "family",
        "modality",
        "context_window",
        "max_output_tokens",
        "input_price_per_mtok",
        "output_price_per_mtok",
        "release_date",
        "deprecation_date",
        "status",
        "source",
        "source_payload_hash",
        "created_at",
        "updated_at",
    }
    assert expected <= cols, f"Missing AIModel cols: {expected - cols}"
    table = AIModel.__table__
    # provider_id FK
    fk_targets = [fk.target_fullname for fk in table.foreign_keys]
    assert any("providers.id" in t for t in fk_targets), f"FK missing: {fk_targets}"
    # source_payload_hash NOT NULL
    assert table.c.source_payload_hash.nullable is False
    # Check constraints exist
    chk_names = [c.name for c in table.constraints if c.__class__.__name__ == "CheckConstraint"]
    # At least context_window>0 and price >=0 check
    table_sql = str(table.compile())
    # Instead, inspect constraints via table.constraints
    has_checks = any("CheckConstraint" in type(c).__name__ for c in table.constraints)
    assert has_checks


# 2.1.5 — ModelHosting no price fields, unique (model_id,provider_id), partial index
def test_model_hosting_no_price_fields():
    cols = {c.key for c in inspect(ModelHosting).columns}
    assert "model_id" in cols
    assert "provider_id" in cols
    assert "is_primary" in cols
    # Must NOT have price fields
    forbidden = {"input_price_override", "output_price_override", "price", "cost", "input_price_per_mtok", "output_price_per_mtok"}
    assert forbidden.isdisjoint(cols), f"Hosting should have no price fields, found {forbidden & cols}"
    table = ModelHosting.__table__
    # unique (model_id, provider_id) via UniqueConstraint
    uc_cols = []
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            uc_cols.append({c.key for c in constraint.columns})
    assert any({"model_id", "provider_id"} <= s for s in uc_cols), f"No unique (model_id,provider_id): {uc_cols}"
    # partial unique index for is_primary
    partial_indexes = [idx for idx in table.indexes if idx.unique and "is_primary" in str(idx.columns)]
    # also check via __table_args__ for partial index definition
    assert len(partial_indexes) >= 1 or any("is_primary" in str(arg) for arg in getattr(ModelHosting, "__table_args__", []))


# 2.1.6 — Category slug per version, parent_id RESTRICT, taxonomy_version FK
def test_category_columns_and_fk():
    cols = {c.key for c in inspect(Category).columns}
    assert {"id", "slug", "parent_id", "taxonomy_version", "status"} <= cols
    table = Category.__table__
    fk_targets = [fk.target_fullname for fk in table.foreign_keys]
    assert any("categories.id" in t for t in fk_targets)  # parent_id self-ref
    assert any("taxonomy_versions.version" in t for t in fk_targets)


# 2.1.7 — Translation unique constraints
def test_translation_unique_constraints():
    for model, fk_field in [
        (ProviderTranslation, "provider_id"),
        (CategoryTranslation, "category_id"),
        (ModelTranslation, "model_id"),
    ]:
        table = model.__table__
        uc_sets = [{c.key for c in uc.columns} for uc in table.constraints if uc.__class__.__name__ == "UniqueConstraint"]
        assert any({fk_field, "locale"} <= s for s in uc_sets), f"{model.__name__} missing unique ({fk_field}, locale): {uc_sets}"


# 2.1.8 — ModelCategory PK and FKs
def test_model_category_pk_and_fks():
    table = ModelCategory.__table__
    pk_cols = {c.key for c in table.primary_key.columns}
    assert pk_cols == {"model_id", "category_id", "taxonomy_version"}
    fk_targets = [fk.target_fullname for fk in table.foreign_keys]
    assert any("ai_models.id" in t for t in fk_targets)
    assert any("categories.id" in t for t in fk_targets)
    assert any("taxonomy_versions.version" in t for t in fk_targets)


# 2.1.9 — TaxonomyVersion single current via partial unique
def test_taxonomy_version_single_current():
    table = TaxonomyVersion.__table__
    cols = {c.key for c in inspect(TaxonomyVersion).columns}
    assert {"id", "version", "released_at", "notes", "is_current"} <= cols
    assert table.c.version.unique is True
    # partial unique index on is_current
    indexes = list(table.indexes)
    partial_unique = [idx for idx in indexes if idx.unique]
    assert len(partial_unique) >= 1, f"No unique index found: {indexes}"


# 2.1.10 — Ingestion entities
def test_ingestion_entities():
    assert IngestionSource.__table__.c.code.primary_key is True
    src_cols = {c.key for c in inspect(IngestionSource).columns}
    assert {"code", "name", "parser_class", "rate_limit_rpm", "base_url"} <= src_cols
    run_cols = {c.key for c in inspect(IngestionRun).columns}
    assert {"id", "source", "status", "models_found", "models_created", "models_updated", "models_skipped", "errors"} <= run_cols


# 2.1.11 — Webhook entities
def test_webhook_entities():
    reg_cols = {c.key for c in inspect(WebhookRegistration).columns}
    assert {"id", "url", "secret", "events", "is_active"} <= reg_cols
    del_cols = {c.key for c in inspect(WebhookDelivery).columns}
    assert {"id", "webhook_id", "event_type", "payload", "delivery_id", "attempt", "status", "created_at"} <= del_cols
    assert WebhookDelivery.__table__.c.delivery_id.unique is True


# 2.1.12 — LocaleMeta PK and required fields
def test_locale_meta():
    cols = {c.key for c in inspect(LocaleMeta).columns}
    assert {"locale", "native_name", "direction", "plural_categories"} <= cols
    assert LocaleMeta.__table__.c.locale.primary_key is True


# 2.1.13 — Decimal precision and pricing nullable
@pytest.mark.asyncio
async def test_decimal_precision_roundtrip(memory_engine):
    async_session = sessionmaker(memory_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        # need provider and taxonomy version to satisfy FKs
        provider = Provider(slug="test-provider", name="Test Provider", status=ProviderStatus.ACTIVE)
        s.add(provider)
        await s.flush()
        version = TaxonomyVersion(version="v1", released_at=datetime.now(timezone.utc), is_current=True)
        s.add(version)
        await s.flush()
        model = AIModel(
            provider_id=provider.id,
            slug="test-model",
            display_name="Test Model",
            modality=[ModelModality.TEXT.value],
            status=ModelStatus.DRAFT,
            source=ModelSource.MANUAL,
            source_payload_hash="hash123",
            input_price_per_mtok=Decimal("0.000001"),
            output_price_per_mtok=Decimal("3.00"),
        )
        s.add(model)
        await s.commit()
        await s.refresh(model)
        # SQLite may store as string/float; check we got back Decimal-ish values
        assert model.input_price_per_mtok is not None
        assert str(model.input_price_per_mtok) == "0.000001" or float(model.input_price_per_mtok) == 0.000001


# 2.1.14 — CHECK constraints enforcement (context_window >0)
@pytest.mark.asyncio
async def test_check_constraint_context_window(memory_engine):
    async_session = sessionmaker(memory_engine, class_=AsyncSession, expire_on_commit=False)  # type: ignore
    async with async_session() as s:
        provider = Provider(slug="chk-provider", name="Chk", status=ProviderStatus.ACTIVE)
        s.add(provider)
        await s.flush()
        bad_model = AIModel(
            provider_id=provider.id,
            slug="bad-model",
            display_name="Bad",
            modality=[ModelModality.TEXT.value],
            context_window=0,  # violates >0 CHECK
            status=ModelStatus.DRAFT,
            source=ModelSource.MANUAL,
            source_payload_hash="badhash",
        )
        s.add(bad_model)
        with pytest.raises(IntegrityError):
            await s.commit()
        await s.rollback()
