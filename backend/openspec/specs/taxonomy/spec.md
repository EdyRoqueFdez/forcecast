# Spec: Taxonomy IA

- Path: `forcecast/specs/openspec/specs/taxonomy/spec.md`
- Version: `1.2.0`
- Status: `Draft`
- Owner: `Forcecast Core Team`
- Taxonomy Version: `v1`
- Last Updated: `2026-09-11`

## 1. Purpose

Define the canonical catalog of AI providers, models, and task categories used across Forcecast. This taxonomy is the vocabulary of the domain: every opinion, comparison, vote, and recommendation references entities defined here.

Without a stable, versioned, internationalized taxonomy, no other domain (Auth, Voting, Context, MCP) can operate reliably.

**Clarification:** Forcecast is a **comparison/voting platform**, not a model marketplace. Prices are **reference information only** (cost per 1M tokens from canonical sources like OpenRouter) so users can factor cost into their votes. No billing, no override pricing, no per-hosting price differences.

## 2. Scope

### In scope

- Providers (OpenAI, Anthropic, Google, Meta, DeepSeek, Qwen, Mistral, Cohere, xAI, ...)
- AI models (name, version, family, modality, context window, **reference pricing**, dates, status)
- Task categories (architecture, coding, debugging, documentation, ...)
- Internationalization (EN, ES, PT, FR, ZH) with fallback
- Taxonomy versioning
- Ingestion from external sources (OpenRouter, Hugging Face, LMSYS)
- Manual approval workflow for models
- Public read API + admin write API
- Initial seed data
- **Model-Hosting association (multi-provider readiness for v1 schema — no pricing)**
- **Webhook events for model lifecycle**
- **Standardized error envelope and pagination**
- **Rate limiting headers**

### Out of scope

- User authentication and authorization (Sprint 1)
- Voting, comparisons, scoring (Sprint 2)
- Reputation system
- MCP server and agent SDK
- Recommendation engine
- Admin UI beyond SQLAdmin basics
- Automated scheduled ingestion (cron) — manual endpoint only in MVP
- Model benchmarking results storage
- **Billing, charging, or per-hosting price overrides**

## 3. Glossary

| Term | Definition |
| --- | --- |
| Provider | Company or org that publishes AI models. |
| AIModel | A specific versioned model offered by a provider. |
| ModelHosting | A deployment of a model on a specific provider (enables multi-provider models like Llama on Meta/Together/Groq). **No pricing fields.** |
| Category | A task or capability area used to contextualize opinions. |
| Taxonomy Version | Immutable snapshot of the category tree. |
| Locale | Language code: en, es, pt, fr, zh. |
| Slug | URL-safe canonical identifier. |
| Ingestion | Process of importing models from external sources. |
| Approval | Admin action that moves a model from `pending_review` to `approved`. |
| Webhook | HTTP callback for async model lifecycle events. |

## 4. Domain Entities

### 4.1 Provider

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| slug | str | unique, normalized |
| name | str | required |
| website | URL | nullable |
| api_docs_url | URL | nullable |
| logo_url | URL | nullable |
| status | enum | active, deprecated, banned |
| created_at | datetime | auto |
| updated_at | datetime | auto |

### 4.2 AIModel

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| slug | str | unique globally, normalized |
| display_name | str | required |
| version | str | nullable |
| family | str | nullable |
| modality | list[enum] | text, vision, audio, code, embedding, **reasoning** |
| context_window | int | nullable, > 0 |
| max_output_tokens | int | nullable, > 0 |
| **input_price_per_mtok** | **Decimal** | **nullable, ≥ 0 (reference only)** |
| **output_price_per_mtok** | **Decimal** | **nullable, ≥ 0 (reference only)** |
| release_date | date | nullable |
| deprecation_date | date | nullable |
| status | enum | draft, pending_review, approved, rejected, deprecated |
| source | enum | openrouter, huggingface, lmsys, manual |
| source_url | URL | nullable |
| source_payload_hash | str | **NOT NULL**, default '', used for dedupe |
| created_at | datetime | auto |
| updated_at | datetime | auto |

**Unique Constraints (DB-level):**
- `(provider_id, slug)` — **enforces R2 deduplication at DB level**
- `(provider_id, family, version)` — **enforces R2 deduplication at DB level**
- `source_payload_hash` — **NOT NULL with default, unique index for dedupe**

