from collections.abc import Sequence
from decimal import Decimal

from app.schemas.catalog import CatalogModel, ModelModality


CATALOG: tuple[CatalogModel, ...] = (
    CatalogModel(
        slug="claude-3-7-sonnet",
        display_name="Claude 3.7 Sonnet",
        provider="Anthropic",
        family="Claude",
        modalities=[ModelModality.TEXT, ModelModality.VISION, ModelModality.CODE, ModelModality.REASONING],
        context_window=200_000,
        input_price_per_mtok=Decimal("3"),
        output_price_per_mtok=Decimal("15"),
        categories=["coding", "debugging", "reasoning", "documentation"],
        source="manual",
    ),
    CatalogModel(
        slug="gpt-4.1",
        display_name="GPT-4.1",
        provider="OpenAI",
        family="GPT",
        modalities=[ModelModality.TEXT, ModelModality.VISION, ModelModality.CODE],
        context_window=1_000_000,
        input_price_per_mtok=Decimal("2"),
        output_price_per_mtok=Decimal("8"),
        categories=["coding", "documentation", "vision", "architecture"],
        source="manual",
    ),
    CatalogModel(
        slug="gemini-2-5-pro",
        display_name="Gemini 2.5 Pro",
        provider="Google",
        family="Gemini",
        modalities=[ModelModality.TEXT, ModelModality.VISION, ModelModality.CODE, ModelModality.REASONING],
        context_window=1_000_000,
        input_price_per_mtok=Decimal("1.25"),
        output_price_per_mtok=Decimal("10"),
        categories=["reasoning", "coding", "architecture", "vision"],
        source="manual",
    ),
    CatalogModel(
        slug="deepseek-r1",
        display_name="DeepSeek R1",
        provider="DeepSeek",
        family="DeepSeek",
        modalities=[ModelModality.TEXT, ModelModality.REASONING, ModelModality.CODE],
        context_window=128_000,
        input_price_per_mtok=Decimal("0.55"),
        output_price_per_mtok=Decimal("2.19"),
        categories=["reasoning", "coding", "debugging"],
        source="manual",
    ),
    CatalogModel(
        slug="llama-4-maverick",
        display_name="Llama 4 Maverick",
        provider="Meta",
        family="Llama",
        modalities=[ModelModality.TEXT, ModelModality.VISION, ModelModality.CODE],
        context_window=1_000_000,
        input_price_per_mtok=Decimal("0.15"),
        output_price_per_mtok=Decimal("0.60"),
        categories=["coding", "vision", "documentation"],
        source="manual",
    ),
)


def list_models(
    *,
    query: str | None = None,
    category: str | None = None,
    modality: ModelModality | None = None,
    provider: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> tuple[Sequence[CatalogModel], int]:
    normalized_query = query.casefold().strip() if query else None
    normalized_category = category.casefold().strip() if category else None
    normalized_provider = provider.casefold().strip() if provider else None

    filtered = [
        model
        for model in CATALOG
        if (
            not normalized_query
            or normalized_query in model.display_name.casefold()
            or normalized_query in model.slug.casefold()
            or normalized_query in model.provider.casefold()
        )
        and (not normalized_category or normalized_category in model.categories)
        and (not modality or modality in model.modalities)
        and (not normalized_provider or normalized_provider == model.provider.casefold())
    ]
    return filtered[offset : offset + limit], len(filtered)


def compare_models(slugs: list[str]) -> tuple[list[CatalogModel], list[str]]:
    requested = list(dict.fromkeys(slugs))
    by_slug = {model.slug: model for model in CATALOG}
    items = [by_slug[slug] for slug in requested if slug in by_slug]
    missing = [slug for slug in requested if slug not in by_slug]
    return items, missing
