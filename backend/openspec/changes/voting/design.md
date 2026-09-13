# Design: Voting System

- **Change:** voting
- **Date:** 2026-09-12
- **Status:** Draft
- **Author:** Forcecast Core Team

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                      API Layer                           │
│  POST /votes  │  DELETE /votes/{id}  │  GET /votes      │
└───────────┬───────────────┬───────────────┬─────────────┘
            │               │               │
            ▼               ▼               ▼
┌─────────────────────────────────────────────────────────┐
│                   VoteService                            │
│  cast_vote()  │  change_vote()  │  revoke_vote()        │
│               │                  │                        │
│  ┌────────────┴──────────────────┴────────────┐         │
│  │         Validation + Idempotency            │         │
│  │  • Auth check (email_verified, not bot)     │         │
│  │  • Model status check (approved only)       │         │
│  │  • Category status check (active only)      │         │
│  │  • Idempotency key lookup                   │         │
│  └────────────────────────────────────────────┘         │
└───────────┬───────────────┬───────────────┬─────────────┘
            │               │               │
            ▼               ▼               ▼
┌─────────────────────────────────────────────────────────┐
│                   Repositories                           │
│  VoteEventRepo  │  UserVoteRepo  │  AuditRepo           │
│  (append-only)  │  (CRUD)        │  (append-only)       │
└───────────┬───────────────┬───────────────┬─────────────┘
            │               │               │
            ▼               ▼               ▼
┌─────────────────────────────────────────────────────────┐
│              PostgreSQL (AsyncSession)                    │
│  vote_events  │  user_votes  │  audit_logs              │
│  (append-only)│  (materialized)│  (append-only)         │
└─────────────────────────────────────────────────────────┘
```

## 2. Module Structure

```
app/voting/
├── __init__.py
├── models/
│   ├── __init__.py
│   ├── vote_event.py      # VoteEvent SQLAlchemy model
│   ├── user_vote.py       # UserVote SQLAlchemy model
│   └── audit_log.py       # AuditLog SQLAlchemy model
├── schemas/
│   ├── __init__.py
│   ├── vote.py            # VoteRequest, VoteResponse
│   ├── user_vote.py       # UserVoteResponse
│   └── audit.py           # AuditEvent
├── repositories/
│   ├── __init__.py
│   ├── vote_event.py      # VoteEventRepository
│   ├── user_vote.py       # UserVoteRepository
│   └── audit_log.py       # AuditLogRepository
├── services/
│   ├── __init__.py
│   ├── vote_service.py    # VoteService (orchestration)
│   └── audit_service.py   # AuditService
├── api/
│   ├── __init__.py
│   └── votes.py           # FastAPI router
└── tests/
    ├── __init__.py
    ├── test_vote_service.py
    ├── test_vote_api.py
    └── conftest.py
```

## 3. Sequence Diagrams

### 3.1 Cast Vote (Happy Path)

```
Client                  API                    VoteService              DB
  │                      │                         │                     │
  │─POST /votes────────>│                         │                     │
  │                      │─get_current_user()────>│                     │
  │                      │<─User──────────────────│                     │
  │                      │                         │                     │
  │                      │─cast_vote(user,...)───>│                     │
  │                      │                         │─validate_model()──>│
  │                      │                         │<─AIModel───────────│
  │                      │                         │─validate_category()>│
  │                      │                         │<─Category──────────│
  │                      │                         │─check_idempotency()>│
  │                      │                         │<─None──────────────│
  │                      │                         │─check_active_vote()>│
  │                      │                         │<─None──────────────│
  │                      │                         │                     │
  │                      │                         │─BEGIN─────────────>│
  │                      │                         │─INSERT vote_event─>│
  │                      │                         │─INSERT user_vote──>│
  │                      │                         │─INSERT audit_log──>│
  │                      │                         │─COMMIT────────────>│
  │                      │                         │                     │
  │                      │<─VoteEvent──────────────│                     │
  │<─201 Created────────│                         │                     │
```

### 3.2 Change Vote (Atomic Transaction)

```
Client                  API                    VoteService              DB
  │                      │                         │                     │
  │─POST /votes────────>│                         │                     │
  │  (different target)  │─cast_vote(user,...)───>│                     │
  │                      │                         │─check_active_vote()>│
  │                      │                         │<─UserVote(A)───────│
  │                      │                         │                     │
  │                      │                         │─BEGIN─────────────>│
  │                      │                         │─UPDATE user_vote──>│
  │                      │                         │  SET target_id=B   │
  │                      │                         │─INSERT vote_event─>│
  │                      │                         │  action='change'   │
  │                      │                         │─INSERT audit_log──>│
  │                      │                         │─COMMIT────────────>│
  │                      │                         │                     │
  │<─201 Created────────│<─VoteEvent──────────────│                     │
