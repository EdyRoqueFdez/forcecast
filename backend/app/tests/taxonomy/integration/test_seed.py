"""Phase 4.1-4.2 — Seed Data & Idempotent Seed Command (TDD RED)."""

import json
import pathlib
import pytest
import pytest_asyncio
from sqlalchemy import event, text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import TaxonomyVersion

SEEDS_DIR = pathlib.Path("seeds")

# ---------------------------------------------------------------------------
# 4.1 Seed JSON Files validation (pure file checks)
# ---------------------------------------------------------------------------

class TestSeedJsonFiles:
    def test_provider_seed_count(self):
        data = json.loads((SEEDS_DIR / "providers.json").read_text(encoding="utf-8"))
        assert len(data) >= 10, f"Expected >=10 providers, got {len(data)}"
        slugs = [p["slug"] for p in data]
        assert len(slugs) == len(set(slugs)), "Provider slugs must be unique"

    def test_model_seed_count(self):
        data = json.loads((SEEDS_DIR / "models.json").read_text(encoding="utf-8"))
        assert len(data) >= 30, f"Expected >=30 models, got {len(data)}"
        # Check that models span multiple providers
        provider_slugs = set(m["provider_slug"] for m in data)
        assert len(provider_slugs) >= 3, "Models must span >=3 providers"
        # Check reference prices present or null but fields exist
        for m in data:
            assert "slug" in m and m["slug"], "Model missing slug"
            assert "display_name" in m
            assert "modality" in m
            assert "status" in m

    def test_category_seed_count(self):
        data = json.loads((SEEDS_DIR / "categories.json").read_text(encoding="utf-8"))
        assert len(data) == 17, f"Expected 17 categories, got {len(data)}"
        # Validate tree max depth 2
        parent_map = {c["slug"]: c["parent_slug"] for c in data}
        for slug, parent in parent_map.items():
            if parent is not None:
                assert parent in parent_map, f"Parent {parent} for {slug} must exist"
                # parent's parent must be None (depth 2)
                assert parent_map[parent] is None, f"Max depth 2 exceeded for {slug}"

    def test_ingestion_source_seeds(self):
        data = json.loads((SEEDS_DIR / "ingestion_sources.json").read_text(encoding="utf-8"))
        assert len(data) == 3, f"Expected 3 sources, got {len(data)}"
        codes = {s["code"] for s in data}
        assert codes == {"openrouter", "huggingface", "lmsys"}
        for s in data:
            assert "parser_class" in s and s["parser_class"]
            assert "rate_limit_rpm" in s

    def test_model_hosting_no_price_fields(self):
        data = json.loads((SEEDS_DIR / "model_hostings.json").read_text(encoding="utf-8"))
        assert len(data) >= 30, f"Expected >=30 hostings, got {len(data)}"
        forbidden = {"input_price_override", "output_price_override", "price", "cost", "input_price_per_mtok", "output_price_per_mtok"}
        for i, row in enumerate(data):
            found = forbidden & set(row.keys())
            assert not found, f"Row {i} hosting must not have price fields, found {found}"
            # required fields
            assert "model_slug" in row or "model_id" in row
            assert "provider_slug" in row or "provider_id" in row
            assert "is_primary" in row
            assert row["is_primary"] is True, "v1 hostings should be primary"

    def test_translation_coverage_all_locales(self):
        """Every seed entity must have translations in all 5 locales (en, es, pt, fr, zh)."""
        locales = ["en", "es", "pt", "fr", "zh"]
        # categories
        categories = json.loads((SEEDS_DIR / "categories.json").read_text(encoding="utf-8"))
        providers = json.loads((SEEDS_DIR / "providers.json").read_text(encoding="utf-8"))
        models = json.loads((SEEDS_DIR / "models.json").read_text(encoding="utf-8"))
        cat_slugs = {c["slug"] for c in categories}
        prov_slugs = {p["slug"] for p in providers}
        model_slugs = {m["slug"] for m in models}

        for locale in locales:
            # files are translations_{locale}.json at seeds/ root
            tf = SEEDS_DIR / f"translations_{locale}.json"
            assert tf.exists(), f"Missing translation file {tf}"
            trans = json.loads(tf.read_text(encoding="utf-8"))
            # Must have keys: categories, providers, models
            assert "categories" in trans, f"{locale} missing categories"
            assert "providers" in trans, f"{locale} missing providers"
            assert "models" in trans, f"{locale} missing models"
            # Every category slug must be present
            for slug in cat_slugs:
                assert slug in trans["categories"], f"{locale} missing category translation for {slug}"
                assert "name" in trans["categories"][slug], f"{locale} category {slug} missing name"
            for slug in prov_slugs:
                assert slug in trans["providers"], f"{locale} missing provider translation for {slug}"
                assert "name" in trans["providers"][slug], f"{locale} provider {slug} missing name"
            for slug in model_slugs:
                assert slug in trans["models"], f"{locale} missing model translation for {slug}"
                assert "display_name" in trans["models"][slug], f"{locale} model {slug} missing display_name"


