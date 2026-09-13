"""Seed data — idempotent admin + taxonomy with validation."""

import hashlib
import json
import pathlib
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models.user import User, RoleEnum
from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    IngestionSource,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
)
from app.taxonomy.services.core import normalize_slug

ADMIN_EMAIL = "admin@forcecast.dev"
ADMIN_DISPLAY_NAME = "Forcecast Admin"

LOCALES = ["en", "es", "pt", "fr", "zh"]


class SeedValidationError(Exception):
    pass


async def seed_admin(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.email == ADMIN_EMAIL))
    existing = result.scalars().first()
    if existing:
        updated = False
        role_val = existing.role.value if hasattr(existing.role, "value") else str(existing.role)
        if role_val != "admin":
            existing.role = RoleEnum.ADMIN
            updated = True
        if not existing.email_verified:
            existing.email_verified = True
            updated = True
        if updated:
            await db.flush()
        return existing
    admin = User(
        id=str(uuid.uuid4()),
        email=ADMIN_EMAIL,
        display_name=ADMIN_DISPLAY_NAME,
        avatar_url=None,
        role=RoleEnum.ADMIN,
        reputation_score=5.0,
        email_verified=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(admin)
    await db.flush()
    return admin


def _load_json(path: pathlib.Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _hash_payload(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def validate_seed_files(seeds_dir: str | pathlib.Path = "seeds") -> bool:
    p = pathlib.Path(seeds_dir)
    # --- providers ---
    prov_path = p / "providers.json"
    if not prov_path.exists():
        raise SeedValidationError(f"Missing {prov_path}")
    providers = _load_json(prov_path)
    if len(providers) < 10:
        raise SeedValidationError(f"providers.json must have >=10, got {len(providers)}")
    # --- models ---
    models_path = p / "models.json"
    models = _load_json(models_path)
    if len(models) < 30:
        raise SeedValidationError(f"models.json must have >=30, got {len(models)}")
    # --- categories ---
    cats_path = p / "categories.json"
    categories = _load_json(cats_path)
    if len(categories) != 17:
        raise SeedValidationError(f"categories.json must have 17, got {len(categories)}")
    # --- ingestion sources ---
    src_path = p / "ingestion_sources.json"
    sources = _load_json(src_path)
    if len(sources) != 3:
        raise SeedValidationError(f"ingestion_sources.json must have 3, got {len(sources)}")
    codes = {s["code"] for s in sources}
    if codes != {"openrouter", "huggingface", "lmsys"}:
        raise SeedValidationError(f"ingestion sources codes must be openrouter/huggingface/lmsys, got {codes}")
    # --- hostings ---
    host_path = p / "model_hostings.json"
    hostings = _load_json(host_path)
    if len(hostings) < 30:
        raise SeedValidationError(f"model_hostings.json must have >=30, got {len(hostings)}")
    forbidden = {"input_price_override", "output_price_override", "price", "cost", "input_price_per_mtok", "output_price_per_mtok"}
    for i, row in enumerate(hostings):
        found = forbidden & set(row.keys())
        if found:
            raise SeedValidationError(f"model_hostings.json row {i} has forbidden price fields {found}")
    # --- translations ---
    cat_slugs = {c["slug"] for c in categories}
    prov_slugs = {prov["slug"] for prov in providers}
    model_slugs = {m["slug"] for m in models}
    for locale in LOCALES:
        tf = p / f"translations_{locale}.json"
        if not tf.exists():
            alt = p / "translations" / f"{locale}.json"
            if alt.exists():
                tf = alt
            else:
                raise SeedValidationError(f"Missing translation file for locale {locale}: {tf}")
        trans = _load_json(tf)
        for key in ["categories", "providers", "models"]:
            if key not in trans:
                raise SeedValidationError(f"{locale} missing key {key}")
        for slug in cat_slugs:
            if slug not in trans["categories"]:
                raise SeedValidationError(f"Missing translation for category '{slug}' in locale '{locale}'")
            if "name" not in trans["categories"][slug]:
                raise SeedValidationError(f"Category '{slug}' locale '{locale}' missing name")
        for slug in prov_slugs:
            if slug not in trans["providers"]:
                raise SeedValidationError(f"Missing translation for provider '{slug}' in locale '{locale}'")
            if "name" not in trans["providers"][slug]:
                raise SeedValidationError(f"Provider '{slug}' locale '{locale}' missing name")
        for slug in model_slugs:
            if slug not in trans["models"]:
                raise SeedValidationError(f"Missing translation for model '{slug}' in locale '{locale}'")
            if "display_name" not in trans["models"][slug]:
                raise SeedValidationError(f"Model '{slug}' locale '{locale}' missing display_name")
    return True


async def seed_taxonomy(session: AsyncSession, seeds_dir: str | pathlib.Path = "seeds") -> dict:
    await validate_seed_files(seeds_dir)
    p = pathlib.Path(seeds_dir)
    providers = _load_json(p / "providers.json")
    models = _load_json(p / "models.json")
    categories_json = _load_json(p / "categories.json")
    sources = _load_json(p / "ingestion_sources.json")
    hostings = _load_json(p / "model_hostings.json")

    # Ensure taxonomy version v1
    result = await session.execute(select(TaxonomyVersion).where(TaxonomyVersion.version == "v1"))
    v1 = result.scalar_one_or_none()
    if not v1:
        v1 = TaxonomyVersion(
            id=str(uuid.uuid4()),
            version="v1",
            released_at=datetime.now(timezone.utc),
            notes="Seed v1",
            is_current=True,
        )
        session.add(v1)
        await session.flush()
    elif not v1.is_current:
        v1.is_current = True
        await session.flush()

    # Providers upsert
    slug_to_provider: dict[str, Provider] = {}
    for prov in providers:
        slug = normalize_slug(prov["slug"])
        result = await session.execute(select(Provider).where(Provider.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = prov.get("name", existing.name)
            existing.website = prov.get("website", existing.website)
            existing.api_docs_url = prov.get("api_docs_url", existing.api_docs_url)
            existing.logo_url = prov.get("logo_url", existing.logo_url)
            existing.status = prov.get("status", existing.status)
            existing.updated_at = datetime.now(timezone.utc)
            await session.flush()
            slug_to_provider[slug] = existing
        else:
            new = Provider(
                id=str(uuid.uuid4()),
                slug=slug,
                name=prov["name"],
                website=prov.get("website"),
                api_docs_url=prov.get("api_docs_url"),
                logo_url=prov.get("logo_url"),
                status=prov.get("status", "active"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(new)
            await session.flush()
            await session.refresh(new)
            slug_to_provider[slug] = new
        # also map original slug
        slug_to_provider[prov["slug"]] = slug_to_provider[slug]

    # Ingestion sources upsert
    for src in sources:
        result = await session.execute(select(IngestionSource).where(IngestionSource.code == src["code"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = src["name"]
            existing.parser_class = src["parser_class"]
            existing.rate_limit_rpm = src.get("rate_limit_rpm", existing.rate_limit_rpm)
            existing.base_url = src.get("base_url", existing.base_url)
            await session.flush()
        else:
            new = IngestionSource(
                code=src["code"],
                name=src["name"],
                parser_class=src["parser_class"],
                rate_limit_rpm=src.get("rate_limit_rpm", 60),
                base_url=src.get("base_url"),
            )
            session.add(new)
            await session.flush()

    # Categories upsert - two passes for parent resolution
    # First ensure all categories exist
    slug_to_cat: dict[str, Category] = {}
    for cat in categories_json:
        slug = normalize_slug(cat["slug"])
        result = await session.execute(select(Category).where(Category.slug == slug, Category.taxonomy_version == "v1"))
        existing = result.scalar_one_or_none()
        if existing:
            slug_to_cat[slug] = existing
            slug_to_cat[cat["slug"]] = existing
        else:
            new = Category(
                id=str(uuid.uuid4()),
                slug=slug,
                parent_id=None,
                taxonomy_version="v1",
                status=cat.get("status", "active"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(new)
            await session.flush()
            await session.refresh(new)
            slug_to_cat[slug] = new
            slug_to_cat[cat["slug"]] = new
    # Second pass: set parents
    for cat in categories_json:
        slug = normalize_slug(cat["slug"])
        parent_slug = cat.get("parent_slug")
        if parent_slug:
            parent = slug_to_cat.get(normalize_slug(parent_slug)) or slug_to_cat.get(parent_slug)
            child = slug_to_cat.get(slug)
            if parent and child and child.parent_id != parent.id:
                child.parent_id = parent.id
                await session.flush()

    # Provider translations + Category translations + Model translations will be done after models (to have IDs)

    # Models upsert
    slug_to_model: dict[str, AIModel] = {}
    for m in models:
        slug = normalize_slug(m["slug"])
        provider_slug = m["provider_slug"]
        provider = slug_to_provider.get(provider_slug) or slug_to_provider.get(normalize_slug(provider_slug))
        if not provider:
            result = await session.execute(select(Provider).where(Provider.slug == normalize_slug(provider_slug)))
            provider = result.scalar_one_or_none()
            if not provider:
                raise SeedValidationError(f"Provider {provider_slug} not found for model {slug}")
            slug_to_provider[provider_slug] = provider
        # hash
        payload_hash = m.get("source_payload_hash") or _hash_payload({"slug": slug, "provider_slug": provider_slug, "display_name": m["display_name"]})
        # prices to Decimal
        def to_decimal(v):
            if v is None:
                return None
            return Decimal(str(v))
        input_price = to_decimal(m.get("input_price_per_mtok"))
        output_price = to_decimal(m.get("output_price_per_mtok"))
        # release date
        rel_date = None
        if m.get("release_date"):
            try:
                rel_date = date.fromisoformat(m["release_date"])
            except Exception:
                rel_date = None
        modality = m.get("modality", ["text"])
        # Find existing by slug
        result = await session.execute(select(AIModel).where(AIModel.slug == slug))
        existing = result.scalar_one_or_none()
        if existing:
            existing.display_name = m["display_name"]
            existing.provider_id = provider.id
            existing.version = m.get("version")
            existing.family = m.get("family")
            existing.modality = modality
            existing.context_window = m.get("context_window")
            existing.max_output_tokens = m.get("max_output_tokens")
            existing.input_price_per_mtok = input_price
            existing.output_price_per_mtok = output_price
            existing.release_date = rel_date
            existing.status = m.get("status", existing.status)
            existing.source = m.get("source", existing.source)
            existing.source_url = m.get("source_url", existing.source_url)
            # do not overwrite hash if existing has one? keep existing
            existing.updated_at = datetime.now(timezone.utc)
            await session.flush()
            slug_to_model[slug] = existing
            slug_to_model[m["slug"]] = existing
        else:
            new = AIModel(
                id=str(uuid.uuid4()),
                provider_id=provider.id,
                slug=slug,
                display_name=m["display_name"],
                version=m.get("version"),
                family=m.get("family"),
                modality=modality,
                context_window=m.get("context_window"),
                max_output_tokens=m.get("max_output_tokens"),
                input_price_per_mtok=input_price,
                output_price_per_mtok=output_price,
                release_date=rel_date,
                status=m.get("status", "draft"),
                source=m.get("source", "manual"),
                source_payload_hash=payload_hash,
                source_url=m.get("source_url"),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(new)
            await session.flush()
            await session.refresh(new)
            slug_to_model[slug] = new
            slug_to_model[m["slug"]] = new
        # ModelCategory associations
        for cat_slug in m.get("categories", []):
            cat = slug_to_cat.get(normalize_slug(cat_slug)) or slug_to_cat.get(cat_slug)
            if not cat:
                continue
            result = await session.execute(
                select(ModelCategory).where(
                    ModelCategory.model_id == slug_to_model[slug].id,
                    ModelCategory.category_id == cat.id,
                    ModelCategory.taxonomy_version == "v1",
                )
            )
            if not result.scalar_one_or_none():
                link = ModelCategory(
                    model_id=slug_to_model[slug].id,
                    category_id=cat.id,
                    taxonomy_version="v1",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(link)
                await session.flush()

    # Model hostings upsert
    for h in hostings:
        model_slug = normalize_slug(h["model_slug"])
        provider_slug = normalize_slug(h["provider_slug"])
        model = slug_to_model.get(model_slug) or slug_to_model.get(h["model_slug"])
        provider = slug_to_provider.get(provider_slug) or slug_to_provider.get(h["provider_slug"])
        if not model or not provider:
            continue
        result = await session.execute(
            select(ModelHosting).where(ModelHosting.model_id == model.id, ModelHosting.provider_id == provider.id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.endpoint_url = h.get("endpoint_url", existing.endpoint_url)
            existing.status = h.get("status", existing.status)
            existing.is_primary = h.get("is_primary", existing.is_primary)
            existing.updated_at = datetime.now(timezone.utc)
            await session.flush()
        else:
            new = ModelHosting(
                id=str(uuid.uuid4()),
                model_id=model.id,
                provider_id=provider.id,
                endpoint_url=h.get("endpoint_url"),
                status=h.get("status", "active"),
                is_primary=h.get("is_primary", True),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.add(new)
            await session.flush()

    # Translations upsert
    for locale in LOCALES:
        tf = p / f"translations_{locale}.json"
        if not tf.exists():
            alt = p / "translations" / f"{locale}.json"
            if alt.exists():
                tf = alt
        trans = _load_json(tf)
        # provider translations
        for slug, t in trans.get("providers", {}).items():
            norm = normalize_slug(slug)
            prov = slug_to_provider.get(norm) or slug_to_provider.get(slug)
            if not prov:
                continue
            result = await session.execute(
                select(ProviderTranslation).where(ProviderTranslation.provider_id == prov.id, ProviderTranslation.locale == locale)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = t["name"]
                existing.description = t.get("description")
                await session.flush()
            else:
                new = ProviderTranslation(
                    id=str(uuid.uuid4()),
                    provider_id=prov.id,
                    locale=locale,
                    name=t["name"],
                    description=t.get("description"),
                )
                session.add(new)
                await session.flush()
        # category translations
        for slug, t in trans.get("categories", {}).items():
            norm = normalize_slug(slug)
            cat = slug_to_cat.get(norm) or slug_to_cat.get(slug)
            if not cat:
                continue
            result = await session.execute(
                select(CategoryTranslation).where(CategoryTranslation.category_id == cat.id, CategoryTranslation.locale == locale)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = t["name"]
                existing.description = t.get("description")
                await session.flush()
            else:
                new = CategoryTranslation(
                    id=str(uuid.uuid4()),
                    category_id=cat.id,
                    locale=locale,
                    name=t["name"],
                    description=t.get("description"),
                )
                session.add(new)
                await session.flush()
        # model translations
        for slug, t in trans.get("models", {}).items():
            norm = normalize_slug(slug)
            model = slug_to_model.get(norm) or slug_to_model.get(slug)
            if not model:
                continue
            result = await session.execute(
                select(ModelTranslation).where(ModelTranslation.model_id == model.id, ModelTranslation.locale == locale)
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.display_name = t["display_name"]
                existing.description = t.get("description")
                await session.flush()
            else:
                new = ModelTranslation(
                    id=str(uuid.uuid4()),
                    model_id=model.id,
                    locale=locale,
                    display_name=t["display_name"],
                    description=t.get("description"),
                )
                session.add(new)
                await session.flush()

    return {
        "providers": len(slug_to_provider),
        "categories": len(slug_to_cat),
        "models": len(slug_to_model),
        "hostings": len(hostings),
    }


async def seed_all(db: AsyncSession) -> dict:
    admin = await seed_admin(db)
    tax = await seed_taxonomy(db)
    return {"admin": str(admin.id), **tax}


if __name__ == "__main__":
    import argparse
    import asyncio
    from app.db.session import async_session_maker, engine, Base

    parser = argparse.ArgumentParser(description="Seed Forcecast DB")
    parser.add_argument("--file", default="seeds/", help="Seeds directory")
    parser.add_argument("--validate-only", action="store_true", help="Only validate seed files")
    args = parser.parse_args()

    async def _run():
        if args.validate_only:
            try:
                await validate_seed_files(args.file)
                print("Seed validation passed")
            except SeedValidationError as e:
                print(f"Seed validation failed: {e}")
                raise SystemExit(1)
            return
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with async_session_maker() as session:
            await seed_admin(session)
            await seed_taxonomy(session, seeds_dir=args.file)
            await session.commit()
            print(f"Seeded admin {ADMIN_EMAIL} + taxonomy")

    asyncio.run(_run())