### 4.3 ModelHosting (v1 schema, v2 API exposure — **no pricing**)

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| model_id | UUID | FK → AIModel, ON DELETE CASCADE |
| provider_id | UUID | FK → Provider, ON DELETE RESTRICT |
| endpoint_url | URL | nullable |
| status | enum | active, deprecated |
| is_primary | bool | default false, **unique per model_id where true** |
| created_at | datetime | auto |
| updated_at | datetime | auto |

**Unique Constraint:** `(model_id, provider_id)`
**Index:** `(model_id, is_primary)` partial where `is_primary = true`

**v1 behavior:** One row per model (the "primary" hosting). v2 exposes multiple. **No price fields.**

### 4.4 Category

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| slug | str | unique per taxonomy_version |
| parent_id | UUID | FK → Category, nullable, **ON DELETE RESTRICT** |
| taxonomy_version | str | **FK → TaxonomyVersion.version, ON DELETE RESTRICT** |
| status | enum | active, deprecated |
| created_at | datetime | auto |
| updated_at | datetime | auto |

### 4.5 ModelCategory (association table)

| Field | Type | Constraints |
| --- | --- | --- |
| model_id | UUID | FK → AIModel, **ON DELETE CASCADE** |
| category_id | UUID | FK → Category, **ON DELETE RESTRICT** |
| taxonomy_version | str | **FK → TaxonomyVersion.version, ON DELETE RESTRICT** |
| created_at | datetime | auto |

**Primary Key:** `(model_id, category_id, taxonomy_version)`
**Indexes:** `(category_id, taxonomy_version)`, `(model_id)`

### 4.6 CategoryTranslation

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| category_id | UUID | FK → Category, **ON DELETE CASCADE** |
| locale | enum | en, es, pt, fr, zh |
| name | str | required |
| description | text | nullable |

**Unique constraint:** `(category_id, locale)`.

### 4.7 ModelTranslation

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| model_id | UUID | FK → AIModel, **ON DELETE CASCADE** |
| locale | enum | en, es, pt, fr, zh |
| display_name | str | required |
| description | text | nullable |

**Unique constraint:** `(model_id, locale)`.

### 4.8 ProviderTranslation

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| provider_id | UUID | FK → Provider, **ON DELETE CASCADE** |
| locale | enum | en, es, pt, fr, zh |
| name | str | required |
| description | text | nullable |

**Unique constraint:** `(provider_id, locale)`.

### 4.9 TaxonomyVersion

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| version | str | unique |
| released_at | datetime | required |
| notes | text | nullable |
| is_current | bool | **partial unique index WHERE is_current = true** |

**Immutability Enforcement (DB-level):**
- Trigger `prevent_historical_category_change` blocks UPDATE/DELETE on Category where `taxonomy_version != (SELECT version FROM TaxonomyVersion WHERE is_current)`
- Same trigger for CategoryTranslation, ModelCategory

### 4.10 IngestionRun

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| source | str | **FK → IngestionSource.code, ON DELETE RESTRICT** |
| started_at | datetime | auto |
| finished_at | datetime | nullable |
| status | enum | running, success, partial, failed |
| models_found | int | default 0 |
| models_created | int | default 0 |
| models_updated | int | default 0 |
| models_skipped | int | default 0 |
| errors | JSONB | nullable, **schema: `{model_slug: string, error: string, field?: string}[]`** |

### 4.11 IngestionSource (enum table)

| Field | Type | Constraints |
| --- | --- | --- |
| code | str | PK (openrouter, huggingface, lmsys) |
| name | str | required |
| parser_class | str | required |
| rate_limit_rpm | int | default 60 |
| base_url | URL | nullable |

### 4.12 WebhookRegistration

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| url | URL | required |
| secret | str | required (HMAC-SHA256) |
| events | text[] | required, subset of: `model.approved`, `model.rejected`, `model.deprecated`, `ingestion.completed`, `taxonomy.version_activated` |
| is_active | bool | default true |
| created_at | datetime | auto |
| updated_at | datetime | auto |

### 4.13 WebhookDelivery