# ---------------------------------------------------------------------------
# 4.2 Idempotent Seed Command (integration)
# ---------------------------------------------------------------------------

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


class TestSeedIdempotent:
    @pytest.mark.asyncio
    async def test_seed_twice_no_duplicates(self, session):
        from app.db.seed import seed_taxonomy
        # First run
        result1 = await seed_taxonomy(session, seeds_dir="seeds")
        await session.commit()
        # Count after first
        from sqlalchemy import select, func
        from app.taxonomy.models.entities import Provider, AIModel, Category, ModelHosting, IngestionSource
        p1 = (await session.execute(select(func.count()).select_from(Provider))).scalar()
        m1 = (await session.execute(select(func.count()).select_from(AIModel))).scalar()
        h1 = (await session.execute(select(func.count()).select_from(ModelHosting))).scalar()
        c1 = (await session.execute(select(func.count()).select_from(Category))).scalar()
        # Second run should not create duplicates
        result2 = await seed_taxonomy(session, seeds_dir="seeds")
        await session.commit()
        p2 = (await session.execute(select(func.count()).select_from(Provider))).scalar()
        m2 = (await session.execute(select(func.count()).select_from(AIModel))).scalar()
        h2 = (await session.execute(select(func.count()).select_from(ModelHosting))).scalar()
        c2 = (await session.execute(select(func.count()).select_from(Category))).scalar()
        assert p1 == p2, f"Providers duplicated: {p1} -> {p2}"
        assert m1 == m2, f"Models duplicated: {m1} -> {m2}"
        assert h1 == h2, f"Hostings duplicated: {h1} -> {h2}"
        assert c1 == c2, f"Categories duplicated: {c1} -> {c2}"
        # result should indicate idempotency
        assert result1 is not None and result2 is not None

    @pytest.mark.asyncio
    async def test_seed_missing_translation_fails(self, session, tmp_path):
        from app.db.seed import seed_taxonomy, SeedValidationError
        import shutil
        # Create a copy of seeds with missing Portuguese translation for a provider
        broken_dir = tmp_path / "broken_seeds"
        shutil.copytree("seeds", broken_dir)
        # Remove pt translation for one provider
        trans_pt = json.loads((broken_dir / "translations_pt.json").read_text(encoding="utf-8"))
        # Remove first provider entry
        first_provider = next(iter(trans_pt["providers"]))
        del trans_pt["providers"][first_provider]
        (broken_dir / "translations_pt.json").write_text(json.dumps(trans_pt, ensure_ascii=False, indent=2), encoding="utf-8")
        with pytest.raises(SeedValidationError) as exc:
            await seed_taxonomy(session, seeds_dir=str(broken_dir))
        assert "pt" in str(exc.value).lower() or first_provider in str(exc.value)
        # Ensure session still usable - no partial data committed for broken run
        # (seed should fail before mutating)

    @pytest.mark.asyncio
    async def test_seed_validate_only(self, session):
        from app.db.seed import validate_seed_files
        # Should pass for correct seeds
        ok = await validate_seed_files(seeds_dir="seeds")
        assert ok is True or ok is None or ok == True  # validate returns bool or None without raising
