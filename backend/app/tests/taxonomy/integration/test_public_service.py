"""Phase 7.2 — Public Service Layer (i18n, FTS, Cache) — TDD RED"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, text as sa_text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
    LocaleMeta,
)
from app.taxonomy.services.public import PublicService, cache_key, clear_cache


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
        yield s


async def seed_minimal(session, approved=True):
    # Provider
    prov = Provider(id=str(uuid.uuid4()), slug="anthropic", name="Anthropic", status="active")
    session.add(prov)
    prov2 = Provider(id=str(uuid.uuid4()), slug="openai", name="OpenAI", status="active")
    session.add(prov2)
    await session.flush()
    # Translation for provider
    session.add(ProviderTranslation(id=str(uuid.uuid4()), provider_id=prov.id, locale="es", name="Antrópico"))
    # Taxonomy version
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()
    # Category
    cat = Category(id=str(uuid.uuid4()), slug="coding", taxonomy_version="v1", status="active")
    session.add(cat)
    await session.flush()
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="en", name="Coding"))
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="zh", name="编程"))
    # LocaleMeta
    for loc, native in [("en", "English"), ("es", "Español"), ("pt", "Português"), ("fr", "Français"), ("zh", "中文")]:
        session.add(LocaleMeta(locale=loc, native_name=native, direction="ltr", plural_categories=["one", "other"]))
    await session.flush()
    # Models
    m1 = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov.id,
        slug="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        modality=["text"],
        status="approved" if approved else "draft",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
        input_price_per_mtok=Decimal("3.00"),
        output_price_per_mtok=Decimal("15.00"),
        release_date=datetime(2024, 6, 1).date(),
    )
    m2 = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov2.id,
        slug="llama-3-70b",
        display_name="Llama 3 70B",
        modality=["text"],
        status="approved",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
        input_price_per_mtok=None,
        output_price_per_mtok=None,
        release_date=datetime(2024, 4, 1).date(),
    )
    session.add(m1)
    session.add(m2)
    await session.flush()
    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m1.id, locale="es", display_name="Claude 3.5 Soneto"))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m1.id, provider_id=prov.id, is_primary=True))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m2.id, provider_id=prov2.id, is_primary=True))
    session.add(ModelCategory(model_id=m1.id, category_id=cat.id, taxonomy_version="v1"))
    await session.commit()
    await session.refresh(m1)
    await session.refresh(m2)
    return {"prov": prov, "prov2": prov2, "cat": cat, "m1": m1, "m2": m2, "tv": tv}


@pytest.mark.asyncio
async def test_list_models_returns_only_approved(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(limit=20, locale="en")
    assert total == 2
    assert all(r["status"] == "approved" for r in result)


@pytest.mark.asyncio
async def test_list_models_filter_by_category(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(category_slug="coding", locale="en")
    assert total == 1
    assert result[0]["slug"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_list_models_filter_by_provider(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(provider_slug="anthropic", locale="en")
    assert total == 1
    assert result[0]["slug"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_list_models_search_fts(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(search="claude", locale="en")
    assert total == 1
    assert "claude" in result[0]["slug"]


@pytest.mark.asyncio
async def test_list_models_locale_fallback(session):
    data = await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(locale="es")
    # m1 has es translation, m2 fallback to en
    m1_res = [r for r in result if r["slug"] == "claude-3-5-sonnet"][0]
    assert m1_res["display_name"] == "Claude 3.5 Soneto"
    assert m1_res["locale_used"] == "es"


@pytest.mark.asyncio
async def test_list_models_price_omission(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, total = await svc.list_models(locale="en")
    m2 = [r for r in result if r["slug"] == "llama-3-70b"][0]
    assert "input_price_per_mtok" not in m2
    assert "output_price_per_mtok" not in m2


@pytest.mark.asyncio
async def test_list_models_sort_and_order(session):
    await seed_minimal(session)
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="release_date", order="asc", locale="en")
    assert result[0]["slug"] == "llama-3-70b"
    result2, _ = await svc.list_models(sort="release_date", order="desc", locale="en")
    assert result2[0]["slug"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_cache_key_includes_taxonomy_version():
    k1 = cache_key(filters={"category_slug": "coding"}, locale="en", taxonomy_version="v1")
    k2 = cache_key(filters={"category_slug": "coding"}, locale="en", taxonomy_version="v2")
    assert k1 != k2


@pytest.mark.asyncio
async def test_cache_hit_and_invalidation(session):
    await seed_minimal(session)
    svc = PublicService(session)
    clear_cache()
    # First call caches
    await svc.list_models(limit=20, locale="en", use_cache=True)
    # Second call should hit cache (we verify no exception and key exists)
    from app.taxonomy.services.public import _cache
    assert len(_cache) > 0
    # Invalidate
    await svc.invalidate_cache()
    assert len(_cache) == 0


@pytest.mark.asyncio
async def test_get_model_detail(session):
    data = await seed_minimal(session)
    svc = PublicService(session)
    detail = await svc.get_model("claude-3-5-sonnet", locale="en")
    assert detail is not None
    assert detail["slug"] == "claude-3-5-sonnet"
    assert "hostings" in detail
    # hostings no prices
    for h in detail["hostings"]:
        assert "is_primary" in h
        assert "provider" in h


@pytest.mark.asyncio
async def test_list_categories_with_translation(session):
    await seed_minimal(session)
    svc = PublicService(session)
    cats, tv = await svc.list_categories(locale="zh")
    assert tv == "v1"
    assert cats[0]["name"] == "编程"


@pytest.mark.asyncio
async def test_list_providers_excludes_deprecated(session):
    await seed_minimal(session)
    # Add deprecated provider
    dep = Provider(id=str(uuid.uuid4()), slug="old-provider", name="Old", status="deprecated")
    session.add(dep)
    await session.commit()
    svc = PublicService(session)
    provs = await svc.list_providers(locale="en")
    slugs = [p["slug"] for p in provs]
    assert "anthropic" in slugs
    assert "old-provider" not in slugs


@pytest.mark.asyncio
async def test_list_locales(session):
    await seed_minimal(session)
    svc = PublicService(session)
    locales = await svc.list_locales()
    assert len(locales) == 5
    assert any(l["locale"] == "zh" for l in locales)


@pytest.mark.asyncio
async def test_cursor_pagination(session):
    # Seed 5 models
    await seed_minimal(session)
    for i in range(3, 6):
        prov_id = (await session.execute(__import__("sqlalchemy").select(Provider).where(Provider.slug == "anthropic"))).scalars().first().id
        m = AIModel(
            id=str(uuid.uuid4()),
            provider_id=prov_id,
            slug=f"model-{i}",
            display_name=f"Model {i}",
            modality=["text"],
            status="approved",
            source="manual",
            source_payload_hash=str(uuid.uuid4()),
        )
        session.add(m)
    await session.commit()
    svc = PublicService(session)
    page1, total = await svc.list_models(limit=2, locale="en")
    assert total == 5
    assert len(page1) == 2
    # get cursor for next page
    from app.taxonomy.services.public import encode_cursor, decode_cursor

    cursor = encode_cursor(page1[-1])
    page2, _ = await svc.list_models(limit=2, locale="en", cursor=cursor)
    assert len(page2) == 2
    assert page2[0]["slug"] != page1[0]["slug"]