```

### 3.3 Revoke Vote

```
Client                  API                    VoteService              DB
  │                      │                         │                     │
  │─DELETE /votes/{id}>│                         │                     │
  │                      │─get_current_user()────>│                     │
  │                      │<─User──────────────────│                     │
  │                      │                         │                     │
  │                      │─revoke_vote(user,...)>│                     │
  │                      │                         │─check_active_vote()>│
  │                      │                         │<─UserVote──────────│
  │                      │                         │                     │
  │                      │                         │─BEGIN─────────────>│
  │                      │                         │─DELETE user_vote──>│
  │                      │                         │─INSERT vote_event─>│
  │                      │                         │  action='revoke'   │
  │                      │                         │─INSERT audit_log──>│
  │                      │                         │─COMMIT────────────>│
  │                      │                         │                     │
  │<─200 OK─────────────│<─VoteEvent──────────────│                     │
```

## 4. Key Design Decisions

### 4.1 Materialized UserVote

**Decision:** Maintain a `user_votes` table as a materialized view of `vote_events`.

**Rationale:**
- RG-08 requires one active vote per category — composite PK enforces this at DB level
- Ranking calculation needs fast iteration over active votes
- Vote queries ("who voted for X") are O(1) vs O(n) scanning vote_events

**Trade-off:** Extra storage, but negligible for expected scale.

### 4.2 Transaction Strategy

**Decision:** Use `BEGIN` transaction with `SELECT FOR UPDATE` on `user_votes` for vote changes.

**Rationale:**
- RG-09 requires atomicity — -1/+1 must be all-or-nothing
- `SELECT FOR UPDATE` prevents race conditions on concurrent votes
- PostgreSQL serializable isolation for extra safety

### 4.3 Idempotency at DB Level

**Decision:** `idempotency_key` has a UNIQUE constraint on `vote_events`.

**Rationale:**
- RG-29 requires idempotent operations
- DB constraint is the ultimate safety net
- Application-level check avoids unnecessary work

### 4.4 Append-Only Enforcement

**Decision:** Use PostgreSQL `CREATE RULE ... DO INSTEAD NOTHING` for append-only tables.

**Rationale:**
- RG-13 requires vote history to be immutable
- DB-level enforcement is tamper-proof
- Application cannot accidentally modify audit trail

### 4.5 API Key Restrictions

**Decision:** Vote endpoints accept JWT only, not API keys.

**Rationale:**
- RG-05 requires API keys to be read-only
- Voting is a write operation
- API keys with `write:votes` scope would violate RG-05

## 5. Database Migration

### Migration: 003_voting_initial

```sql
-- 1. Create vote_events table (append-only)
-- 2. Create user_votes table (materialized current state)
-- 3. Create audit_logs table (append-only)
-- 4. Add indexes
-- 5. Add constraints
-- 6. Add append-only rules
```

**Rollback:** `DROP TABLE audit_logs, user_votes, vote_events;`

## 6. Testing Strategy

### Unit Tests
- `VoteService`: mock repositories, test business logic
- `AuditService`: mock repository, test logging
- Schema validation: test Pydantic models

### Integration Tests
- Vote API endpoints: full request/response cycle
- Database transactions: verify atomicity
- Idempotency: verify duplicate handling

### Test Fixtures
- Authenticated user (email_verified=true)
- Approved model in active category
- TaxonomyVersion (current)
- Redis mock for rate limiting

## 7. Performance Considerations

| Operation | Target | Strategy |
|-----------|--------|----------|
| Vote creation | < 200ms p95 | Single transaction, minimal queries |
| User votes query | < 50ms p95 | Direct lookup on user_votes PK |
| Target vote count | < 50ms p95 | Index on (target_type, target_id) |
| Idempotency check | < 10ms p95 | UNIQUE constraint lookup |

## 8. Future Considerations

- **Ranking calculation:** Read from `user_votes` + `vote_events` for weighted scores
- **Orchestrator voting:** Same mechanism, `target_type='orchestrator'`
- **Collusion detection:** Analyze `vote_events` for patterns (IP, fingerprint, timing)
- **GDPR:** Anonymize `user_votes` and `vote_events` on account deletion

## Artifact
- **Path:** `openspec/changes/voting/design.md`
- **Next:** `sdd-tasks` — break down into implementation tasks
