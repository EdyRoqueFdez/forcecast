# Tasks: HU-T08 — List Orchestrators

## Phase 1: Models & Schema

### 1.1 Add Orchestrator Models
- [x] Add `Orchestrator` model to `entities.py`
- [x] Add `OrchestratorTranslation` model to `entities.py`
- [x] Add `OrchestratorProvider` model to `entities.py`

### 1.2 Add Repository
- [x] Create `app/taxonomy/repositories/orchestrator.py`
- [x] Implement `list_approved(limit, offset, sort, order)`
- [x] Implement `get_providers(orchestrator_ids)`

## Phase 2: Service Layer

### 2.1 Add Public Service Methods
- [x] Add `list_orchestrators()` to `PublicService`
- [x] Implement pagination logic
- [x] Implement i18n translation logic
- [x] Implement caching

## Phase 3: API Layer

### 3.1 Add Public API Endpoint
- [x] Add `GET /api/v1/orchestrators` endpoint
- [x] Add query parameters (lang, category, cursor, limit, sort, order, page)
- [x] Add response schema validation
- [x] Add cache headers

## Phase 4: Seed Data

### 4.1 Create Seed Script
- [x] Create seed script for example orchestrators
- [x] Add translations for EN, ES, PT, FR, ZH
- [x] Add provider associations

## Phase 5: Tests

### 5.1 Repository Tests
- [x] Test `list_approved` returns only approved
- [x] Test pagination works correctly
- [x] Test sorting works correctly
- [x] Test provider fetching works

### 5.2 Service Tests
- [x] Test `list_orchestrators` with locale
- [x] Test cache behavior
- [x] Test cursor pagination

### 5.3 API Tests
- [x] Test endpoint returns 200
- [x] Test pagination works
- [x] Test i18n works
- [x] Test 406 for unsupported locale
- [x] Test p95 < 200ms

## Phase 6: Migration

### 6.1 Create Migration
- [x] Create Alembic migration for new tables
- [x] Add indexes
- [x] Test migration up/down
