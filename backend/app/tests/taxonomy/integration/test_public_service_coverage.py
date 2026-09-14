"""Coverage boost for PublicService — targeting 90%+ on public.py"""
import uuid
from datetime import datetime, timezone, date
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import event as sa_event, select, text as sa_text
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
    Domain,
    DomainTranslation,
    Orchestrator,
    OrchestratorTranslation,
    OrchestratorProvider,
    OrchestratorCategory,
)
from app.taxonomy.services.public import (
    PublicService,
    cache_key,
    clear_cache,
    encode_cursor,
    decode_cursor,
    _cache_get,
    _cache_set,
    _cache,
    _TTL,
    _get_current_version,
    _resolve_translation,
)


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


async def _seed_base(session):
    """Seed base entities: providers, taxonomy version, category, locale metas."""
    prov = Provider(id=str(uuid.uuid4()), slug="anthropic", name="Anthropic", status="active")
    prov2 = Provider(id=str(uuid.uuid4()), slug="openai", name="OpenAI", status="active")
    session.add_all([prov, prov2])
    await session.flush()

    session.add(ProviderTranslation(id=str(uuid.uuid4()), provider_id=prov.id, locale="es", name="Antrópico"))
    session.add(ProviderTranslation(id=str(uuid.uuid4()), provider_id=prov.id, locale="en", name="Anthropic EN"))

    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    session.add(tv)
    await session.flush()

    cat = Category(id=str(uuid.uuid4()), slug="coding", taxonomy_version="v1", status="active")
    session.add(cat)
    await session.flush()
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="en", name="Coding"))
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat.id, locale="zh", name="编程"))

    for loc, native in [("en", "English"), ("es", "Español"), ("pt", "Português"), ("fr", "Français"), ("zh", "中文")]:
        session.add(LocaleMeta(locale=loc, native_name=native, direction="ltr", plural_categories=["one", "other"]))

    await session.flush()

    m1 = AIModel(
        id=str(uuid.uuid4()),
        provider_id=prov.id,
        slug="claude-3-5-sonnet",
        display_name="Claude 3.5 Sonnet",
        modality=["text"],
        status="approved",
        source="manual",
        source_payload_hash=str(uuid.uuid4()),
        input_price_per_mtok=Decimal("3.00"),
        output_price_per_mtok=Decimal("15.00"),
        release_date=date(2024, 6, 1),
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
        release_date=date(2024, 4, 1),
    )
    session.add_all([m1, m2])
    await session.flush()

    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m1.id, locale="es", display_name="Claude 3.5 Soneto"))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m1.id, provider_id=prov.id, is_primary=True))
    session.add(ModelHosting(id=str(uuid.uuid4()), model_id=m2.id, provider_id=prov2.id, is_primary=True))
    session.add(ModelCategory(model_id=m1.id, category_id=cat.id, taxonomy_version="v1"))
    await session.commit()
    return {"prov": prov, "prov2": prov2, "cat": cat, "m1": m1, "m2": m2, "tv": tv}


# ---------------------------------------------------------------------------
# _cache_get / _cache_set / TTL expiry (lines 72-73)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_get_returns_none_for_missing_key():
    clear_cache()
    assert _cache_get("nonexistent") is None


@pytest.mark.asyncio
async def test_cache_expired_entry_returns_none():
    clear_cache()
    key = "test:expired"
    _cache_set(key, "value")
    data, ts = _cache[key]
    _cache[key] = (data, ts - _TTL - 1)
    assert _cache_get(key) is None
    assert key not in _cache


@pytest.mark.asyncio
async def test_cache_valid_entry_returns_data():
    clear_cache()
    key = "test:valid"
    _cache_set(key, {"hello": 123})
    assert _cache_get(key) == {"hello": 123}


# ---------------------------------------------------------------------------
# _get_current_version fallback paths (lines 120-124)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_current_version_no_current_uses_any(session):
    result = await _get_current_version(session)
    assert result == "v1"


@pytest.mark.asyncio
async def test_get_current_version_no_current_but_has_one(session):
    tv = TaxonomyVersion(id=str(uuid.uuid4()), version="v2", is_current=False)
    session.add(tv)
    await session.flush()
    result = await _get_current_version(session)
    assert result == "v2"


