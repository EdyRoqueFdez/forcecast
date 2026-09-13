# Public API Specification

## Purpose

Define the public read API — 5 endpoints exposing approved models, categories, providers, and locale metadata. Responses use standardized envelope, keyset pagination, Redis caching, and full-text search with GIN indexes. Only approved models and active categories are returned. **Price fields are reference-only and omitted when null.**

## Requirements

### Requirement: Standard Response Envelope

The system SHALL wrap all paginated responses in an envelope: {data: [...], meta: {page, limit, total, has_more, next_cursor}, links: {first, prev, next, last}}. Non-paginated endpoints use {data: [...]}.

#### Scenario: Paginated Response

- GIVEN 42 approved models exist
- WHEN requesting GET /api/v1/models?limit=20
- THEN response contains data with 20 items, meta.total=42, meta.has_more=true, and links.next present

#### Scenario: Empty Result

- GIVEN no models match a filter
- WHEN requesting GET /api/v1/models?category_slug=nonexistent
- THEN response contains data=[], meta.total=0, meta.has_more=false

### Requirement: Standard Error Envelope

The system SHALL return errors in RFC 7807 Problem Details format: {error: {code, message, details: [{field, issue}], trace_id}}. Appropriate HTTP status codes: 400, 401, 403, 404, 406, 409, 422, 429, 500.

#### Scenario: Validation Error

- GIVEN a request with invalid query parameter page_size=-1
- WHEN the server processes the request
- THEN response is 422 with error.code="VALIDATION_ERROR" and details mentioning page_size

### Requirement: List Models

The system SHALL expose GET /api/v1/models with query params: category_slug, provider_slug, modalities (repeated), lang (default en), search, cursor (keyset), limit (default 20, max 100), sort (release_date|input_price|output_price|name, default release_date), order (asc|desc, default desc). Only approved models returned.

#### Scenario: Filter by Category and Language

- GIVEN approved models in category "coding" with Spanish translations
- WHEN requesting GET /api/v1/models?category_slug=coding&lang=es
- THEN response includes models in "coding" with Spanish display_name and locale_used="es"

#### Scenario: Full-Text Search

- GIVEN models with display_name containing "claude"
- WHEN requesting GET /api/v1/models?search=claude
- THEN matching models are returned ranked by relevance

#### Scenario: Keyset Pagination

- GIVEN 100 approved models
- WHEN requesting GET /api/v1/models?limit=20&cursor=<opaque>
- THEN the next 20 models are returned with a new cursor

### Requirement: Get Model Detail

The system SHALL expose GET /api/v1/models/{slug} returning full model detail including description, source, source_url, deprecation_date, categories, hostings (provider + is_primary only, no prices), and locale_used. **Price fields (input_price_per_mtok, output_price_per_mtok) are included only when non-null.** No `price_unknown` flag.

#### Scenario: Model With Prices

- GIVEN a model with input_price_per_mtok=3.00 and output_price_per_mtok=15.00
- WHEN requesting GET /api/v1/models/claude-3-5-sonnet
- THEN response includes input_price_per_mtok="3.00" and output_price_per_mtok="15.00"

#### Scenario: Model Without Prices

- GIVEN a model with both price fields null
- WHEN requesting GET /api/v1/models/llama-3-70b
- THEN response omits input_price_per_mtok and output_price_per_mtok entirely (no null, no price_unknown)

#### Scenario: Hostings Without Prices

- GIVEN a model with two hostings (anthropic primary, together secondary)
- WHEN requesting GET /api/v1/models/llama-3-70b
- THEN hostings array contains [{provider: {slug: "anthropic", name: "Anthropic"}, is_primary: true}, {provider: {slug: "together", name: "Together"}, is_primary: false}] with no price fields

#### Scenario: Model Not Found

- GIVEN no model with slug "nonexistent" exists
- WHEN requesting GET /api/v1/models/nonexistent
- THEN the system returns 404 with error.code="NOT_FOUND"

### Requirement: List Categories

The system SHALL expose GET /api/v1/categories with query param lang (default en). Returns active categories in current taxonomy_version with translated names and descriptions. Response includes meta.taxonomy_version.

#### Scenario: Categories with Translation

- GIVEN active categories in taxonomy_version="v1" with Chinese translations
- WHEN requesting GET /api/v1/categories?lang=zh
- THEN response contains categories with Chinese names and meta.taxonomy_version="v1"

### Requirement: List Providers

The system SHALL expose GET /api/v1/providers with query param lang (default en). Returns active providers with translated names.

#### Scenario: Providers Excludes Deprecated

- GIVEN providers "anthropic" (active) and "old-provider" (deprecated)
- WHEN requesting GET /api/v1/providers
- THEN only "anthropic" is returned

### Requirement: List Locales

The system SHALL expose GET /api/v1/locales returning LocaleMeta entities: locale, native_name, direction, plural_categories.

#### Scenario: Locale Metadata

- WHEN requesting GET /api/v1/locales
- THEN response contains 5 locales with native_name, direction, and plural_categories

### Requirement: Redis Caching

The system SHALL cache public GET responses in Redis keyed by (filters_hash, locale, taxonomy_version) with TTL 60s. Cache SHALL be invalidated on model approval, ingestion completion, and taxonomy version activation.

#### Scenario: Cache Hit

- GIVEN a cached response for GET /api/v1/models?category_slug=coding&lang=en
- WHEN the same request arrives within 60s
- THEN Redis returns the cached response without DB query

#### Scenario: Cache Invalidation

- GIVEN a cached response for models in category "coding"
- WHEN a new model is approved in "coding"
- THEN the cache is invalidated and next request hits DB