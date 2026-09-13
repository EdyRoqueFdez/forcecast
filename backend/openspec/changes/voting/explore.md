# Exploration: Voting System for Forcecast

- **Date:** 2026-09-12
- **Author:** SDD Explorer
- **Status:** Complete

## 1. Current Architecture Summary

### Tech Stack
- **Framework:** FastAPI (async) + Uvicorn
- **ORM:** SQLAlchemy 2.0 (async) + Alembic migrations
- **Validation:** Pydantic v2 + pydantic-settings
- **Database:** PostgreSQL (asyncpg) with SQLite compat
- **Cache:** Redis (with in-memory dict fallback)
- **Auth:** python-jose (JWT RS256), passlib (bcrypt), cryptography (RSA)
- **Testing:** pytest + pytest-asyncio + pytest-cov (TDD enabled)

### Directory Structure
```
app/
├── auth/
│   ├── api/          # OAuth, tokens, API keys routes
│   ├── middleware/    # Auth + rate limiting
│   ├── models/       # User, Session, RefreshToken, APIKey
│   ├── schemas/      # Token, API key, identity, anti-bot schemas
│   └── services/     # JWT, OAuth, API keys, anti-bot
├── taxonomy/
│   ├── api/          # Public + admin routes
│   ├── models/       # 14 entities + enums
│   ├── repositories/ # Data access layer
│   ├── schemas/      # Public API schemas
│   └── services/     # Core, public, versioning, ingestion, webhooks
├── core/
│   └── config.py     # Settings (pydantic-settings)
├── db/
│   ├── migrations/   # Alembic versions
│   └── session.py    # Async session factory
└── main.py           # App entry, router registration
```

### Key Patterns
1. **Hexagonal architecture** — domain logic in services, data access in repositories
2. **Dependency injection** — FastAPI `Depends()` for DB sessions, auth, rate limiting
3. **StrEnum** — all enums extend `StrEnum` for JSON serialization
4. **UUID primary keys** — all entities use `String(36)` UUIDs
5. **Timestamps** — `created_at` + `updated_at` with UTC timezone
6. **JSONType** — `JSON().with_variant(JSONB(), "postgresql")` for SQLite compat
7. **Repository pattern** — one repository per aggregate root
8. **Service layer** — pure domain logic in `core.py`, I/O in service classes

## 2. Relevant Existing Code

### Models (reuse patterns)
- **User** (`app/auth/models/user.py`): id, email, display_name, role (RoleEnum), reputation_score (float, default 5.0), email_verified (bool)
- **AIModel** (`app/taxonomy/models/entities.py`): id, provider_id, slug, status (ModelStatus), + many fields
- **Category** (`app/taxonomy/models/entities.py`): id, slug, taxonomy_version, parent_id
- **TaxonomyVersion** (`app/taxonomy/models/entities.py`): id, version, is_current, released_at
- **ModelCategory** (`app/taxonomy/models/entities.py`): model_id + category_id + taxonomy_version (composite PK)

### Enums (extend for voting)
- **ModelStatus**: draft, pending_review, approved, rejected, deprecated
- **Locale**: en, es, pt, fr, zh

### Services (patterns to follow)
- **DomainError** (`app/taxonomy/services/core.py`): exception with status_code for API translation
- **Pure functions** in `core.py`: slug normalization, status FSM, i18n fallback, pricing
- **Service classes**: `PublicService`, `VersioningService`, `IngestionService` — inject session + repos

### Repositories (patterns to follow)
- **AIModelRepository**: get, list, upsert, upsert_batch, delete — all async, flush + commit pattern
- Constructor takes `session: AsyncSession`

### Middleware (reuse directly)
- **get_current_user** (`app/auth/middleware/auth.py`): JWT extraction, validation, User lookup
- **require_admin**: role check
- **require_api_key**: API key validation + rate limiting
- **get_current_user_or_api_key**: dual auth (JWT first, API key fallback)

### Auth Models (reuse directly)
- **User.reputation_score**: float, default 5.0, range 0.0-10.0 — already exists
- **User.email_verified**: bool — already exists

## 3. Gaps — What Needs to Be Created