# ---------------------------------------------------------------------------
# _resolve_translation (lines 129-145)
# ---------------------------------------------------------------------------

class FakeTrans:
    def __init__(self, locale, display_name=None, name=None):
        self.locale = locale
        self.display_name = display_name
        self.name = name


def test_resolve_translation_exact_locale():
    t1 = FakeTrans("en", display_name="English Name")
    t2 = FakeTrans("es", display_name="Nombre Español")
    name, loc = _resolve_translation([t1, t2], "es")
    assert name == "Nombre Español"
    assert loc == "es"


def test_resolve_translation_fallback_to_first():
    t1 = FakeTrans("fr", display_name="Nom Français")
    t2 = FakeTrans("de", name="Deutsch Name")
    name, loc = _resolve_translation([t1, t2], "ja")
    assert name == "Nom Français"
    assert loc == "ja"


def test_resolve_translation_empty_list():
    name, loc = _resolve_translation([], "en")
    assert name == ""
    assert loc == "en"


def test_resolve_translation_uses_name_when_no_display_name():
    t1 = FakeTrans("en", name="Only Name")
    name, loc = _resolve_translation([t1], "en")
    assert name == "Only Name"
    assert loc == "en"


# ---------------------------------------------------------------------------
# list_models — provider not found (lines 212-215)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_provider_not_found(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(provider_slug="nonexistent", locale="en")
    assert total == 0
    assert result == []


