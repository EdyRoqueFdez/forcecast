# Design: Taxonomy

## Technical Approach

Phased TDD implementation following the proposal's bottom-up phases: pure logic → DB models → repositories → seed/versioning → ingestion → admin API → public API → performance. Each phase writes tests first (RED), implements (GREEN), refactors. The domain uses FastAPI hexagonal architecture with SQLAlchemy 2.0 async ORM, PostgreSQL for constraints/triggers, Redis for caching, and Pydantic v2 for request/response validation. OpenAPI 3.1 schemas are generated separately for public and admin surfaces.

## Architecture Decisions

### Decision: Layered Hexagonal Architecture

**Choice**: Models → Repositories → Services → API routers, with dependency injection via FastAPI `Depends`.

**Alternatives considered**: Monolithic services, anemic domain models with service layer only.

**Rationale**: Matches existing `app/` structure (`models/`, `repositories/`, `services/`, `api/`). Enables unit testing of pure logic (slug, FSM, i18n) without DB. Repositories encapsulate SQLAlchemy queries; services orchestrate business rules; API layer handles HTTP concerns only.

### Decision: Dual Router Split (Public vs Admin)

**Choice**: Two FastAPI routers under `/api/v1` and `/api/v1/admin` with separate OpenAPI specs.

**Alternatives considered**: Single router with role-based endpoint guards.

**Rationale**: Spec requires separate OpenAPI 3.1 schemas (`forcecast/contracts/taxonomy-public.yaml`, `taxonomy-admin.yaml`). Public API is read-only with caching; admin API requires auth, rate limiting, and write operations. Clean separation avoids leaking admin endpoints in public docs.

### Decision: DB-Enforced Constraints Over Application Logic

**Choice**: Partial unique indexes, CHECK constraints, triggers for immutability, ON DELETE RESTRICT/CASCADE.

**Alternatives considered**: Application-level validation only.

**Rationale**: Spec mandates DB-level deduplication (R2), primary hosting uniqueness (R3), single current version (R6), historical immutability (R6). PostgreSQL constraints are the only way to guarantee these under concurrent ingestion/admin operations. Triggers enforce immutability of non-current taxonomy versions.

### Decision: Keyset Pagination with Offset Fallback (First 10 Pages)

**Choice**: Cursor-based pagination using opaque base64 tokens; offset allowed only for pages 1-10.

**Alternatives considered**: Pure offset, pure keyset.

**Rationale**: Spec NFR requires keyset for performance at 10k models. First 10 pages use offset for simpler client UX (direct page jumps). Cursor encodes `(sort_field, sort_value, id)` for stable ordering.

### Decision: Advisory Locks for Ingestion Concurrency

**Choice**: `pg_advisory_xact_lock(source_code_hash)` per ingestion run.

**Alternatives considered**: Row-level locks, application-level mutex.

**Rationale**: Spec requires blocking concurrent runs for same source (R7) while allowing different sources in parallel. Advisory locks are lightweight, transaction-scoped, and don't require a lock table. Hash of source code (e.g., "openrouter") as lock key.

### Decision: No Pricing on ModelHosting

**Choice**: ModelHosting entity has zero price fields. Pricing lives only on AIModel as nullable Decimal reference values.

**Alternatives considered**: Per-hosting price overrides (input_price_override, output_price_override).

**Rationale**: Spec explicitly states Forcecast is a comparison platform, not a marketplace (spec-03, spec-11, spec-12). Price fields are reference-only at AIModel level and omitted from API when null. Adding hosting-level prices would complicate the data model and contradict the platform positioning.

## Data Flow

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
│  Ingestion  │────▶│  Parser      │────▶│  Repository │────▶│  PostgreSQL  │
│  Scheduler  │     │  (3 sources) │     │  (upsert)   │     │  (constraints)│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────────┘
                           │                    │                    │
                           ▼                    ▼                    ▼
                    ┌──────────────┐     ┌─────────────┐     ┌──────────────┐
                    │ IngestionRun │     │  Webhook    │     │   Redis      │
                    │  (tracking)  │     │  Dispatcher │     │  (cache)     │
                    └──────────────┘     └─────────────┘     └──────────────┘

┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Public    │────▶│   Service    │────▶│  Repository │
│   API       │     │  (i18n, FTS) │     │  (cached)   │
└─────────────┘     └──────────────┘     └─────────────┘
                           │                    │
                           ▼                    ▼
                    ┌──────────────┐     ┌──────────────┐
                    │  Locale      │     │  PostgreSQL  │
                    │  Negotiation │     │  (GIN idx)   │
                    └──────────────┘     └──────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `app/taxonomy/__init__.py` | Create | Domain package init |