### New Entities
1. **VoteEvent** — append-only vote log (RG-08, RG-09, RG-13)
   - id, user_id, target_type (model/orchestrator), target_id, category_id, taxonomy_version
   - action (vote/change/revoke), weight, idempotency_key
   - device_fingerprint, ip_address (for anti-abuse)
   - created_at (append-only, no updated_at)

2. **UserVote** — materialized current state (derived from VoteEvent)
   - user_id + category_id + target_type → unique constraint
   - target_id, weight, vote_event_id (FK to latest event)
   - created_at, updated_at

3. **AuditLog** — append-only audit trail (RG-07)
   - id, actor_id, action, entity_type, entity_id
   - details (JSONB), request_id, ip_address, user_agent
   - created_at (append-only)

### New Enums
- **VoteAction**: vote, change, revoke
- **TargetType**: model, orchestrator

### New Services
4. **VoteService** — core voting logic
   - cast_vote(user, target_type, target_id, category_id, idempotency_key)
   - change_vote(user, target_type, target_id, category_id, idempotency_key)
   - revoke_vote(user, target_type, category_id, idempotency_key)
   - All three must be transactional (RG-09)

5. **AuditService** — append-only audit logging
   - log(actor_id, action, entity_type, entity_id, details, request_id, ip)

### New Repositories
6. **VoteEventRepository** — append-only data access
7. **UserVoteRepository** — current vote state CRUD
8. **AuditLogRepository** — append-only audit access

### New API Routes
9. **POST /api/v1/votes** — cast or change vote
10. **DELETE /api/v1/votes/{category_id}** — revoke vote
11. **GET /api/v1/users/me/votes** — list user's votes
12. **GET /api/v1/models/{slug}/votes** — vote count for model (public)

### New Schemas
13. **VoteRequest** — Pydantic schema for vote input
14. **VoteResponse** — Pydantic schema for vote output
15. **AuditEvent** — Pydantic schema for audit log

### Database Migration
16. **003_voting_initial** — create vote_events, user_votes, audit_logs tables

## 4. Design Considerations

### Trade-offs

| Decision | Option A | Option B | Recommendation |
|----------|----------|----------|----------------|
| Current vote state | Derived from VoteEvent at query time | Materialized UserVote table | **Option B** — UserVote for performance, sync on every VoteEvent |
| Vote target | Separate tables for model/orchestrator votes | Single vote_events table with target_type discriminator | **Option B** — single table, simpler queries |
| Ranking calculation | Real-time from VoteEvent | Pre-computed snapshots | **Option B** — snapshots for performance, immutable per RG-12 |
| AuditLog storage | Same DB as domain | Separate append-only store | **Option A** — same DB for MVP, migrate later if needed |

### Risks
1. **Race conditions on vote changes** — Two simultaneous changes could corrupt state. Mitigate with `SELECT FOR UPDATE` or advisory locks.
2. **Idempotency** — Duplicate requests must not create duplicate votes. Use `idempotency_key` unique constraint.
3. **VoteEvent growth** — Append-only table grows indefinitely. Partition by month, archive old data.
4. **Reputation integration** — Vote weight depends on user reputation. Must query User.reputation_score at vote time.

### Dependencies
- TaxonomyVersion must exist (current version for vote reference)
- AIModel must be in `approved` status (RG-36)
- User must be authenticated + email_verified (RG-03)
- User must not be flagged as bot (anti_bot.is_strict_mode)

## 5. Recommended Approach

### Phase 1: Core Voting (MVP)
1. Create VoteEvent + UserVote models
2. Create VoteService with transactional vote/change/revoke
3. Create vote API routes with auth guards
4. Create Alembic migration
5. Write tests (TDD: RED-GREEN-REFACTOR)

### Phase 2: Audit Logging
6. Create AuditLog model
7. Create AuditService
8. Integrate into VoteService + existing auth flows

### Phase 3: Ranking Foundation
9. Create ranking calculation service (reads from UserVote + VoteEvent)
10. Expose ranking API endpoints

### Deferred
- Orchestrator voting (separate target_type, same mechanism)
- Collusion detection (requires vote history analysis)
- Data export/GDPR (requires vote anonymization)

## Artifact
- **Path:** `openspec/changes/voting/explore.md`
- **Next:** `sdd-propose` — create change proposal with intent, scope, and approach