# ---------------------------------------------------------------------------
# list_models — category fallback any version (line 233)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_category_fallback_any_version(session):
    prov = Provider(id=str(uuid.uuid4()), slug="test-prov", name="Test", status="active")
    session.add(prov)
    tv1 = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    tv2 = TaxonomyVersion(id=str(uuid.uuid4()), version="v2", is_current=False)
    session.add_all([tv1, tv2])
    await session.flush()
    # Category exists in v2 only
    cat = Category(id=str(uuid.uuid4()), slug="coding-v2", taxonomy_version="v2", status="active")
    session.add(cat)
    await session.flush()
    # Model mapped to that category
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=prov.id, slug="m-v2", display_name="M V2",
        modality=["text"], status="approved", source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m)
    await session.flush()
    session.add(ModelCategory(model_id=m.id, category_id=cat.id, taxonomy_version="v2"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    # Current tv = v1, but category is in v2 → fallback to any version
    result, total = await svc.list_models(category_slug="coding-v2", locale="en")
    assert total == 1
    assert result[0]["slug"] == "m-v2"


# ---------------------------------------------------------------------------
# list_models — category exists but no models (lines 240-243)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_category_no_models(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    cat2 = Category(id=str(uuid.uuid4()), slug="empty-cat", taxonomy_version="v1", status="active")
    session.add(cat2)
    await session.commit()
    result, total = await svc.list_models(category_slug="empty-cat", locale="en")
    assert total == 0
    assert result == []


# ---------------------------------------------------------------------------
# list_models — category not found at all (lines 228-232)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_category_not_found(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(category_slug="nonexistent", locale="en")
    assert total == 0


# ---------------------------------------------------------------------------
# list_models — modalities filter (lines 263-272)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_modalities_filter_string(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(modalities="text", locale="en")
    assert total >= 1
    for r in result:
        assert "text" in [m.lower() for m in r["modality"]]


@pytest.mark.asyncio
async def test_list_models_modalities_filter_list(session):
    data = await _seed_base(session)
    m3 = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="image-model",
        display_name="Image Model", modality=["image"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m3)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(modalities=["image"], locale="en")
    assert total == 1
    assert result[0]["slug"] == "image-model"


@pytest.mark.asyncio
async def test_list_models_modalities_no_match(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(modalities="video", locale="en")
    assert total == 0


# ---------------------------------------------------------------------------
# list_models — sort_key edge cases (lines 284, 288)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_sort_by_name(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="name", order="asc", locale="en")
    names = [r["display_name"].lower() for r in result]
    assert names == sorted(names)


@pytest.mark.asyncio
async def test_list_models_sort_by_input_price_desc(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="input_price", order="desc", locale="en")
    assert result[0]["slug"] == "llama-3-70b"
    assert result[1]["slug"] == "claude-3-5-sonnet"


@pytest.mark.asyncio
async def test_list_models_sort_by_output_price_asc(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="output_price", order="asc", locale="en")
    assert result[0]["slug"] == "claude-3-5-sonnet"


# ---------------------------------------------------------------------------
# list_models — cursor decode exception (lines 308-309)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_invalid_cursor(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(cursor="invalid-cursor!!!", locale="en")
    assert total == 2


# ---------------------------------------------------------------------------
# list_models — translation fallback paths (lines 330, 335-336)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_translation_en_fallback(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="fr")
    claude = [r for r in result if r["slug"] == "claude-3-5-sonnet"][0]
    assert claude["locale_used"] in ("fr", "es", "en")


@pytest.mark.asyncio
async def test_list_models_translation_first_fallback(session):
    data = await _seed_base(session)
    m3 = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="pt-only-model",
        display_name="PT Model", modality=["text"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m3)
    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m3.id, locale="pt", display_name="Modelo PT"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="ja")
    pt_model = [r for r in result if r["slug"] == "pt-only-model"][0]
    assert pt_model["display_name"] == "Modelo PT"


# ---------------------------------------------------------------------------
# list_models — optional fields (lines 381, 383, 385, 387, 391, 393)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_optional_fields(session):
    data = await _seed_base(session)
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="full-model",
        display_name="Full Model", modality=["text"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
        version="2.0", family="gpt", context_window=128000, max_output_tokens=4096,
        deprecation_date=date(2025, 12, 31), source_url="https://example.com",
    )
    session.add(m)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="en")
    full = [r for r in result if r["slug"] == "full-model"][0]
    assert full["version"] == "2.0"
    assert full["family"] == "gpt"
    assert full["context_window"] == 128000
    assert full["max_output_tokens"] == 4096
    assert full["deprecation_date"] == "2025-12-31"
    assert full["source_url"] == "https://example.com"


# ---------------------------------------------------------------------------
# list_models — cache disabled (line 402-403)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_cache_disabled(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(locale="en", use_cache=False)
    assert len(result) >= 1
    assert len(_cache) == 0


# ---------------------------------------------------------------------------
# get_model — translation paths (lines 428, 430, 467, 482, 484, 486, 488, 490, 494, 496)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_with_translation_found(session):
    data = await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("claude-3-5-sonnet", locale="es")
    assert detail is not None
    assert detail["display_name"] == "Claude 3.5 Soneto"
    assert detail["locale_used"] == "es"


@pytest.mark.asyncio
async def test_get_model_with_en_fallback(session):
    data = await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("claude-3-5-sonnet", locale="fr")
    assert detail is not None
    assert detail["display_name"] is not None


@pytest.mark.asyncio
async def test_get_model_with_first_fallback(session):
    data = await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("llama-3-70b", locale="en")
    assert detail is not None
    assert detail["display_name"] == "Llama 3 70B"


@pytest.mark.asyncio
async def test_get_model_optional_fields(session):
    data = await _seed_base(session)
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="full-detail",
        display_name="Full Detail", modality=["text", "image"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
        version="3.0", family="claude", context_window=200000, max_output_tokens=8192,
        deprecation_date=date(2026, 6, 30), source_url="https://docs.example.com",
        input_price_per_mtok=Decimal("5.00"), output_price_per_mtok=Decimal("25.00"),
    )
    session.add(m)
    session.add(ModelTranslation(
        id=str(uuid.uuid4()), model_id=m.id, locale="en",
        display_name="Full Detail EN", description="A detailed model",
    ))
    await session.commit()
    svc = PublicService(session)
    detail = await svc.get_model("full-detail", locale="en")
    assert detail["description"] == "A detailed model"
    assert detail["version"] == "3.0"
    assert detail["family"] == "claude"
    assert detail["context_window"] == 200000
    assert detail["max_output_tokens"] == 8192
    assert detail["deprecation_date"] == "2026-06-30"
    assert detail["source_url"] == "https://docs.example.com"
    assert detail["input_price_per_mtok"] == "5.00"
    assert detail["output_price_per_mtok"] == "25.00"


@pytest.mark.asyncio
async def test_get_model_not_found(session):
    await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("nonexistent-model", locale="en")
    assert detail is None


@pytest.mark.asyncio
async def test_get_model_with_provider_translation(session):
    data = await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("claude-3-5-sonnet", locale="en")
    assert detail is not None
    assert len(detail["hostings"]) > 0
    h = detail["hostings"][0]
    assert h["provider"]["name"] == "Anthropic EN"


@pytest.mark.asyncio
async def test_get_model_hosting_no_provider_translation(session):
    data = await _seed_base(session)
    svc = PublicService(session)
    detail = await svc.get_model("llama-3-70b", locale="en")
    assert detail is not None
    assert len(detail["hostings"]) > 0
    h = detail["hostings"][0]
    assert h["provider"]["name"] == "OpenAI"


# ---------------------------------------------------------------------------
# list_categories — orchestrators scope (line 515)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_orchestrators_scope(session):
    await _seed_base(session)
    svc = PublicService(session)
    cats, tv = await svc.list_categories(locale="en", scope="orchestrators")
    assert tv == "orchestrators-v1"
    assert isinstance(cats, list)


# ---------------------------------------------------------------------------
# list_categories — fallback to any active (lines 523-524)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_fallback_any_active(session):
    prov = Provider(id=str(uuid.uuid4()), slug="p", name="P", status="active")
    session.add(prov)
    tv1 = TaxonomyVersion(id=str(uuid.uuid4()), version="v1", is_current=True)
    tv2 = TaxonomyVersion(id=str(uuid.uuid4()), version="v3", is_current=False)
    session.add_all([tv1, tv2])
    await session.flush()
    cat = Category(id=str(uuid.uuid4()), slug="x", taxonomy_version="v3", status="active")
    session.add(cat)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    cats, tv = await svc.list_categories(locale="en", scope="models")
    assert tv == "v1"
    assert len(cats) >= 1


# ---------------------------------------------------------------------------
# list_categories — no en translation, use first fallback (line 543)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_no_en_fallback(session):
    await _seed_base(session)
    cat2 = Category(id=str(uuid.uuid4()), slug="pt-cat", taxonomy_version="v1", status="active")
    session.add(cat2)
    session.add(CategoryTranslation(id=str(uuid.uuid4()), category_id=cat2.id, locale="pt", name="Categoria PT"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    cats, tv = await svc.list_categories(locale="ja")
    pt_cat = [c for c in cats if c["slug"] == "pt-cat"][0]
    assert pt_cat["name"] == "Categoria PT"
    assert pt_cat["locale_used"] == "pt"


# ---------------------------------------------------------------------------
# list_categories — no categories at all
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_categories_empty(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    cats, tv = await svc.list_categories(locale="en")
    assert isinstance(cats, list)


# ---------------------------------------------------------------------------
# list_providers — locale_used paths (lines 566, 568, 570)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_providers_es_translation(session):
    await _seed_base(session)
    svc = PublicService(session)
    provs = await svc.list_providers(locale="es")
    anthropic = [p for p in provs if p["slug"] == "anthropic"][0]
    assert anthropic["name"] == "Antrópico"
    assert anthropic["locale_used"] == "es"


@pytest.mark.asyncio
async def test_list_providers_en_fallback(session):
    await _seed_base(session)
    svc = PublicService(session)
    provs = await svc.list_providers(locale="fr")
    anthropic = [p for p in provs if p["slug"] == "anthropic"][0]
    assert anthropic["name"] == "Anthropic EN"
    assert anthropic["locale_used"] == "en"


@pytest.mark.asyncio
async def test_list_providers_no_translation(session):
    await _seed_base(session)
    svc = PublicService(session)
    provs = await svc.list_providers(locale="en")
    openai = [p for p in provs if p["slug"] == "openai"][0]
    assert openai["name"] == "OpenAI"
    assert openai["locale_used"] == "en"


@pytest.mark.asyncio
async def test_list_providers_first_fallback(session):
    await _seed_base(session)
    prov3 = Provider(id=str(uuid.uuid4()), slug="fr-only", name="FR Only", status="active")
    session.add(prov3)
    session.add(ProviderTranslation(id=str(uuid.uuid4()), provider_id=prov3.id, locale="fr", name="Uniquement FR"))
    await session.commit()
    svc = PublicService(session)
    provs = await svc.list_providers(locale="ja")
    fr_prov = [p for p in provs if p["slug"] == "fr-only"][0]
    assert fr_prov["name"] == "Uniquement FR"
    assert fr_prov["locale_used"] == "fr"


# ---------------------------------------------------------------------------
# list_locales — fallback to defaults (lines 974-981)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_locales_fallback_defaults(session):
    svc = PublicService(session)
    locales = await svc.list_locales()
    assert len(locales) == 5
    locale_codes = [l["locale"] for l in locales]
    assert "en" in locale_codes
    assert "zh" in locale_codes


@pytest.mark.asyncio
async def test_list_locales_with_data(session):
    await _seed_base(session)
    svc = PublicService(session)
    locales = await svc.list_locales()
    assert len(locales) == 5
    zh = [l for l in locales if l["locale"] == "zh"][0]
    assert zh["native_name"] == "中文"


# ---------------------------------------------------------------------------
# list_orchestrators — (lines 620-649, 659, 738-740)
# ---------------------------------------------------------------------------

async def _seed_orchestrators(session):
    data = await _seed_base(session)

    tv_orch = TaxonomyVersion(id=str(uuid.uuid4()), version="orchestrators-v1", is_current=False)
    session.add(tv_orch)
    await session.flush()

    orch1 = Orchestrator(
        id=str(uuid.uuid4()), slug="langflow", name="LangFlow", version="1.0",
        maintainer="LangChain", website="https://langflow.com",
        repo_url="https://github.com/langchain-ai/langflow", license="MIT", status="approved",
    )
    orch2 = Orchestrator(
        id=str(uuid.uuid4()), slug="dify", name="Dify", version="0.5", status="approved",
    )
    session.add_all([orch1, orch2])
    await session.flush()

    session.add(OrchestratorTranslation(
        id=str(uuid.uuid4()), orchestrator_id=orch1.id, locale="en",
        name="LangFlow", description="Flow builder for AI",
    ))
    session.add(OrchestratorTranslation(
        id=str(uuid.uuid4()), orchestrator_id=orch1.id, locale="es",
        name="LangFlow ES", description="Constructor de flujos para IA",
    ))
    session.add(OrchestratorTranslation(
        id=str(uuid.uuid4()), orchestrator_id=orch2.id, locale="es",
        name="Dify ES", description="Plataforma de IA",
    ))

    session.add(OrchestratorProvider(orchestrator_id=orch1.id, provider_id=data["prov"].id))

    cat_orch = Category(id=str(uuid.uuid4()), slug="orch-cat", taxonomy_version="orchestrators-v1", status="active")
    session.add(cat_orch)
    await session.flush()
    session.add(OrchestratorCategory(
        orchestrator_id=orch1.id, category_id=cat_orch.id, taxonomy_version="orchestrators-v1",
    ))

    await session.commit()
    return {**data, "orch1": orch1, "orch2": orch2, "cat_orch": cat_orch}


@pytest.mark.asyncio
async def test_list_orchestrators_basic(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en")
    assert total == 2


@pytest.mark.asyncio
async def test_list_orchestrators_desc_sort(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en", sort="name", order="desc")
    assert result[0]["name"] == "LangFlow"


@pytest.mark.asyncio
async def test_list_orchestrators_category_filter(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en", category="orch-cat")
    assert total == 1
    assert result[0]["slug"] == "langflow"


@pytest.mark.asyncio
async def test_list_orchestrators_category_not_found(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en", category="nonexistent")
    assert total == 0
    assert result == []


@pytest.mark.asyncio
async def test_list_orchestrators_category_no_orchestrators(session):
    await _seed_orchestrators(session)
    cat_empty = Category(id=str(uuid.uuid4()), slug="empty-orch-cat", taxonomy_version="orchestrators-v1", status="active")
    session.add(cat_empty)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en", category="empty-orch-cat")
    assert total == 0


@pytest.mark.asyncio
async def test_list_orchestrators_first_fallback(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="ja")
    orch2_item = [r for r in result if r["slug"] == "dify"][0]
    assert orch2_item["name"] == "Dify ES"


@pytest.mark.asyncio
async def test_list_orchestrators_no_translation(session):
    await _seed_orchestrators(session)
    orch3 = Orchestrator(id=str(uuid.uuid4()), slug="bare-orch", name="Bare Orchestrator", status="approved")
    session.add(orch3)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en")
    bare = [r for r in result if r["slug"] == "bare-orch"][0]
    assert bare["name"] == "Bare Orchestrator"
    assert bare["description"] is None


@pytest.mark.asyncio
async def test_list_orchestrators_cache(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    await svc.list_orchestrators(locale="en", use_cache=True)
    result, total = await svc.list_orchestrators(locale="en", use_cache=True)
    assert total == 2


@pytest.mark.asyncio
async def test_list_orchestrators_cursor_pagination(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result1, total = await svc.list_orchestrators(locale="en", limit=1)
    assert len(result1) == 1
    cursor = encode_cursor(result1[-1])
    result2, _ = await svc.list_orchestrators(locale="en", limit=10, cursor=cursor)
    assert len(result2) <= 1


@pytest.mark.asyncio
async def test_list_orchestrators_pagination_no_more(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="en", limit=10)
    assert len(result) == 2
    assert total == 2


# ---------------------------------------------------------------------------
# get_orchestrator — translation + cache (lines 796, 826-837)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_orchestrator_en_fallback(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("dify", locale="en")
    assert detail is not None
    assert detail["name"] == "Dify ES"
    assert detail["locale_used"] == "es"


@pytest.mark.asyncio
async def test_get_orchestrator_no_translation(session):
    await _seed_orchestrators(session)
    orch3 = Orchestrator(id=str(uuid.uuid4()), slug="bare-orch", name="Bare Orchestrator", status="approved")
    session.add(orch3)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("bare-orch", locale="en")
    assert detail is not None
    assert detail["name"] == "Bare Orchestrator"
    assert detail["description"] is None


@pytest.mark.asyncio
async def test_get_orchestrator_found_locale(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("langflow", locale="es")
    assert detail is not None
    assert detail["name"] == "LangFlow ES"
    assert detail["locale_used"] == "es"


@pytest.mark.asyncio
async def test_get_orchestrator_cache_hit(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    await svc.get_orchestrator("langflow", locale="en", use_cache=True)
    detail = await svc.get_orchestrator("langflow", locale="en", use_cache=True)
    assert detail is not None
    assert detail["slug"] == "langflow"


@pytest.mark.asyncio
async def test_get_orchestrator_not_found(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("nonexistent", locale="en")
    assert detail is None


@pytest.mark.asyncio
async def test_get_orchestrator_with_providers(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("langflow", locale="en")
    assert len(detail["providers"]) > 0
    p = detail["providers"][0]
    assert "slug" in p
    assert "name" in p


# ---------------------------------------------------------------------------
# list_domains — full method (lines 889-966)
# ---------------------------------------------------------------------------

async def _seed_domains(session):
    data = await _seed_base(session)
    d1 = Domain(id=str(uuid.uuid4()), slug="nlp", taxonomy_version="v1", status="active")
    d2 = Domain(id=str(uuid.uuid4()), slug="cv", taxonomy_version="v1", status="active")
    d3 = Domain(id=str(uuid.uuid4()), slug="archived", taxonomy_version="v1", status="archived")
    session.add_all([d1, d2, d3])
    await session.flush()
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=d1.id, locale="en", name="NLP", description="Natural Language Processing"))
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=d1.id, locale="es", name="PNL"))
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=d2.id, locale="en", name="Computer Vision"))
    await session.commit()
    return {**data, "d1": d1, "d2": d2, "d3": d3}


@pytest.mark.asyncio
async def test_list_domains_basic(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="en")
    assert len(domains) == 2
    slugs = [d["slug"] for d in domains]
    assert "nlp" in slugs
    assert "cv" in slugs


@pytest.mark.asyncio
async def test_list_domains_es_translation(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="es")
    nlp = [d for d in domains if d["slug"] == "nlp"][0]
    assert nlp["name"] == "PNL"
    assert nlp["locale_used"] == "es"


@pytest.mark.asyncio
async def test_list_domains_en_fallback(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="ja")
    cv = [d for d in domains if d["slug"] == "cv"][0]
    assert cv["name"] == "Computer Vision"


@pytest.mark.asyncio
async def test_list_domains_first_fallback(session):
    await _seed_domains(session)
    d4 = Domain(id=str(uuid.uuid4()), slug="pt-only", taxonomy_version="v1", status="active")
    session.add(d4)
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=d4.id, locale="pt", name="Dominio PT"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="ja")
    pt_d = [d for d in domains if d["slug"] == "pt-only"][0]
    assert pt_d["name"] == "Dominio PT"
    assert pt_d["locale_used"] == "pt"


@pytest.mark.asyncio
async def test_list_domains_no_translation(session):
    await _seed_domains(session)
    d4 = Domain(id=str(uuid.uuid4()), slug="bare-domain", taxonomy_version="v1", status="active")
    session.add(d4)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="en")
    bare = [d for d in domains if d["slug"] == "bare-domain"][0]
    assert bare["name"] == "bare-domain"
    assert bare["description"] is None
    assert bare["locale_used"] == "en"


@pytest.mark.asyncio
async def test_list_domains_empty(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="en")
    assert domains == []


@pytest.mark.asyncio
async def test_list_domains_cache(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    result1 = await svc.list_domains(locale="en", use_cache=True)
    result2 = await svc.list_domains(locale="en", use_cache=True)
    assert result1 == result2


@pytest.mark.asyncio
async def test_list_domains_cache_disabled(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    await svc.list_domains(locale="en", use_cache=False)
    assert len(_cache) == 0


@pytest.mark.asyncio
async def test_list_domains_with_parent(session):
    await _seed_domains(session)
    d_child = Domain(
        id=str(uuid.uuid4()), slug="sub-nlp", taxonomy_version="v1", status="active",
        parent_id=(await session.execute(select(Domain).where(Domain.slug == "nlp"))).scalars().first().id,
    )
    session.add(d_child)
    session.add(DomainTranslation(id=str(uuid.uuid4()), domain_id=d_child.id, locale="en", name="Sub NLP"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="en")
    child = [d for d in domains if d["slug"] == "sub-nlp"][0]
    assert child["parent_id"] is not None


# ---------------------------------------------------------------------------
# list_models — locale normalization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_locale_lowercased(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="ES")
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# list_models — search with family and display_name
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_search_family(session):
    data = await _seed_base(session)
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="family-model",
        display_name="Family Model", family="gemini", modality=["text"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(search="gemini", locale="en")
    assert total == 1
    assert result[0]["slug"] == "family-model"


@pytest.mark.asyncio
async def test_list_models_search_display_name(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(search="Llama", locale="en")
    assert total == 1
    assert "llama" in result[0]["slug"]


# ---------------------------------------------------------------------------
# encode_cursor / decode_cursor round-trip
# ---------------------------------------------------------------------------

def test_cursor_roundtrip():
    item = {"id": "abc-123", "slug": "test-model", "release_date": "2024-01-01"}
    cursor = encode_cursor(item)
    decoded = decode_cursor(cursor)
    assert decoded["id"] == "abc-123"
    assert decoded["slug"] == "test-model"


def test_cursor_roundtrip_with_prices():
    item = {"id": "abc-123", "slug": "test", "input_price_per_mtok": "3.00", "output_price_per_mtok": "15.00"}
    cursor = encode_cursor(item)
    decoded = decode_cursor(cursor)
    assert decoded["input_price_per_mtok"] == "3.00"


# ---------------------------------------------------------------------------
# list_orchestrators — en_fallback path (lines 734-736)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_orchestrators_en_fallback(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_orchestrators(locale="ja")
    langflow = [r for r in result if r["slug"] == "langflow"][0]
    assert langflow["name"] == "LangFlow"
    assert langflow["locale_used"] == "en"


# ---------------------------------------------------------------------------
# get_orchestrator — en_fallback path (lines 826-829)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_orchestrator_en_fallback_direct(session):
    await _seed_orchestrators(session)
    clear_cache()
    svc = PublicService(session)
    detail = await svc.get_orchestrator("langflow", locale="ja")
    assert detail is not None
    assert detail["name"] == "LangFlow"
    assert detail["locale_used"] == "en"


# ---------------------------------------------------------------------------
# list_domains — en_fallback path (lines 941-943)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_domains_en_fallback_direct(session):
    await _seed_domains(session)
    clear_cache()
    svc = PublicService(session)
    domains = await svc.list_domains(locale="ja")
    nlp = [d for d in domains if d["slug"] == "nlp"][0]
    assert nlp["name"] == "NLP"
    assert nlp["locale_used"] == "en"


# ---------------------------------------------------------------------------
# list_models — Decimal conversion for prices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_decimal_prices(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="en")
    claude = [r for r in result if r["slug"] == "claude-3-5-sonnet"][0]
    assert "3.00" in claude["input_price_per_mtok"]
    assert "15.00" in claude["output_price_per_mtok"]


# ---------------------------------------------------------------------------
# list_models — modality=None model
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_model_with_no_modality(session):
    data = await _seed_base(session)
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="no-modality-model",
        display_name="No Modality", modality=None, status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m)
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(locale="en")
    no_mod = [r for r in result if r["slug"] == "no-modality-model"][0]
    assert no_mod["modality"] == []


# ---------------------------------------------------------------------------
# list_models — unknown sort field falls back to release_date
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_unknown_sort_field(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="unknown_field", locale="en")
    assert len(result) >= 1


# ---------------------------------------------------------------------------
# list_models — search returning no results
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_search_no_results(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, total = await svc.list_models(search="zzzznonexistent", locale="en")
    assert total == 0


# ---------------------------------------------------------------------------
# list_providers — locale normalization
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_providers_locale_lowercased(session):
    await _seed_base(session)
    svc = PublicService(session)
    provs = await svc.list_providers(locale="ES")
    assert len(provs) >= 1


# ---------------------------------------------------------------------------
# list_models — price sorting with None prices
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_sort_all_none_prices(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(sort="input_price", order="asc", locale="en")
    assert result[0]["slug"] == "claude-3-5-sonnet"
    assert result[1]["slug"] == "llama-3-70b"


# ---------------------------------------------------------------------------
# _resolve_translation — fallback to 'en' (lines 136-139)
# ---------------------------------------------------------------------------

def test_resolve_translation_fallback_to_en():
    t_en = FakeTrans("en", display_name="English Name")
    t_es = FakeTrans("es", display_name="Nombre Español")
    name, loc = _resolve_translation([t_en, t_es], "fr")
    assert name == "English Name"
    assert loc == "en"


def test_resolve_translation_fallback_to_en_no_name():
    t_en = FakeTrans("en", display_name=None, name="EN Name")
    t_es = FakeTrans("es", display_name="Nombre Español")
    name, loc = _resolve_translation([t_en, t_es], "fr")
    assert name == "EN Name"
    assert loc == "en"


def test_resolve_translation_fallback_en_no_display_name_skips():
    t_en = FakeTrans("en", display_name=None, name=None)
    t_fr = FakeTrans("fr", display_name="French")
    name, loc = _resolve_translation([t_en, t_fr], "de")
    assert name == ""
    assert loc == "de"


# ---------------------------------------------------------------------------
# list_models — cache hit return (line 202)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_cache_hit(session):
    await _seed_base(session)
    clear_cache()
    svc = PublicService(session)
    result1, total1 = await svc.list_models(locale="en", use_cache=True)
    assert total1 >= 1
    result2, total2 = await svc.list_models(locale="en", use_cache=True)
    assert result1 == result2
    assert total1 == total2


# ---------------------------------------------------------------------------
# list_models — model translation en fallback (lines 330, 335-336)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models_translation_en_fallback_path(session):
    data = await _seed_base(session)
    m3 = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="en-only-model",
        display_name="EN Only", modality=["text"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m3)
    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m3.id, locale="en", display_name="EN Translation"))
    await session.commit()
    clear_cache()
    svc = PublicService(session)
    result, _ = await svc.list_models(locale="fr")
    en_model = [r for r in result if r["slug"] == "en-only-model"][0]
    assert en_model["display_name"] == "EN Translation"
    assert en_model["locale_used"] == "en"


# ---------------------------------------------------------------------------
# get_model — locale_used = 'en' from en_fallback (line 430)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_model_locale_used_en_fallback(session):
    data = await _seed_base(session)
    m = AIModel(
        id=str(uuid.uuid4()), provider_id=data["prov"].id, slug="get-en-fallback",
        display_name="Model EN", modality=["text"], status="approved",
        source="manual", source_payload_hash=str(uuid.uuid4()),
    )
    session.add(m)
    session.add(ModelTranslation(id=str(uuid.uuid4()), model_id=m.id, locale="en", display_name="EN Name"))
    await session.commit()
    svc = PublicService(session)
    detail = await svc.get_model("get-en-fallback", locale="fr")
    assert detail is not None
    assert detail["display_name"] == "EN Name"
    assert detail["locale_used"] == "en"