| `app/taxonomy/models/__init__.py` | Create | Models package |
| `app/taxonomy/models/entities.py` | Create | 14 SQLAlchemy models with constraints |
| `app/taxonomy/models/enums.py` | Create | Enum definitions (status, modality, locale, source) |
| `app/taxonomy/repositories/__init__.py` | Create | Repositories package |
| `app/taxonomy/repositories/provider.py` | Create | Provider CRUD + translation upsert |
| `app/taxonomy/repositories/ai_model.py` | Create | AIModel CRUD + deduplication upsert |
| `app/taxonomy/repositories/model_hosting.py` | Create | ModelHosting CRUD + primary constraint (NO price fields) |
| `app/taxonomy/repositories/category.py` | Create | Category tree ops + translation |
| `app/taxonomy/repositories/taxonomy_version.py` | Create | Version lifecycle + immutability checks |
| `app/taxonomy/repositories/ingestion.py` | Create | IngestionRun/Source CRUD + advisory lock |
| `app/taxonomy/repositories/webhook.py` | Create | WebhookRegistration/Delivery CRUD |
| `app/taxonomy/services/__init__.py` | Create | Services package |
| `app/taxonomy/services/core.py` | Create | Slug normalize, status FSM, i18n fallback, **nullable price handling** |
| `app/taxonomy/services/ingestion.py` | Create | Parser orchestration, batched upsert, run tracking |
| `app/taxonomy/services/parsers/__init__.py` | Create | Parser package |
| `app/taxonomy/services/parsers/openrouter.py` | Create | OpenRouter API parser |
| `app/taxonomy/services/parsers/huggingface.py` | Create | HuggingFace Hub parser |
| `app/taxonomy/services/parsers/lmsys.py` | Create | LMSYS Chatbot Arena parser |
| `app/taxonomy/services/webhooks.py` | Create | HMAC signing, delivery creation, retry scheduler |
| `app/taxonomy/schemas/__init__.py` | Create | Schemas package |
| `app/taxonomy/schemas/public.py` | Create | Public API request/response models (nullable prices omitted when null) |
| `app/taxonomy/schemas/admin.py` | Create | Admin API request/response models |
| `app/taxonomy/api/__init__.py` | Create | API package |
| `app/taxonomy/api/public.py` | Create | 5 public GET endpoints |
| `app/taxonomy/api/admin.py` | Create | 7 admin write endpoints |
| `app/taxonomy/api/dependencies.py` | Create | Auth, rate limit, locale negotiation deps |
| `alembic/versions/xxxx_taxonomy_initial.py` | Create | Migration with 14 tables, 8 indexes, 3 triggers |
| `seeds/providers.json` | Create | ≥10 providers |
| `seeds/models.json` | Create | ≥30 models across providers with reference prices |
| `seeds/model_hostings.json` | Create | ≥30 hostings (1 per model for v1, **no price fields**) |
| `seeds/categories.json` | Create | 17 categories (tree, max depth 2) |
| `seeds/translations/*.json` | Create | 5-locale translations for all entities |
| `seeds/ingestion_sources.json` | Create | 3 sources (openrouter, huggingface, lmsys) |
| `app/db/seed.py` | Create | Idempotent seed command with translation validation |
| `forcecast/contracts/taxonomy-public.yaml` | Create | OpenAPI 3.1 public spec |
| `forcecast/contracts/taxonomy-admin.yaml` | Create | OpenAPI 3.1 admin spec |
| `app/tests/taxonomy/` | Create | Test suite (unit, integration, property, contract) |

## Interfaces / Contracts

### Core Enums (SQLAlchemy + Pydantic)

```python
# app/taxonomy/models/enums.py
class ProviderStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BANNED = "banned"

class ModelStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"

class ModelModality(str, Enum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"
    CODE = "code"
    EMBEDDING = "embedding"
    REASONING = "reasoning"

class ModelSource(str, Enum):
    OPENROUTER = "openrouter"
    HUGGINGFACE = "huggingface"
    LMSYS = "lmsys"
    MANUAL = "manual"

class Locale(str, Enum):
    EN = "en"
    ES = "es"
    PT = "pt"
    FR = "fr"
    ZH = "zh"

class WebhookEvent(str, Enum):
    MODEL_APPROVED = "model.approved"
    MODEL_REJECTED = "model.rejected"
    MODEL_DEPRECATED = "model.deprecated"
    INGESTION_COMPLETED = "ingestion.completed"
    TAXONOMY_VERSION_ACTIVATED = "taxonomy.version_activated"
```

### Public API Response Envelope

```python
# app/taxonomy/schemas/public.py
class Meta(BaseModel):
    page: int
    limit: int
    total: int
    has_more: bool
    next_cursor: str | None = None
    taxonomy_version: str | None = None

class Links(BaseModel):
    first: str
    prev: str | None = None
    next: str | None = None
    last: str | None = None

class PaginatedResponse(BaseModel, Generic[T]):
    data: list[T]
    meta: Meta
    links: Links

class ErrorDetail(BaseModel):
    field: str
    issue: str

class ErrorResponse(BaseModel):
    error: ErrorEnvelope

class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    trace_id: str
```

