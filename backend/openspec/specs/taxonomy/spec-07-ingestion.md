# Ingestion Specification

## Purpose

Define the ingestion system — importing AI models from external sources (OpenRouter, HuggingFace, LMSYS). Each source has a parser. Ingestion is idempotent (DB constraints + upsert), uses advisory locks to prevent concurrent runs, and tracks every run via IngestionRun.

## Requirements

### Requirement: IngestionRun Entity

The system SHALL persist IngestionRun entities with fields: id (UUID PK), source (FK → IngestionSource.code, ON DELETE RESTRICT), started_at (auto), finished_at (nullable), status (enum: running, success, partial, failed), models_found (int, default 0), models_created (int, default 0), models_updated (int, default 0), models_skipped (int, default 0), errors (JSONB, nullable, schema: [{model_slug, error, field?}]).

#### Scenario: Run Tracks Progress

- GIVEN an ingestion run is triggered for source "openrouter"
- WHEN the run processes 50 models (30 new, 15 updated, 5 skipped)
- THEN IngestionRun shows models_found=50, models_created=30, models_updated=15, models_skipped=5

#### Scenario: Partial Failure

- GIVEN an ingestion run processes 50 models where 2 fail validation
- WHEN the run completes
- THEN status is "partial" (not "failed")
- AND errors JSONB contains the 2 failure records
- AND the 48 successful models are persisted

### Requirement: IngestionSource Entity

The system SHALL persist IngestionSource entities with fields: code (str PK: openrouter, huggingface, lmsys), name (str, required), parser_class (str, required), rate_limit_rpm (int, default 60), base_url (URL, nullable).

#### Scenario: Source Lookup

- GIVEN IngestionSource with code="openrouter" exists
- WHEN triggering ingestion for source "openrouter"
- THEN the system resolves the parser_class and rate_limit_rpm from the source row

### Requirement: Idempotent Upsert

The system SHALL use INSERT ... ON CONFLICT DO UPDATE for all model upserts during ingestion. Deduplication is enforced by three DB constraints: (provider_id, slug), (provider_id, family, version), source_payload_hash. Running ingestion twice SHALL produce no duplicates.

#### Scenario: Idempotency

- GIVEN an ingestion run for "openrouter" completed with 30 models_created
- WHEN running the same ingestion again with identical source data
- THEN models_created=0, models_updated=30, models_skipped=0
- AND total AIModel count remains unchanged

#### Scenario: Hash-Based Dedup

- GIVEN a model with source_payload_hash="abc123" exists from a previous run
- WHEN a new ingestion run encounters a payload with the same hash
- THEN the existing model is updated (not duplicated)

### Requirement: Advisory Lock

The system SHALL acquire a PostgreSQL advisory lock (pg_advisory_xact_lock) per source code before processing. If another run for the same source is active, the new run SHALL be rejected with 409 Conflict.

#### Scenario: Concurrent Runs Blocked

- GIVEN an ingestion run for "openrouter" is in progress (status="running")
- WHEN triggering another ingestion for "openrouter"
- THEN the system returns 409 Conflict

#### Scenario: Different Sources Allowed

- GIVEN an ingestion run for "openrouter" is in progress
- WHEN triggering ingestion for "huggingface"
- THEN the new run starts successfully (different advisory lock key)

### Requirement: Batched Upserts

The system SHALL batch upserts in groups of 500-1000 rows for performance. Per-model errors SHALL NOT abort the run; the run finishes as "partial" and logs errors individually.

#### Scenario: Batch Processing

- GIVEN an ingestion source returns 2000 models
- WHEN the parser processes them
- THEN upserts are batched in groups of ~500
- AND the run completes with accurate counts