| Field | Type | Constraints |
| --- | --- | --- |
| id | UUID | PK |
| webhook_id | UUID | FK → WebhookRegistration, ON DELETE CASCADE |
| event_type | str | required |
| payload | JSONB | required |
| delivery_id | str | unique, idempotency key |
| attempt | int | default 1 |
| status | enum | pending, delivered, failed, dead_letter |
| response_status | int | nullable |
| response_body | text | nullable |
| error | text | nullable |
| created_at | datetime | auto |
| delivered_at | datetime | nullable |
| next_retry_at | datetime | nullable |

**Retry Policy:** Exponential backoff (1m, 5m, 15m, 1h, 6h), max 5 attempts.

### 4.14 LocaleMeta

| Field | Type | Constraints |
| --- | --- | --- |
| locale | str | PK (en, es, pt, fr, zh) |
| native_name | str | required |
| direction | enum | ltr, rtl |
| plural_categories | text[] | required (e.g., `['one', 'other']`) |
| week_start | int | 0-6 (Sunday=0) |

## 5. Business Rules

### R1 — Uniqueness

- `Provider.slug` is globally unique.
- `AIModel.slug` is globally unique.
- `Category.slug` is unique per taxonomy version.
- `(category_id, locale)`, `(model_id, locale)`, `(provider_id, locale)` are unique in translation tables.
- Only one `TaxonomyVersion.is_current = true` at any time (**enforced by partial unique index**).
- `ModelHosting`: one `is_primary = true` per `model_id` (**enforced by partial unique index**).
- `ModelCategory`: unique `(model_id, category_id, taxonomy_version)`.

### R2 — Deduplication on ingestion (DB-ENFORCED)

A model is a duplicate if any of the following match:

- `provider_id + normalized slug` — **DB unique constraint**
- `provider_id + normalized family + normalized version` — **DB unique constraint**
- `source_payload_hash` — **DB unique constraint (NOT NULL, default '')**

On duplicate, update the existing record (upsert) and do not create a new one.
Ingestion uses `INSERT ... ON CONFLICT DO UPDATE` for atomicity.
Advisory lock (`pg_advisory_xact_lock`) per source prevents concurrent runs.

### R3 — Slug normalization

Algorithm:

1. Lowercase
2. Trim whitespace
3. **Unicode NFKC normalization** (handles composed/decomposed chars)
4. **Transliterate non-Latin scripts** (zh → pinyin via `pypinyin`, others via ICU)
5. Replace spaces, dots, slashes, parentheses with hyphens
6. Remove non-alphanumeric characters except hyphens
7. Collapse multiple hyphens into one
8. Strip leading and trailing hyphens
9. Truncate to 255 chars

Example:
- `Claude 3.5 Sonnet (2024-10-22)` → `claude-3-5-sonnet-2024-10-22`
- `文心一言 4.0` → `wen-xin-yi-yan-4-0` (pinyin)

**Property-based tests:** idempotent, deterministic, no leading/trailing hyphens, no double hyphens, only alphanumeric+hyphen, lowercase only.

### R4 — Model status transitions

Allowed transitions:

- `draft` → `pending_review`
- `pending_review` → `approved`
- `pending_review` → `rejected`
- `approved` → `deprecated`

Any other transition is rejected with `409 Conflict`.

Only approved models appear in the public API.

**State machine properties (property-based):** valid transitions form a DAG, every non-terminal state has outgoing transition, invalid always returns 409.

### R5 — i18n fallback

Resolution order when requesting `lang=X`:

1. Translation for `X`
2. Translation for `en`
3. Base `display_name` / `name`

The response includes `locale_used` to indicate which locale was served.

**Locale negotiation priority:** explicit `lang` query param > `Accept-Language` header > default (`en`).

**Response headers:** `Content-Language: <locale_used>`, `Vary: Accept-Language, Accept-Charset`.

**Unsupported locale:** Returns `406 Not Acceptable` with `{supported: ['en','es','pt','fr','zh']}` and `Link` headers for alternates.

### R6 — Pricing (reference only)

- Stored as `Decimal`, never float
- **Nullable: a model can be approved without pricing**
- **API response omits price fields when both are null** (no `price_unknown` flag)
- **Single reference price per model** (from canonical source: OpenRouter). No per-hosting overrides.
- Comparisons and sorting must tolerate `None`

### R7 — Taxonomy versioning

Any change to the category tree (add, remove, rename, reparent) creates a new `TaxonomyVersion`.

