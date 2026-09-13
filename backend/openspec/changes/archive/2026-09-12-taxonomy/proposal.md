# Proposal: Taxonomy

## Intent

Implement the canonical AI taxonomy — the foundational vocabulary for all Forcecast domains (voting, recommendations, MCP). Every opinion, comparison, and recommendation will reference entities defined here. Without a stable, versioned, internationalized taxonomy, no downstream domain can operate.

**Pricing clarification (v1.2.0):** Forcecast is a comparison/voting platform, not a marketplace. Prices are **reference information only** (cost per 1M tokens from OpenRouter). No billing, no per-hosting price overrides, no `price_unknown` flag.

## Scope

### In Scope
- 14 DB entities: Provider, AIModel, ModelHosting, Category, ModelCategory, CategoryTranslation, ModelTranslation, ProviderTranslation, TaxonomyVersion, IngestionRun, IngestionSource, WebhookRegistration, WebhookDelivery, LocaleMeta
- 12 business rules (R1–R12): uniqueness, deduplication, slug normalization, status state machine, i18n fallback, reference pricing (no overrides), taxonomy versioning, approval workflow, ingestion, public/admin split, rate limiting, webhooks
- 12 use cases (UC1–UC12): public read API (5 endpoints) + admin write API (7 endpoints)
- Standardized response/error envelope, rate limit headers
- Seed data: ≥10 providers, ≥30 models, ≥17 categories, translations in 5 locales
- ModelHosting seed: `model_hostings.json` — ≥30 rows, **no price fields**
- OpenAPI 3.1 schema (public + admin separate specs)
- Property-based tests, integration tests, API tests, contract tests, performance tests

### Out of Scope
- User authentication (Sprint 1 — JWT/API key placeholders only)
- Voting, comparisons, scoring
- MCP server, recommendation engine, admin custom UI
- Automated scheduled ingestion (cron)
- Model benchmarking results
- **Billing, charging, or per-hosting price overrides**

## Capabilities

### New Capabilities
- `taxonomy-core`: Provider, AIModel, ModelHosting (no pricing fields), Category, ModelCategory entities with DB constraints, slug normalization, status state machine
- `taxonomy-i18n`: Translation tables (CategoryTranslation, ModelTranslation, ProviderTranslation), i18n fallback, locale negotiation, 406 handling
- `taxonomy-versioning`: TaxonomyVersion, immutability triggers, category tree versioning
- `taxonomy-ingestion`: IngestionRun, IngestionSource, OpenRouter/HuggingFace/LMSYS parsers, idempotent upsert, advisory locks
- `taxonomy-admin`: Approval workflow, webhook registration/delivery, admin API auth + rate limiting
- `taxonomy-public`: Public read API (hostings array shows provider + primary flag only, no prices), Redis caching, FTS with GIN indexes, keyset pagination

### Modified Capabilities
- None — this is the first domain

## Approach

Phased TDD, bottom-up: pure logic → DB models → repositories → ingestion → admin API → public API → performance. Each phase writes tests first (RED), implements (GREEN), refactors. DB constraints (partial unique indexes, triggers) verified at integration test level.

| Phase | Deliverables | ~Lines |
|-------|-------------|--------|
| 1. Pure logic | Slug normalization (R3), status state machine (R4), i18n fallback (R5), reference pricing (R6: Decimal, nullable, sorting with None, omitted when null) | 300 |
| 2. DB models | 14 SQLAlchemy models, Alembic migration, 8 required indexes | 500 |
| 3. Repositories | CRUD for all entities, translation upsert, category tree ops | 400 |
| 4. Seed + Versioning | TaxonomyVersion lifecycle, seed command, 5-locale translations, `model_hostings.json` (no prices) | 200 |
| 5. Ingestion | 3 parsers, idempotent upsert, advisory lock, IngestionRun tracking | 400 |
| 6. Admin API | Approve/reject, webhook CRUD, auth middleware, rate limiting | 350 |
| 7. Public API | 5 endpoints, keyset pagination, FTS, response envelope (prices omitted when null, hostings without prices) | 400 |
| 8. Performance | Redis cache, CDN headers, load test script | 200 |

**400-line budget risk: HIGH** — domain exceeds single PR. Chained PRs required per phase.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `app/taxonomy/` | New | All domain modules (models, repositories, services, API) |
| `app/taxonomy/models/` | New | 14 SQLAlchemy entity definitions (ModelHosting: no price fields) |
| `app/taxonomy/repositories/` | New | Data access layer with DB constraint enforcement |
| `app/taxonomy/services/` | New | Business logic: slug normalization, status FSM, i18n, ingestion |
| `app/taxonomy/api/` | New | FastAPI routers: public + admin |
| `app/taxonomy/schemas/` | New | Pydantic v2 request/response models (price fields nullable, omitted when null) |
| `app/db/migrations/versions/` | New | Alembic migration with indexes, triggers, constraints |
| `seeds/` | New | Provider, model, category, translation seed data |
| `seeds/model_hostings.json` | New | ≥30 rows, no price fields |
| `forcecast/contracts/` | New | OpenAPI 3.1 schemas (public + admin) |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Multi-provider ModelHosting complexity | Medium | v1: one primary per model. Schema ready for v2 multi-hosting. No pricing on hostings. |
| Ingestion idempotency across sources | Medium | DB constraints + advisory locks + upsert. Property-based tests. |
| Taxonomy versioning immutability triggers | Low | PostgreSQL triggers verified at integration test level. |
| 10k model performance at p95 < 200ms | Medium | Keyset pagination + GIN indexes + Redis cache + load testing. |
| 5-locale translation completeness | Low | Seed validation enforces 100% locale coverage per entity. |

## Rollback Plan

1. Drop all `app/taxonomy/` modules (no external consumers yet)
2. `alembic downgrade base` — removes all tables, triggers, indexes
3. Remove `seeds/` and `forcecast/contracts/taxonomy*`
4. No downstream domains exist to break — this is the first domain

## Dependencies

None — this is the first domain in forcecast-backend.

## Success Criteria

- [ ] All 14 entities implemented with DB constraints matching spec exactly
- [ ] All 12 business rules (R1–R12) have at least one test
- [ ] Property-based tests: slug normalization, i18n fallback, status transitions, deduplication, price handling (Decimal, nullable, sorting with None, omitted when null)
- [ ] Coverage ≥ 80% in `app/taxonomy/` (branch)
- [ ] OpenAPI 3.1 schemas committed to `forcecast/contracts/`
- [ ] Seed data: ≥10 providers, ≥30 models, ≥17 categories, 5-locale translations
- [ ] `model_hostings.json` seed contains ≥30 rows with no price fields
- [ ] `GET /api/v1/models?category=coding&lang=es` returns real translated data
- [ ] API response omits price fields when both are null (no `price_unknown` flag)
- [ ] Load test: p95 < 200ms with 10k models
