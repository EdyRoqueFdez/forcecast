# Forcecast Backend

FastAPI backend for Forcecast — User opinions platform for AI agent model selection.

## Stack

- **FastAPI** — Modern, fast web framework
- **SQLAlchemy 2.0** — Async ORM
- **Alembic** — Database migrations
- **Pydantic v2** — Data validation
- **PostgreSQL** — Primary database (GIN indexes, advisory locks, triggers)
- **Redis** — Caching & sessions (TTL 60s, in-memory fallback)
- **structlog** — Structured logging
- **Locust** — Load testing (100 concurrent users)

## Development

```bash
# Install dependencies
pip install -e ".[dev,full,taxonomy]"

# Run development server
uvicorn app.main:app --reload

# Run tests
pytest
pytest app/tests/taxonomy/ -v          # taxonomy domain only
pytest app/tests/taxonomy/performance -v  # performance gate
pytest app/tests/taxonomy/contract -v     # contract tests

# Lint & format
ruff check app/taxonomy
ruff format .
mypy app/taxonomy

# Generate OpenAPI contracts
python -m scripts.generate_contracts

# Load test — 100 users, 5 min, 10k models, p95 < 200ms
locust -f bench/load_test.py --headless -u 100 -r 10 -t 300s --host http://localhost:8000
python -m bench.load_test --gate --models 10000 --requests 1000 --p95-threshold 200
python -m bench.load_test --seed --count 10000
```

## Environment

Copy `.env.example` to `.env` and configure:

```env
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/forcecast
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key
TURNSTILE_SECRET_KEY=your-turnstile-secret
RESEND_API_KEY=your-resend-key
SENTRY_DSN=your-sentry-dsn
```

## Taxonomy Domain

Canonical AI taxonomy — foundational vocabulary for all Forcecast domains (voting, recommendations, MCP). Every opinion and comparison references entities defined here.

### Architecture

Layered hexagonal: `models → repositories → services → api` with FastAPI `Depends`.

- **14 entities**: Provider, AIModel (+translations), ModelHosting, Category (+translations), ModelCategory, TaxonomyVersion, IngestionRun/Source, WebhookRegistration/Delivery, LocaleMeta
- **DB-enforced constraints**: partial unique indexes, CHECK, triggers for immutability, Advisory locks for ingestion concurrency
- **Public API** (`/api/v1`): 5 GET endpoints — models (keyset pagination), model detail, categories, providers, locales. Envelope `{data, meta, links}`; price fields omitted when null; hostings show provider+is_primary only. Cache-Control `public, max-age=60, stale-while-revalidate=300`.
- **Admin API** (`/api/v1/admin`): 7 POST endpoints — ingest, approve/reject/deprecate, version create/activate, webhooks. Auth via JWT `role:admin` or `fk_admin_*` API key. Rate limits 60/300/1000 with `X-RateLimit-*` + `Retry-After`.
- **Ingestion**: 3 parsers (OpenRouter, HuggingFace, LMSYS), batched upsert (500), advisory lock `pg_advisory_xact_lock`, run tracking.
- **Webhooks**: HMAC-SHA256 signing, envelope `{id, type, timestamp, taxonomy_version, data}`, retry `1m/5m/15m/1h/6h` → dead_letter after 5.
- **Seed**: `python -m app.db.seed` — idempotent, validates 5-locale completeness; ≥10 providers, ≥30 models, 17 categories, 30 hostings (no prices).
- **Pricing**: reference-only on `AIModel` (Decimal nullable, omitted when null, nulls last on sort). No per-hosting overrides — comparison platform, not marketplace.

### Database

```bash
alembic upgrade head          # 002_taxonomy_initial — 14 tables, 8 indexes, 3 triggers
alembic downgrade base        # rollback taxonomy
python -m app.db.seed --validate-only
python -m app.db.seed
```

### Performance

- Target: `p95 < 200ms` at 10k models, `p99 < 500ms`, error <0.1% — keyset pagination + GIN + Redis
- Indexes: `idx_ai_model_provider_status`, `idx_ai_model_modality_gin`, `idx_ai_model_search` (GIN tsvector), `idx_model_category_lookup`, `idx_model_hosting_model` (partial), `idx_ingestion_run_source_status`, `idx_webhook_delivery_pending` (partial)
- Pool 20/30 + PgBouncer (prod)

### Contracts

Separate OpenAPI 3.1 specs — committed to `forcecast/contracts/`:

- `taxonomy-public.yaml` — 5 public endpoints
- `taxonomy-admin.yaml` — 7 admin endpoints

Generated via `scripts/generate_contracts.py` from live FastAPI routers; validated with `openapi-spec-validator` and schemathesis. CI contract tests in `app/tests/taxonomy/contract/`.

### i18n

5 locales: `en, es, pt, fr, zh`. Translation tables + fallback `requested → en → first`. `406` with `Link` alternates, `Content-Language` + `Vary` headers. No hardcoded strings; ISO 8601 UTC.

## API Docs

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc
- OpenAPI JSON: http://localhost:8000/api/v1/openapi.json
- Contracts: `forcecast/contracts/taxonomy-public.yaml`, `taxonomy-admin.yaml`