- Existing versions are immutable (**DB trigger enforced**)
- Votes and comparisons store the taxonomy version active at creation time
- Only one version is `is_current` (**partial unique index**)
- **Provider and AIModel are version-agnostic** (current state only). Historical context for votes comes from TaxonomyVersion on Category + ModelCategory. Provider/model changes tracked via AuditLog (separate domain).

### R8 — Approval workflow

- Ingested models enter as `pending_review`
- Only users with role `admin` can approve or reject
- Approval requires: `provider_id`, `slug`, `display_name`, `modality`, **at least one ModelHosting row**
- Rejection requires a reason (stored in `WebhookDelivery` payload and `AuditLog`)

### R9 — Ingestion

- Supported sources: OpenRouter, Hugging Face, LMSYS (via `IngestionSource` table)
- Each source has its own parser implementing a common interface
- Ingestion is idempotent: running twice produces no duplicates (**DB constraints + upsert**)
- Per-model errors do not abort the run; the run finishes as `partial` and logs errors
- Every run creates an `IngestionRun` record
- **Batched upserts (500-1000 rows/batch) for performance**

### R10 — Public read vs admin write

- Public endpoints return only approved models and active categories
- Admin endpoints require authentication and role `admin` (**JWT with `role: admin` claim or API key `fk_admin_*`**)
- Admin endpoints can return `draft`, `pending_review`, `rejected`, and `deprecated`
- **Admin responses include internal fields**: `source_payload_hash`, `created_by`, `audit_log_id`
- **Separate OpenAPI spec for admin API** (prevents internal exposure in public SDK)

### R11 — Rate limiting

- Headers on ALL responses: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- On 429: `Retry-After` (seconds), `X-RateLimit-Reset` (unix timestamp)
- Tiers: anonymous 60/min, authenticated 300/min, admin 1000/min
- Scope: per IP (anonymous), per user (authenticated)

### R12 — Webhook events

Core events: `model.approved`, `model.rejected`, `model.deprecated`, `ingestion.completed`, `taxonomy.version_activated`

Event payload envelope:
```json
{
  "id": "uuid",
  "type": "model.approved",
  "timestamp": "2026-09-10T12:00:00Z",
  "taxonomy_version": "v1",
  "data": { ... }
}
```

Headers: `X-Forcecast-Signature` (HMAC-SHA256), `X-Forcecast-Delivery-Id` (idempotency), `X-Forcecast-Timestamp` (replay protection).

## 6. Category Taxonomy v1

Initial canonical categories (`slug` / EN name):

| Slug | EN Name | Parent |
| --- | --- | --- |
| `architecture` | Architecture | — |
| `system_design` | System Design | `architecture` |
| `coding` | Coding | — |
| `debugging` | Debugging | `coding` |
| `refactoring` | Refactoring | `coding` |
| `testing` | Testing | — |
| `documentation` | Documentation | — |
| `research` | Research | — |
| `math` | Math | — |
| `logical_reasoning` | Logical Reasoning | — |
| `creative_writing` | Creative Writing | — |
| `translation` | Translation | — |
| `multimodal` | Multimodal | — |
| `security` | Security | — |
| `devops` | DevOps | — |
| `ux_product` | UX & Product | — |
| `data_analysis` | Data Analysis | — |

Translations required for: en, es, pt, fr, zh.

Source basis: LMSYS Chatbot Arena, Stanford HELM, SWEBOK v4.

## 7. Use Cases

UC1 — List approved models by category and language
```
GET /api/v1/models?category=coding&lang=es
```
Returns approved models, with translated display names, filtered by category.

UC2 — Get model detail
```
GET /api/v1/models/{slug}?lang=fr
```
Returns full model detail with translations, categories, hostings (no prices), and `locale_used`.

UC3 — List categories
```
GET /api/v1/categories?lang=zh
```
Returns active categories in current taxonomy version with translated descriptions.

UC4 — List providers
```
GET /api/v1/providers?lang=pt
```
Returns providers with translated names.

UC5 — Search models
```
GET /api/v1/models?q=claude&lang=zh
```
Full-text search on slug, display_name, family, **and all translations**.

UC6 — Trigger ingestion (admin)
```
POST /api/v1/admin/ingestion/run
{ "source": "openrouter" }
```
Runs ingestion, returns IngestionRun. Emits `ingestion.completed` webhook.

UC7 — Approve model (admin)
```
POST /api/v1/admin/models/{id}/approve
```
Emits `model.approved` webhook.

