# Non-Functional Requirements Specification

## Purpose

Define non-functional requirements for the taxonomy domain: performance targets, pagination strategy, idempotency, observability, security, i18n constraints, data integrity, indexing, connection pooling, CDN caching, and pricing data integrity.

## Requirements

### Requirement: Performance Target

The system SHALL serve GET /api/v1/models at p95 < 200ms with 10,000 models using keyset pagination, GIN indexes, and Redis cache. N+1 queries are prohibited.

#### Scenario: Load Test Pass

- GIVEN 10,000 approved models with translations and categories
- WHEN 100 concurrent users request GET /api/v1/models for 5 minutes
- THEN p95 latency < 200ms, p99 < 500ms, error rate < 0.1%

### Requirement: Keyset Pagination

The system SHALL use keyset/cursor-based pagination for page > 10. Offset pagination is allowed only for the first 10 pages. Cursor is an opaque base64 token.

#### Scenario: Cursor Pagination Beyond Page 10

- GIVEN 500 models, requesting page 11
- WHEN using offset pagination
- THEN the system returns 422 suggesting cursor-based pagination

#### Scenario: Cursor Pagination Works

- GIVEN 500 models
- WHEN requesting with cursor=<opaque> and limit=20
- THEN the next 20 models are returned with a new cursor

### Requirement: Idempotency

The system SHALL make ingestion endpoints safe to retry via DB constraints (unique indexes) and advisory locks. Duplicate ingestion runs produce no duplicate data.

#### Scenario: Retry Safe

- GIVEN an ingestion run completed successfully
- WHEN retrying the same ingestion
- THEN no duplicate models are created

### Requirement: Observability

The system SHALL emit structured logs with run_id, source, models_found, models_created, models_updated, models_skipped, trace_id for every ingestion run. Admin mutations are logged to AuditLog.

#### Scenario: Ingestion Log

- GIVEN an ingestion run processes 50 models
- WHEN the run completes
- THEN structured log contains run_id, source, counts, and trace_id

### Requirement: Security

The system SHALL protect admin endpoints with auth + role check. Rate limits are scoped per IP (anonymous) or per user (authenticated). All admin mutations create AuditLog entries.

#### Scenario: Rate Limit Scope

- GIVEN user A makes 300 requests/min and user B makes 300 requests/min
- WHEN both are authenticated
- THEN both are within their individual limits (not shared)

### Requirement: i18n Constraints

The system SHALL have no hardcoded user-facing strings outside translation tables. API responses use canonical formats (ISO 8601 UTC, decimal strings). Clients format for display. Content-Language and Vary headers on translated endpoints. 406 for unsupported locales with Link headers for alternates.

#### Scenario: Unsupported Locale

- GIVEN a request with lang=de (not supported)
- WHEN the server processes the request
- THEN the system returns 406 with {supported: ['en','es','pt','fr','zh']} and Link headers

### Requirement: Data Integrity

The system SHALL enforce FK constraints: ON DELETE RESTRICT for Provider→AIModel, Category.parent_id, Category.taxonomy_version, ModelCategory.category_id. ON DELETE CASCADE for translations (CategoryTranslation, ModelTranslation, ProviderTranslation) and ModelCategory→AIModel.

#### Scenario: RESTRICT Prevents Orphan

- GIVEN a Provider with associated AIModels
- WHEN attempting to delete the Provider
- THEN the system returns 409 (ON DELETE RESTRICT)

### Requirement: Pricing Data Integrity

The system SHALL store pricing as Decimal (never float), nullable. API responses omit price fields when both are null (no `price_unknown` flag). Price fields are reference-only (cost per 1M tokens from OpenRouter). No per-hosting price overrides.

#### Scenario: Decimal Precision

- GIVEN a model with input_price_per_mtok=0.000001
- WHEN stored and retrieved
- THEN the value is exactly 0.000001 (no floating-point rounding)

#### Scenario: Nullable Pricing

- GIVEN a model with both price fields null
- WHEN the public API returns the model
- THEN input_price_per_mtok and output_price_per_mtok are omitted from response

#### Scenario: Sorting with Null Prices

- GIVEN models with mixed null and non-null prices
- WHEN sorting by input_price ascending
- THEN null prices appear at the end (or beginning) without crashing

### Requirement: Database Indexes

The system SHALL create 8 required indexes: idx_ai_model_provider_status, idx_ai_model_modality_gin, idx_ai_model_search (GIN tsvector), idx_ai_model_search_translations (GIN tsvector), idx_model_category_lookup, idx_model_hosting_model (partial), idx_ingestion_run_source_status, idx_webhook_delivery_pending (partial).

#### Scenario: FTS Index Used

- GIVEN models with tsvector search index
- WHEN querying with search="claude"
- THEN PostgreSQL uses the GIN index for the text search

### Requirement: Connection Pooling

The system SHALL use connection pool 20/30 (dev/prod). Production uses PgBouncer with transaction pooling.

#### Scenario: Pool Configuration

- GIVEN production environment
- WHEN the application starts
- THEN connection pool is configured with max 30 connections

### Requirement: CDN Caching

The system SHALL set Cache-Control headers on public GET endpoints: `public, max-age=60, stale-while-revalidate=300`. Cache tags: `taxonomy:v1`, `models:approved`, `categories:active`. Cache purge on approval/version activation.

#### Scenario: Cache Headers Present

- GIVEN a public GET /api/v1/models request
- WHEN the response is returned
- THEN headers include Cache-Control: public, max-age=60, stale-while-revalidate=300

#### Scenario: Cache Purge on Approval

- GIVEN a cached model list
- WHEN a new model is approved
- THEN the cache is purged and next request fetches fresh data