### Model Detail Response (Nullable Prices Omitted When Null)

```python
# app/taxonomy/schemas/public.py
class ModelHostingResponse(BaseModel):
    provider: ProviderSummary
    is_primary: bool
    # NO price fields

class ModelDetailResponse(BaseModel):
    id: UUID
    slug: str
    display_name: str
    version: str | None = None
    family: str | None = None
    modality: list[ModelModality]
    context_window: int | None = None
    max_output_tokens: int | None = None
    # Price fields included ONLY when non-null (spec-08, spec-12)
    input_price_per_mtok: Decimal | None = None  # omitted in JSON when null
    output_price_per_mtok: Decimal | None = None  # omitted in JSON when null
    release_date: date | None = None
    deprecation_date: date | None = None
    status: ModelStatus
    source: ModelSource
    source_url: HttpUrl | None = None
    categories: list[CategorySummary]
    hostings: list[ModelHostingResponse]
    locale_used: Locale
```

### Admin API Auth Dependency

```python
# app/taxonomy/api/dependencies.py
async def require_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    # Validate JWT role:admin OR API key prefix fk_admin_*
    # Return User with role claim
    ...

class RateLimiter:
    async def __call__(
        self,
        request: Request,
        user: User | None = Depends(optional_user),
    ) -> None:
        # Scope: IP (anon) or user_id (auth)
        # Limits: anon 60/min, auth 300/min, admin 1000/min
        # Headers: X-RateLimit-Limit, Remaining, Reset
        # 429 with Retry-After
        ...
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit (pure logic) | Slug normalization (R3), status FSM (R4), i18n fallback (R5), **nullable price handling**, deduplication keys | Property-based tests (hypothesis) for slug/FSM/i18n; parametrized for price handling |
| Unit (services) | Ingestion parser transforms, webhook payload signing, retry schedule calc | Mock external HTTP; assert output shapes |
| Integration (DB) | All 14 entities CRUD, FK constraints (RESTRICT/CASCADE), partial unique indexes, triggers (immutability), advisory lock contention | Real PostgreSQL testcontainers; verify constraint violations raise 409 |
| Integration (API) | Public 5 endpoints + admin 7 endpoints, auth/rate limit, locale negotiation (406), pagination, FTS, **price field omission when null** | FastAPI TestClient + real DB; contract tests vs OpenAPI schemas |
| Contract | Public/admin OpenAPI specs match implemented routes | `schemathesis` or `pytest-openapi` against generated YAML |
| Performance | p95 < 200ms at 10k models, keyset pagination, cache hit/miss | Locust script in `bench/load_test.py`; CI gate on p95 |
| Mutation | Core logic (slug, FSM, i18n, **price handling**) survives mutants | `mutmut` on `app/taxonomy/services/core.py` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary in this design.

## Migration / Rollout

1. **Alembic migration** creates all 14 tables, 8 indexes, 3 triggers (immutability), partial unique indexes, FK constraints in single transaction.
2. **Seed command** (`python -m app.db.seed`) loads JSON files, validates 5-locale translation completeness, uses upsert (idempotent).
3. **Feature flag**: None required — taxonomy is first domain, no downstream consumers.
4. **Rollback**: `alembic downgrade base` drops all taxonomy tables/triggers/indexes; remove `app/taxonomy/`, `seeds/`, `forcecast/contracts/taxonomy*`.

## Open Questions

- [ ] Parser base URLs and auth for OpenRouter/HuggingFace/LMSYS — need API keys in `.env` (spec has placeholder fields in `IngestionSource`)
- [ ] Webhook retry scheduler: run as background task in same process (APScheduler) or separate worker? Proposal implies same process for v1.
- [ ] `LocaleMeta` entity fields (plural_categories) — need CLDR data for 5 locales; confirm exact values.
- [ ] OpenAPI spec generation: use `fastapi.openapi()` at runtime or generate static YAML during build? Proposal says "committed to contracts/".

## Summary

- **Approach**: Phased TDD, hexagonal layers, DB-enforced constraints, dual router split, keyset pagination, advisory locks for ingestion, **no pricing on ModelHosting**.
- **Key Decisions**: 8 documented (architecture, router split, DB constraints, pagination, advisory locks, cache keys, webhook signing, seed validation, **no hosting pricing**).
- **Files Affected**: 38 new files (models, repositories, services, parsers, schemas, API, migration, seeds, contracts, tests).
- **Testing Strategy**: Property-based (5 core rules), integration (DB constraints/triggers), contract (OpenAPI), performance (load test), mutation (core logic).
- **Next Step**: Ready for tasks (sdd-tasks).