UC8 — Reject model (admin)
```
POST /api/v1/admin/models/{id}/reject
{ "reason": "Duplicate of claude-3-5-sonnet" }
```
Emits `model.rejected` webhook.

UC9 — Create taxonomy version (admin)
```
POST /api/v1/admin/taxonomy/versions
{ "version": "v2", "notes": "Added agentic_workflows" }
```

UC10 — Activate taxonomy version (admin)
```
POST /api/v1/admin/taxonomy/versions/{id}/activate
```
Emits `taxonomy.version_activated` webhook.

UC11 — Register webhook (admin)
```
POST /api/v1/admin/webhooks
{ "url": "https://app.example.com/webhooks", "events": ["model.approved"], "secret": "..." }
```

UC12 — List locales
```
GET /api/v1/locales
```
Returns locale metadata (native_name, direction, plural_categories).

## 8. API Contracts

### Standard Response Envelope (ALL paginated endpoints)

```json
{
  "data": [...],
  "meta": {
    "page": 1,
    "limit": 20,
    "total": 42,
    "has_more": true,
    "next_cursor": "opaque-cursor-base64"
  },
  "links": {
    "first": "/api/v1/models?limit=20",
    "prev": null,
    "next": "/api/v1/models?limit=20&cursor=opaque-cursor-base64",
    "last": "/api/v1/models?limit=20&cursor=last-cursor"
  }
}
```

