"""Public service — i18n, FTS, Redis cache, pagination."""
from __future__ import annotations

import base64
import hashlib
import json
import time
from decimal import Decimal
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.taxonomy.models.entities import (
    AIModel,
    Category,
    CategoryTranslation,
    LocaleMeta,
    ModelCategory,
    ModelHosting,
    ModelTranslation,
    Provider,
    ProviderTranslation,
    TaxonomyVersion,
)

# ---------------------------------------------------------------------------
# Cache (Redis with in-memory fallback) TTL 60s
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[Any, float]] = {}
_TTL = 60

try:
    import redis.asyncio as redis  # type: ignore

    _redis_client = None

    def _get_redis():
        global _redis_client
        if _redis_client is None:
            try:
                from app.core.config import settings

                _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            except Exception:
                return None
        return _redis_client

except Exception:
    _redis_client = None

    def _get_redis():  # type: ignore
        return None


def cache_key(filters: dict, locale: str, taxonomy_version: str) -> str:
    payload = json.dumps({"filters": filters, "locale": locale, "taxonomy_version": taxonomy_version}, sort_keys=True, default=str)
    return "taxonomy:public:" + hashlib.sha256(payload.encode()).hexdigest()


def clear_cache() -> None:
    _cache.clear()


def _cache_get(key: str) -> Any | None:
    val = _cache.get(key)
    if val is None:
        return None
    data, ts = val
    if time.time() - ts > _TTL:
        _cache.pop(key, None)
        return None
    return data


def _cache_set(key: str, value: Any) -> None:
    _cache[key] = (value, time.time())


def encode_cursor(item: dict) -> str:
    # item must have id and sort value; we encode id and slug for simplicity
    payload = {"id": item.get("id"), "slug": item.get("slug")}
    # also include sort value if present
    for k in ("release_date", "input_price_per_mtok", "output_price_per_mtok", "display_name"):
        if k in item and item[k] is not None:
            payload[k] = str(item[k])
    raw = json.dumps(payload).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> dict:
    pad = "=" * (-len(cursor) % 4)
    raw = base64.urlsafe_b64decode(cursor + pad)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


SORT_MAP = {
    "release_date": "release_date",
    "input_price": "input_price_per_mtok",
    "output_price": "output_price_per_mtok",
    "name": "display_name",
    "display_name": "display_name",
    "input_price_per_mtok": "input_price_per_mtok",
    "output_price_per_mtok": "output_price_per_mtok",
}


async def _get_current_version(session: AsyncSession) -> str:
    result = await session.execute(select(TaxonomyVersion).where(TaxonomyVersion.is_current == True))  # noqa: E712
    cur = result.scalar_one_or_none()
    if cur:
        return cur.version
    # fallback: any version
    result2 = await session.execute(select(TaxonomyVersion).limit(1))
    any_v = result2.scalar_one_or_none()
    if any_v:
        return any_v.version
    return "v1"


def _resolve_translation(translations: list, locale: str, fallback="en") -> tuple[str, str]:
    # translations: list of objects with locale attr and name/display_name attr
    by_locale = {t.locale: t for t in translations}
    if locale in by_locale:
        obj = by_locale[locale]
        name = getattr(obj, "display_name", None) or getattr(obj, "name", None)
        if name:
            return name, locale
    if fallback in by_locale:
        obj = by_locale[fallback]
        name = getattr(obj, "display_name", None) or getattr(obj, "name", None)
        if name:
            return name, fallback
    # fallback to first
    if translations:
        obj = translations[0]
        name = getattr(obj, "display_name", None) or getattr(obj, "name", None)
        return name or "", locale
    return "", locale


# ---------------------------------------------------------------------------
# PublicService
# ---------------------------------------------------------------------------


