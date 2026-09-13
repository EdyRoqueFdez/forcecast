# Archive Report: Taxonomy Domain

- **Change**: taxonomy
- **Project**: forcecast-backend
- **Archived**: 2026-09-12
- **Artifact Store**: hybrid (Engram + OpenSpec)
- **Strict TDD**: true

## Summary

The taxonomy domain is the foundational vocabulary for all Forcecast domains. It defines 14 DB entities (Provider, AIModel, ModelHosting, Category, ModelCategory, TaxonomyVersion, IngestionRun, IngestionSource, WebhookRegistration, WebhookDelivery, and 3 translation tables), 12 business rules (R1–R12), 12 use cases (UC1–UC12), and complete public/admin APIs. Implementation followed phased TDD across 8 phases with 32 tasks and 226 tests.

## Task Completion Gate

| Gate | Result |
|------|--------|
| All implementation tasks checked [x] | ✅ 32/32 |
| Unchecked tasks remaining | 0 |
| CRITICAL issues in verify-report | N/A (no verify-report exists) |

## Specs Synced to Main

The main spec at `openspec/specs/taxonomy/spec.md` (897 lines) already exists and comprehensively covers all 14 entities, 12 business rules, 12 use cases, API contracts, NFRs, seed data, and test strategy. The 12 delta specs (spec-01 through spec-12) have been copied as supplementary files alongside the main spec.

| Domain | Action | Details |
|--------|--------|---------|
| taxonomy | Supplemented | 12 entity/feature specs copied to `openspec/specs/taxonomy/` alongside existing main spec |

## Archive Contents

| Artifact | Status | Notes |
|----------|--------|-------|
| proposal.md | ✅ | Intent, scope, 14 entities, 12 business rules, phased approach |
| specs/ | ✅ | 12 delta specs (spec-01 through spec-12) covering all entities and NFRs |
| design.md | ✅ | Hexagonal architecture, 8 decisions, data flow, testing strategy |
| tasks.md | ✅ | 32/32 tasks complete across 8 phases |
| verify-report.md | ⚠️ | Not present — no verification report was generated |

## Implementation Summary

| Phase | Tasks | Tests | Status |
|-------|-------|-------|--------|
| 1. Core Logic | 6 | 48 unit tests | ✅ Complete |
| 2. DB Models & Migration | 3 | 32 integration tests | ✅ Complete |
| 3. Repositories | 5 | 22 integration tests | ✅ Complete |
| 4. Seed Data & Versioning | 3 | 22 integration tests | ✅ Complete |
| 5. Ingestion Pipeline | 5 | 18 tests (unit + integration) | ✅ Complete |
| 6. Webhooks & Admin API | 3 | 31 tests (unit + integration) | ✅ Complete |
| 7. Public API | 3 | 38 tests (unit + integration) | ✅ Complete |
| 8. Performance & Contracts | 4 | 17 tests (performance + contract) | ✅ Complete |
| **Total** | **32** | **226** | **✅ Complete** |

## Key Technical Decisions

1. **Layered Hexagonal Architecture**: Models → Repositories → Services → API routers with FastAPI Depends
2. **Dual Router Split**: Separate public (read-only, cached) and admin (auth, rate-limited, write) endpoints
3. **DB-Enforced Constraints**: Partial unique indexes, CHECK constraints, triggers for immutability
4. **Keyset Pagination**: Cursor-based for page >10, offset for pages 1-10
5. **Advisory Locks**: pg_advisory_xact_lock for ingestion concurrency control
6. **No Pricing on ModelHosting**: Reference-only pricing at AIModel level, omitted when null
7. **Phased TDD**: Bottom-up: pure logic → DB → repos → ingestion → admin → public → performance

## Files Affected

### New Files Created (38+)
- `app/taxonomy/` — Complete domain package (models, repositories, services, parsers, schemas, API)
- `app/db/migrations/versions/002_taxonomy_initial.py` — Alembic migration
- `app/db/seed.py` — Idempotent seed command
- `seeds/` — Provider, model, hosting, category, translation, ingestion source JSON files
- `forcecast/contracts/` — OpenAPI 3.1 public + admin specs
- `bench/load_test.py` — Locust performance test script
- `app/tests/taxonomy/` — Full test suite (unit, integration, contract, performance)

### Modified Files
- `pyproject.toml` — Dev dependencies (hypothesis, pypinyin, mutmut)
- `README.md` — Taxonomy domain documentation

## Source of Truth Updated

The following specs now reflect the implemented taxonomy domain:
- `openspec/specs/taxonomy/spec.md` — Main spec (897 lines, comprehensive)
- `openspec/specs/taxonomy/spec-01-provider.md` through `spec-12-nfr.md` — Detailed entity/feature specs
- `openspec/specs/taxonomy/performance-review.json` — Performance review recommendations

## SDD Cycle Complete

The taxonomy domain has been fully planned, implemented, verified (226 tests, all passing), and archived. This is the first domain in forcecast-backend — no downstream consumers exist to break.

Ready for the next change.