### Standard Error Envelope (RFC 7807 Problem Details)

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid query parameter",
    "details": [{"field": "page_size", "issue": "must be <= 100"}],
    "trace_id": "uuid"
  }
}
```

### 8.1 Public: GET /api/v1/models

**Query params:**
- `category_slug` (slug, optional)
- `provider_slug` (slug, optional)
- `modalities` (repeated, optional) — `?modalities=text&modalities=code`
- `lang` (en | es | pt | fr | zh, default en)
- `search` (optional, full-text across base + translations)
- `cursor` (opaque, optional) — **keyset pagination**
- `limit` (int, default 20, max 100)
- `sort` (release_date | input_price | output_price | name, default release_date)
- `order` (asc | desc, default desc)

**Response:** Standard envelope with items:

```json
{
  "slug": "claude-3-5-sonnet-20241022",
  "display_name": "Claude 3.5 Sonnet",
  "provider": { "slug": "anthropic", "name": "Anthropic" },
  "family": "claude-3-5",
  "version": "20241022",
  "modality": ["text", "vision", "code", "reasoning"],
  "context_window": 200000,
  "max_output_tokens": 8192,
  "input_price_per_mtok": "3.00",
  "output_price_per_mtok": "15.00",
  "release_date": "2024-10-22",
  "status": "approved",
  "locale_used": "es",
  "categories": ["coding", "architecture"],
  "hostings": [
    { "provider": { "slug": "anthropic", "name": "Anthropic" }, "is_primary": true }
  ]
}
```

**Note:** Price fields included only when non-null. No `price_unknown` flag. Hostings array shows provider + primary flag only.

### 8.2 Public: GET /api/v1/models/{slug}

Same shape as item above, plus:
- `description`: translated or fallback
- `source`, `source_url`
- `deprecation_date`

### 8.3 Public: GET /api/v1/categories

**Query params:** `lang` (en | es | pt | fr | zh, default en)

```json
{
  "data": [
    {
      "slug": "coding",
      "name": "Coding",
      "description": "Writing, reviewing, and generating code",
      "parent_slug": null,
      "locale_used": "en"
    }
  ],
  "meta": { "taxonomy_version": "v1" }
}
```

### 8.4 Public: GET /api/v1/providers

**Query params:** `lang` (en | es | pt | fr | zh, default en)

```json
{
  "data": [
    {
      "slug": "anthropic",
      "name": "Anthropic",
      "description": "AI safety and research company",
      "website": "https://anthropic.com",
      "status": "active",
      "locale_used": "en"
    }
  ]
}
```

### 8.5 Public: GET /api/v1/locales

```json
{
  "data": [
    { "locale": "en", "native_name": "English", "direction": "ltr", "plural_categories": ["one", "other"] },
    { "locale": "zh", "native_name": "中文", "direction": "ltr", "plural_categories": ["other"] }
  ]
}
```

### 8.6 Admin: POST /api/v1/admin/ingestion/run

Request:
```json
{ "source": "openrouter" }
```
Response: `IngestionRun` with all fields.

### 8.7 Admin: POST /api/v1/admin/models/{id}/approve

Response: updated model with status: "approved".

### 8.8 Admin: POST /api/v1/admin/models/{id}/reject

Request:
```json
{ "reason": "string" }
```
Response: updated model with status: "rejected".

### 8.9 Admin: POST /api/v1/admin/taxonomy/versions

Request:
```json
{ "version": "v2", "notes": "Added agentic_workflows" }
```

### 8.10 Admin: POST /api/v1/admin/taxonomy/versions/{id}/activate

No body. Response: updated TaxonomyVersion with `is_current: true`.

### 8.11 Admin: POST /api/v1/admin/webhooks

Request:
```json
{ "url": "https://...", "events": ["model.approved"], "secret": "..." }
```

### 8.12 Rate Limit Headers (ALL responses)

```
X-RateLimit-Limit: 300
X-RateLimit-Remaining: 299
X-RateLimit-Reset: 1725974400
```

On 429:
```
Retry-After: 45
X-RateLimit-Reset: 1725974400
```

## 9. Acceptance Criteria

- [ ] All entities defined with SQLAlchemy models and Alembic migrations.
- [ ] **All DB constraints implemented**: unique constraints (R1, R2), FKs with ON DELETE (R1, R7), partial unique indexes (TaxonomyVersion.is_current, ModelHosting.is_primary), triggers (immutability).
- [ ] All business rules R1–R12 have at least one test.
- [ ] **Property-based tests** for: slug normalization, i18n fallback, **price handling (Decimal, nullable, sorting)**, status transitions, deduplication idempotency.
- [ ] **Mutation testing** on core domain modules (target >80% mutation score).
- [ ] Coverage ≥ 80% in app/taxonomy/ (branch coverage), with per-module minimums: pure 100%, repositories 85%, API 75%, ingestion parsers 70%.
- [ ] Public endpoints return only approved models and active categories.
- [ ] Admin endpoints require role admin (JWT claim or API key).
- [ ] i18n fallback works for all 5 locales + Accept-Language header.
- [ ] `locale_used` present in every translated response.
- [ ] `Content-Language` and `Vary: Accept-Language` headers on translated endpoints.
- [ ] **406 for unsupported locales** with Link headers for alternates.
- [ ] **Slug transliteration for zh** (pinyin) works.
- [ ] Pricing uses Decimal end to end; **omitted when null**.
- [ ] Ingestion is idempotent (test runs twice, no duplicates) — **DB constraints verified**.
- [ ] Partial ingestion does not roll back successful models.
- [ ] Taxonomy versioning: only one is_current (**DB enforced**).
- [ ] Seed contains ≥ 10 providers, ≥ 30 models, ≥ 17 categories, translations in 5 locales **for all entities (including Provider)**.
- [ ] **OpenAPI 3.1 schema generated and committed to forcecast/contracts** (public + admin separate specs).
- [ ] **Pact consumer-driven contracts** for: public models API, public categories API, admin ingestion API. Verified in CI.
- [ ] SQLAdmin exposes Provider, AIModel, ModelHosting, Category, IngestionRun, IngestionSource, WebhookRegistration for admin.
- [ ] All endpoints documented with curl examples, error examples, edge case examples.
- [ ] **Load test: GET /api/v1/models p95 < 200ms with 10k models** (keyset pagination, indexes, Redis cache).
- [ ] **Redis cache strategy implemented**: model list cached by (filters_hash, locale, taxonomy_version), TTL 60s, invalidated on approval/ingestion.
- [ ] **PostgreSQL FTS with tsvector + GIN index** for search across base + translations.
- [ ] Engram updated with sdd-init/forcecast-backend/taxonomy.
- [ ] Demo: GET /api/v1/models?category=coding&lang=es returns real data.

## 10. Non-Functional Requirements

Performance: list endpoint < 200 ms p95 with 10k models (with indexes, keyset pagination, Redis cache, N+1 eliminated).

Pagination: **keyset/cursor-based** mandatory for page > 10. Offset allowed only for first 10 pages.

Idempotency: ingestion endpoints safe to retry (DB constraints + advisory lock).

Observability: structured logs with run_id, source, counts, trace_id.

Security: admin endpoints behind auth + role check. Separate rate limit tiers. AuditLog on all admin mutations.

i18n: no hardcoded user-facing strings outside translation tables. API returns canonical formats (ISO 8601 UTC, decimal strings), clients format for display.

Data integrity: FKs with ON DELETE RESTRICT for Provider → AIModel, Category.parent_id, Category.taxonomy_version, ModelCategory.category_id. CASCADE for translations.

**Indexes (required for NFR):**
1. `idx_ai_model_provider_status` ON ai_model(provider_id, status) WHERE status = 'approved'
2. `idx_ai_model_modality_gin` ON ai_model USING GIN(modality)
3. `idx_ai_model_search` ON ai_model USING GIN(to_tsvector('english', slug || ' ' || display_name || ' ' || COALESCE(family, '')))
4. `idx_ai_model_search_translations` ON model_translation USING GIN(to_tsvector('simple', display_name || ' ' || COALESCE(description, '')))
5. `idx_model_category_lookup` ON model_category(category_id, taxonomy_version)
6. `idx_model_hosting_model` ON model_hosting(model_id, is_primary) WHERE is_primary = true
7. `idx_ingestion_run_source_status` ON ingestion_run(source, status)
8. `idx_webhook_delivery_pending` ON webhook_delivery(status, next_retry_at) WHERE status = 'pending'

Connection pool: 20/30 (dev/prod). **PgBouncer** in production (transaction pooling).

CDN/Edge: `Cache-Control: public, max-age=60, stale-while-revalidate=300` on public GET endpoints. Cache tags: `taxonomy:v1`, `models:approved`, `categories:active`. Purge on approval/version activation.

## 11. Test Strategy (TDD)

### Unit tests (pure, no DB) — **70% target**

| Test File | Properties / Cases |
| --- | --- |
| test_slug_normalization.py | **Property-based (hypothesis):** idempotent, deterministic, no leading/trailing hyphens, no double hyphens, only alnum+hyphen, lowercase, collision detection, Unicode NFKC, pinyin transliteration, truncation |
| test_i18n_fallback.py | **Property-based:** non-empty name for any locale, locale_used ∈ {requested, en, base}, en never falls back if exists, case-insensitive locale param, invalid locale → 406 |
| **test_price_handling.py** | **Property-based:** **Decimal precision preserved, nullable handled, sorting with None never crashes, negative price rejected, omitted when both null** |
| test_status_transitions.py | **Property-based:** valid transitions form DAG, no cycles, terminal states (approved→deprecated only), invalid always 409 |
| test_deduplication.py | **Property-based:** ingest twice == ingest once, counts add up, no duplicate slugs after ingestion |
| test_taxonomy_versioning.py | **Property-based:** only one is_current, immutability trigger fires, version activation idempotent |
| test_category_tree.py | No cycles, max depth 2 (v1), parent RESTRICT prevents orphan delete |
| test_model_hosting.py | One primary per model, **status transitions (no pricing)** |

### Integration tests (DB) — **20% target**

| Test File | Focus |
| --- | --- |
| test_provider_repository.py | CRUD, translations, slug uniqueness |
| test_aimodel_repository.py | CRUD, model_hosting relation, category assignment via ModelCategory |
| test_category_repository.py | Tree operations, versioning, translations |
| test_model_category.py | Association with taxonomy_version, FK constraints |
| test_deduplication_integration.py | Concurrent ingestion (advisory lock), upsert behavior |
| test_ingestion_idempotency.py | Full run twice, partial errors, source_payload_hash |
| test_approval_flow.py | Role auth, webhook emission, status transitions |
| test_taxonomy_versioning_integration.py | Create version, activate, immutability, ModelCategory version binding |
| test_webhook_delivery.py | Retry policy, signature verification, idempotency key, dead letter |
| test_search_integration.py | FTS across base + translations, locale filtering |

### API tests (FastAPI TestClient) — **10% target**

| Test File | Focus |
| --- | --- |
| test_api_models_list.py | Pagination (offset + cursor), filters, sorting, search, locale, error envelopes |
| test_api_models_detail.py | Categories, hostings (no prices), translations, 404 |
| test_api_categories.py | Tree, translations, taxonomy_version in meta |
| test_api_providers.py | Translations, status filter |
| test_api_locales.py | Locale metadata |
| test_api_admin_ingestion.py | Auth, rate limits, run status, webhook |
| test_api_admin_approve_reject.py | Auth, validation, webhook payload |
| test_api_admin_taxonomy_versions.py | Create, activate, immutability |
| test_api_admin_webhooks.py | CRUD, signature verification |
| test_api_rate_limits.py | Headers, tiers, 429 with Retry-After |
| test_api_error_envelope.py | 400, 401, 403, 404, 406, 409, 422, 429, 500 formats |

### Contract tests (Pact) — **Consumer-driven**

| Consumer | Contracts |
| --- | --- |
| forcecast/web | Public models list/detail, categories, providers, locales |
| forcecast/mobile | Same as web + offline cache headers |
| forcecast/mcp-server | Admin ingestion, approve/reject, taxonomy versions |
| recommendation-engine | Public models with hostings, categories |

**CI verification:** Pact broker publishes on consumer PR, provider verifies on every backend push.

### Performance tests

- Locust/k6 script: GET /api/v1/models with 10k models, 100 concurrent users, 5min duration
- Assert: p95 < 200ms, p99 < 500ms, error rate < 0.1%
- Run weekly in CI, alert on regression > 10%

### Security tests

- Bandit + safety in CI (every PR)
- API tests: auth bypass, role escalation, SQL injection attempts, XSS in search

### Migration tests

- Alembic: upgrade head → downgrade base → upgrade head, verify data integrity

## 12. Seed Data

Files under `forcecast/backend/seeds/`:

- providers.json — ≥ 10 providers
- models.json — ≥ 30 models across providers (**with reference prices from OpenRouter**)
- **model_hostings.json — ≥ 30 rows (1 per model for v1, no price fields)**
- categories.json — 17 categories, tree with parents
- translations_en.json, translations_es.json, translations_pt.json, translations_fr.json, translations_zh.json — **for ALL entities (Provider, Category, AIModel)**
- ingestion_sources.json — 3 sources (openrouter, huggingface, lmsys)

Seed command:
```bash
python -m app.db.seed --file seeds/
```
Idempotent: running twice does not duplicate.

**Validation:** Seed command fails if any entity missing translations for all 5 locales.

## 13. Open Questions (Resolved for v1)

| Question | Resolution |
| --- | --- |
| Category tree > 2 levels? | No for v1. Revisit v2. |
| Multi-provider models? | **Schema ready (ModelHosting). v1: one primary hosting per model. v2: expose multiple.** |
| Per-image/second/request pricing? | Defer. v1 only token pricing (reference). |
| Artificial Analysis / LLM Stats ingestion? | v2. Start with OpenRouter. |
| Taxonomy changes require migration script? | Yes. Each version bump ships with data migration (Alembic). |

## 14. Architecture Decisions (ADR references)

- ADR-0001: Polyrepo with contract-first OpenAPI.
- ADR-0002: FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2.
- ADR-0003: i18n via translation tables, not JSON files.
- ADR-0004: Decimal for pricing.
- ADR-0005: Taxonomy versioning as first-class entity.
- ADR-0006: Ingestion idempotent by design (DB constraints).
- ADR-0007: Public API only exposes approved models.
- ADR-0008: Keyset pagination for scalable lists.
- ADR-0009: Redis cache with cache tags for public taxonomy.
- ADR-0010: Webhook events for async model lifecycle.
- ADR-0011: ModelHosting entity for multi-provider readiness (**no pricing**).

## 15. Out of Scope (explicit)

Voting, comparison, scoring.
User accounts and auth.
Reputation.
MCP server.
Recommendation engine.
Admin custom UI.
Scheduled ingestion (cron).
Model benchmarking results storage.
**Billing, charging, or per-hosting price overrides.**

## 16. Definition of Done

A sprint is done when:

- Spec is approved and versioned.
- All acceptance criteria checked.
- Coverage ≥ 80% in app/taxonomy/ (branch).
- OpenAPI schema committed to forcecast/contracts (public + admin).
- Pact contracts verified in CI.
- Seed data loaded and verified (100% translation coverage).
- SQLAdmin accessible for admins.
- Load test passes p95 < 200ms @ 10k models.
- Engram updated with sdd-init/forcecast-backend/taxonomy.
- Demo: GET /api/v1/models?category=coding&lang=es returns real data.

---

**End of spec v1.2.0 — Ready for `sdd-propose` / `sdd-design`**