class PublicService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def invalidate_cache(self) -> None:
        clear_cache()
        # try redis flush pattern if available
        r = _get_redis()
        if r:
            try:
                async with r:
                    await r.flushdb()
            except Exception:
                pass

    async def list_models(
        self,
        category_slug: str | None = None,
        provider_slug: str | None = None,
        modalities: str | list[str] | None = None,
        search: str | None = None,
        locale: str = "en",
        limit: int = 20,
        cursor: str | None = None,
        sort: str = "release_date",
        order: str = "desc",
        use_cache: bool = True,
    ) -> tuple[list[dict], int]:
        # Normalize
        locale = str(locale).lower()
        sort_field = SORT_MAP.get(sort, "release_date")
        # Cache key
        filters = {
            "category_slug": category_slug,
            "provider_slug": provider_slug,
            "modalities": modalities,
            "search": search,
            "limit": limit,
            "cursor": cursor,
            "sort": sort,
            "order": order,
        }
        tv = await _get_current_version(self.session)
        # Isolate cache per DB engine to avoid cross-test contamination
        engine_id = str(id(self.session.bind) if self.session.bind is not None else "no-bind")
        key = cache_key(filters, locale, tv) + f":{engine_id}"
        if use_cache:
            cached = _cache_get(key)
            if cached is not None:
                return cached

        # Build base query
        stmt = select(AIModel).where(AIModel.status == "approved")

        # Provider filter
        if provider_slug:
            prov_result = await self.session.execute(select(Provider).where(Provider.slug == provider_slug))
            prov = prov_result.scalar_one_or_none()
            if not prov:
                result_empty: tuple[list[dict], int] = ([], 0)
                if use_cache:
                    _cache_set(key, result_empty)
                return result_empty
            stmt = stmt.where(AIModel.provider_id == prov.id)

        # Category filter
        if category_slug:
            cat_result = await self.session.execute(
                select(Category).where(Category.slug == category_slug, Category.taxonomy_version == tv)
            )
            cat = cat_result.scalar_one_or_none()
            if not cat:
                # try any version
                cat_result2 = await self.session.execute(select(Category).where(Category.slug == category_slug))
                cat2 = cat_result2.scalar_one_or_none()
                if not cat2:
                    result_empty = ([], 0)
                    if use_cache:
                        _cache_set(key, result_empty)
                    return result_empty
                cat = cat2
            # get model ids for category
            mc_result = await self.session.execute(
                select(ModelCategory.model_id).where(ModelCategory.category_id == cat.id)
            )
            model_ids = [r[0] for r in mc_result.all()]
            if not model_ids:
                result_empty = ([], 0)
                if use_cache:
                    _cache_set(key, result_empty)
                return result_empty
            stmt = stmt.where(AIModel.id.in_(model_ids))

        # Search (simple LIKE)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    AIModel.slug.ilike(pattern),
                    AIModel.display_name.ilike(pattern),
                    AIModel.family.ilike(pattern),
                )
            )

        # Execute to get all matching before pagination (small dataset)
        result = await self.session.execute(stmt)
        models = list(result.scalars().all())

        # Modalities filter (python side, JSON field)
        if modalities:
            if isinstance(modalities, str):
                modalities = [modalities]
            modalities = [m.lower() for m in modalities]
            filtered = []
            for m in models:
                mods = m.modality or []
                mods_lower = [str(x).lower() for x in mods]
                if any(mod in mods_lower for mod in modalities):
                    filtered.append(m)
            models = filtered

        # Sorting
        reverse = order == "desc"

        def sort_key(m: AIModel):
            val = getattr(m, sort_field, None)
            # None last
            is_none = val is None
            # For descending, we want None last, so tuple (is_none, val) works with reverse handling
            # Normalize val for comparison
            if isinstance(val, str):
                val = val.lower()
            if val is None:
                # placeholder for sorting
                if sort_field in ("input_price_per_mtok", "output_price_per_mtok"):
                    val = Decimal("-1") if reverse else Decimal("999999")
                else:
                    val = ""
            return (is_none, val, m.id)

        models.sort(key=sort_key, reverse=reverse)

        total = len(models)

        # Cursor pagination: find index after cursor
        start_idx = 0
        if cursor:
            try:
                cur_data = decode_cursor(cursor)
                cur_id = cur_data.get("id")
                # Find position of cur_id
                for idx, m in enumerate(models):
                    if m.id == cur_id:
                        start_idx = idx + 1
                        break
            except Exception:
                start_idx = 0

        paginated = models[start_idx : start_idx + limit]

        # Build response dicts with i18n and price omission
        items: list[dict] = []
        for m in paginated:
            # Translations
            trans_result = await self.session.execute(select(ModelTranslation).where(ModelTranslation.model_id == m.id))
            trans_list = list(trans_result.scalars().all())
            display_name = m.display_name
            locale_used = locale
            if trans_list:
                # find requested locale
                found = None
                fallback_en = None
                for t in trans_list:
                    if t.locale == locale:
                        found = t
                        break
                    if t.locale == "en":
                        fallback_en = t
                if found and found.display_name:
                    display_name = found.display_name
                    locale_used = locale
                elif fallback_en and fallback_en.display_name:
                    display_name = fallback_en.display_name
                    locale_used = "en"
                else:
                    # use first
                    display_name = trans_list[0].display_name or display_name
                    locale_used = trans_list[0].locale

            # Categories for this model
            cat_rows = await self.session.execute(select(ModelCategory).where(ModelCategory.model_id == m.id))
            cat_links = list(cat_rows.scalars().all())
            cats: list[dict] = []
            for mc in cat_links:
                c = await self.session.get(Category, mc.category_id)
                if c:
                    # translation
                    ct_result = await self.session.execute(select(CategoryTranslation).where(CategoryTranslation.category_id == c.id))
                    ct_list = list(ct_result.scalars().all())
                    cname = c.slug
                    if ct_list:
                        # try locale
                        cloc = next((x for x in ct_list if x.locale == locale), None)
                        if cloc:
                            cname = cloc.name
                        else:
                            en_ct = next((x for x in ct_list if x.locale == "en"), None)
                            if en_ct:
                                cname = en_ct.name
                    cats.append({"slug": c.slug, "name": cname})

            # Provider summary
            prov = await self.session.get(Provider, m.provider_id)
            prov_summary = {"slug": prov.slug if prov else "unknown", "name": prov.name if prov else prov_slug or "unknown"}

            item: dict[str, Any] = {
                "id": m.id,
                "slug": m.slug,
                "display_name": display_name,
                "modality": m.modality or [],
                "status": m.status,
                "source": m.source,
                "locale_used": locale_used,
                "categories": cats,
                "provider": prov_summary,
            }
            # optional fields
            if m.version is not None:
                item["version"] = m.version
            if m.family is not None:
                item["family"] = m.family
            if m.context_window is not None:
                item["context_window"] = m.context_window
            if m.max_output_tokens is not None:
                item["max_output_tokens"] = m.max_output_tokens
            if m.release_date is not None:
                item["release_date"] = str(m.release_date)
            if m.deprecation_date is not None:
                item["deprecation_date"] = str(m.deprecation_date)
            if m.source_url is not None:
                item["source_url"] = m.source_url
            # prices omitted when None
            if m.input_price_per_mtok is not None:
                item["input_price_per_mtok"] = str(m.input_price_per_mtok) if isinstance(m.input_price_per_mtok, Decimal) else m.input_price_per_mtok
            if m.output_price_per_mtok is not None:
                item["output_price_per_mtok"] = str(m.output_price_per_mtok) if isinstance(m.output_price_per_mtok, Decimal) else m.output_price_per_mtok
            items.append(item)

        result_tuple: tuple[list[dict], int] = (items, total)
        if use_cache:
            _cache_set(key, result_tuple)
        return result_tuple

    async def get_model(self, slug: str, locale: str = "en") -> dict | None:
        locale = str(locale).lower()
        result = await self.session.execute(select(AIModel).where(AIModel.slug == slug, AIModel.status == "approved"))
        m = result.scalar_one_or_none()
        if not m:
            return None

        # translations
        trans_result = await self.session.execute(select(ModelTranslation).where(ModelTranslation.model_id == m.id))
        trans_list = list(trans_result.scalars().all())
        display_name = m.display_name
        description = None
        locale_used = locale
        if trans_list:
            found = next((t for t in trans_list if t.locale == locale), None)
            en_fallback = next((t for t in trans_list if t.locale == "en"), None)
            chosen = found or en_fallback or trans_list[0]
            if chosen:
                display_name = chosen.display_name or display_name
                description = chosen.description
                locale_used = chosen.locale if chosen == found else (chosen.locale if chosen == en_fallback else trans_list[0].locale)
                if found:
                    locale_used = locale
                elif en_fallback:
                    locale_used = "en"

        # categories
        cat_rows = await self.session.execute(select(ModelCategory).where(ModelCategory.model_id == m.id))
        cat_links = list(cat_rows.scalars().all())
        cats: list[dict] = []
        for mc in cat_links:
            c = await self.session.get(Category, mc.category_id)
            if c:
                ct_result = await self.session.execute(select(CategoryTranslation).where(CategoryTranslation.category_id == c.id))
                ct_list = list(ct_result.scalars().all())
                cname = c.slug
                cdesc = None
                if ct_list:
                    cloc = next((x for x in ct_list if x.locale == locale), None)
                    en_ct = next((x for x in ct_list if x.locale == "en"), None)
                    chosen_ct = cloc or en_ct or ct_list[0]
                    cname = chosen_ct.name if chosen_ct else c.slug
                    cdesc = chosen_ct.description if chosen_ct else None
                cats.append({"slug": c.slug, "name": cname, "description": cdesc})

        # hostings
        host_result = await self.session.execute(select(ModelHosting).where(ModelHosting.model_id == m.id))
        hostings = list(host_result.scalars().all())
        host_list: list[dict] = []
        for h in hostings:
            prov = await self.session.get(Provider, h.provider_id)
            prov_sum = {"slug": prov.slug if prov else "unknown", "name": prov.name if prov else "unknown"}
            # translate provider name
            if prov:
                pt_result = await self.session.execute(select(ProviderTranslation).where(ProviderTranslation.provider_id == prov.id))
                pt_list = list(pt_result.scalars().all())
                if pt_list:
                    pt_loc = next((x for x in pt_list if x.locale == locale), None)
                    en_pt = next((x for x in pt_list if x.locale == "en"), None)
                    chosen_pt = pt_loc or en_pt
                    if chosen_pt:
                        prov_sum["name"] = chosen_pt.name
            host_list.append({"provider": prov_sum, "is_primary": bool(h.is_primary)})

        item: dict[str, Any] = {
            "id": m.id,
            "slug": m.slug,
            "display_name": display_name,
            "modality": m.modality or [],
            "status": m.status,
            "source": m.source,
            "locale_used": locale_used,
            "categories": cats,
            "hostings": host_list,
        }
        if description is not None:
            item["description"] = description
        if m.version is not None:
            item["version"] = m.version
        if m.family is not None:
            item["family"] = m.family
        if m.context_window is not None:
            item["context_window"] = m.context_window
        if m.max_output_tokens is not None:
            item["max_output_tokens"] = m.max_output_tokens
        if m.release_date is not None:
            item["release_date"] = str(m.release_date)
        if m.deprecation_date is not None:
            item["deprecation_date"] = str(m.deprecation_date)
        if m.source_url is not None:
            item["source_url"] = m.source_url
        if m.input_price_per_mtok is not None:
            item["input_price_per_mtok"] = str(m.input_price_per_mtok) if isinstance(m.input_price_per_mtok, Decimal) else m.input_price_per_mtok
        if m.output_price_per_mtok is not None:
            item["output_price_per_mtok"] = str(m.output_price_per_mtok) if isinstance(m.output_price_per_mtok, Decimal) else m.output_price_per_mtok
        return item

    async def list_categories(self, locale: str = "en") -> tuple[list[dict], str]:
        locale = str(locale).lower()
        tv = await _get_current_version(self.session)
        result = await self.session.execute(select(Category).where(Category.status == "active", Category.taxonomy_version == tv))
        cats = list(result.scalars().all())
        # fallback: if no cats for current version, try any active
        if not cats:
            result2 = await self.session.execute(select(Category).where(Category.status == "active"))
            cats = list(result2.scalars().all())
        items: list[dict] = []
        for c in cats:
            ct_result = await self.session.execute(select(CategoryTranslation).where(CategoryTranslation.category_id == c.id))
            ct_list = list(ct_result.scalars().all())
            name = c.slug
            desc = None
            locale_used = locale
            if ct_list:
                found = next((x for x in ct_list if x.locale == locale), None)
                en_fallback = next((x for x in ct_list if x.locale == "en"), None)
                chosen = found or en_fallback or ct_list[0]
                name = chosen.name if chosen else c.slug
                desc = chosen.description if chosen else None
                if found:
                    locale_used = locale
                elif en_fallback:
                    locale_used = "en"
                else:
                    locale_used = chosen.locale if chosen else locale
            items.append({"slug": c.slug, "name": name, "description": desc, "taxonomy_version": c.taxonomy_version, "locale_used": locale_used})
        return items, tv

    async def list_providers(self, locale: str = "en") -> list[dict]:
        locale = str(locale).lower()
        result = await self.session.execute(select(Provider).where(Provider.status == "active"))
        provs = list(result.scalars().all())
        items: list[dict] = []
        for p in provs:
            pt_result = await self.session.execute(select(ProviderTranslation).where(ProviderTranslation.provider_id == p.id))
            pt_list = list(pt_result.scalars().all())
            name = p.name
            desc = None
            locale_used = locale
            if pt_list:
                found = next((x for x in pt_list if x.locale == locale), None)
                en_fallback = next((x for x in pt_list if x.locale == "en"), None)
                chosen = found or en_fallback or pt_list[0]
                if chosen:
                    name = chosen.name
                    desc = chosen.description
                    if found:
                        locale_used = locale
                    elif en_fallback:
                        locale_used = "en"
                    else:
                        locale_used = chosen.locale
            items.append({"slug": p.slug, "name": name, "description": desc, "website": p.website, "status": p.status, "locale_used": locale_used})
        return items

    async def list_locales(self) -> list[dict]:
        result = await self.session.execute(select(LocaleMeta))
        locales = list(result.scalars().all())
        if not locales:
            # fallback to enum defaults

            defaults = {
                "en": ("English", "ltr"),
                "es": ("Español", "ltr"),
                "pt": ("Português", "ltr"),
                "fr": ("Français", "ltr"),
                "zh": ("中文", "ltr"),
            }
            return [
                {"locale": k, "native_name": v[0], "direction": v[1], "plural_categories": ["one", "other"]}
                for k, v in defaults.items()
            ]
        return [
            {"locale": lm.locale, "native_name": lm.native_name, "direction": lm.direction, "plural_categories": lm.plural_categories or ["one", "other"]}
            for lm in locales
        ]
