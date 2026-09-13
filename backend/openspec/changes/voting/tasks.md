# Tasks: Voting System

- **Change:** voting
- **Date:** 2026-09-12
- **Status:** Ready
- **Author:** Forcecast Core Team

## Review Workload Forecast

- **Estimated changed lines:** ~1200
- **400-line budget risk:** High
- **Chained PRs recommended:** Yes
- **Decision needed before apply:** Yes — choose chained PR strategy

## Tasks

### Phase 1: Models + Migration (3 tasks)

#### 1.1 Create VoteEvent Model
- **File:** `app/voting/models/vote_event.py`
- **Spec:** spec-01-vote-event.md
- **TDD:** RED → write test for model fields, GREEN → create model, REFACTOR
- **Acceptance:**
  - [ ] VoteEvent model with all fields from spec
  - [ ] Append-only rules (no UPDATE/DELETE)
  - [ ] Unique constraint on `idempotency_key`
  - [ ] Foreign keys to users, categories, taxonomy_versions
  - [ ] Indexes for user, target, category, created_at

#### 1.2 Create UserVote Model
- **File:** `app/voting/models/user_vote.py`
- **Spec:** spec-02-user-vote.md
- **TDD:** RED → write test, GREEN → create model, REFACTOR
- **Acceptance:**
  - [ ] UserVote model with composite PK (user_id, category_id, target_type)
  - [ ] Foreign keys to users, categories, vote_events
  - [ ] Indexes for target, user

#### 1.3 Create AuditLog Model
- **File:** `app/voting/models/audit_log.py`
- **Spec:** spec-04-audit-log.md
- **TDD:** RED → write test, GREEN → create model, REFACTOR
- **Acceptance:**
  - [ ] AuditLog model with all fields from spec
  - [ ] Append-only rules
  - [ ] Foreign key to users
  - [ ] Indexes for actor, entity, action, created_at

#### 1.4 Create Voting Enums
- **File:** `app/voting/models/enums.py`
- **Acceptance:**
  - [ ] VoteAction enum: vote, change, revoke
  - [ ] TargetType enum: model, orchestrator

#### 1.5 Create Alembic Migration
- **File:** `app/db/migrations/versions/003_voting_initial.py`
- **Acceptance:**
  - [ ] Creates vote_events, user_votes, audit_logs tables
  - [ ] Adds all constraints and indexes
  - [ ] Adds append-only rules
  - [ ] `alembic upgrade head` succeeds
  - [ ] `alembic downgrade -1` succeeds

### Phase 2: Repositories (3 tasks)

#### 2.1 Create VoteEventRepository
- **File:** `app/voting/repositories/vote_event.py`
- **Pattern:** Follow `app/taxonomy/repositories/ai_model.py`
- **Acceptance:**
  - [ ] `get(id)` → VoteEvent | None
  - [ ] `get_by_idempotency_key(key)` → VoteEvent | None
  - [ ] `list_by_user(user_id)` → list[VoteEvent]
  - [ ] `list_by_target(target_type, target_id)` → list[VoteEvent]
  - [ ] `create(event_data)` → VoteEvent (append-only, no update/delete)

#### 2.2 Create UserVoteRepository
- **File:** `app/voting/repositories/user_vote.py`
- **Acceptance:**
  - [ ] `get(user_id, category_id, target_type)` → UserVote | None
  - [ ] `list_by_user(user_id)` → list[UserVote]
  - [ ] `list_by_target(target_type, target_id)` → list[UserVote]
  - [ ] `create(vote_data)` → UserVote
  - [ ] `update(vote_id, vote_data)` → UserVote
  - [ ] `delete(vote_id)` → None

#### 2.3 Create AuditLogRepository
- **File:** `app/voting/repositories/audit_log.py`
- **Acceptance:**
  - [ ] `create(log_data)` → AuditLog (append-only)
  - [ ] `list_by_actor(actor_id)` → list[AuditLog]
  - [ ] `list_by_entity(entity_type, entity_id)` → list[AuditLog]

### Phase 3: Services (2 tasks)

#### 3.1 Create AuditService
- **File:** `app/voting/services/audit_service.py`
- **Spec:** spec-04-audit-log.md
- **Acceptance:**
  - [ ] `log(actor_id, action, entity_type, entity_id, details, request_id, ip, user_agent)` → AuditLog
  - [ ] Creates append-only AuditLog entry

#### 3.2 Create VoteService
- **File:** `app/voting/services/vote_service.py`
- **Spec:** spec-03-vote-service.md
- **TDD:** RED → write tests for all scenarios, GREEN → implement, REFACTOR
- **Acceptance:**
  - [ ] `cast_vote()` — creates vote, validates auth/model/category
  - [ ] `change_vote()` — atomic -1/+1 transaction
  - [ ] `revoke_vote()` — deletes active vote
  - [ ] `get_user_votes()` — returns user's active votes
  - [ ] `get_target_votes()` — returns vote count for target
  - [ ] Idempotency: same key returns existing event
  - [ ] Atomicity: transaction rolls back on failure
  - [ ] Audit: all actions logged

### Phase 4: API (2 tasks)

#### 4.1 Create Vote Schemas
- **File:** `app/voting/schemas/vote.py`
- **Spec:** spec-05-vote-api.md
- **Acceptance:**
  - [ ] VoteRequest (target_type, target_id, category_id, idempotency_key)
  - [ ] VoteResponse (id, user_id, target_type, target_id, category_id, action, weight, created_at)
  - [ ] UserVotesResponse (list of votes)
  - [ ] ModelVotesResponse (total, weighted, by category)
  - [ ] Validation: UUID format, idempotency_key length

#### 4.2 Create Vote API Router
- **File:** `app/voting/api/votes.py`
- **Spec:** spec-05-vote-api.md
- **Acceptance:**
  - [ ] `POST /api/v1/votes` — cast or change vote
  - [ ] `DELETE /api/v1/votes/{category_id}` — revoke vote
  - [ ] `GET /api/v1/users/me/votes` — user's votes
  - [ ] `GET /api/v1/models/{slug}/votes` — model vote count
  - [ ] Auth: JWT required for write, JWT or API key for read
  - [ ] Rate limiting: 60 req/min authenticated
  - [ ] Error responses: 401, 403, 404, 409, 429

#### 4.3 Register Router in Main App
- **File:** `app/main.py`
- **Acceptance:**
  - [ ] Vote router included in app
  - [ ] All vote endpoints accessible

### Phase 5: Integration + Tests (2 tasks)

#### 5.1 Integration Tests
- **File:** `app/voting/tests/test_vote_api.py`
- **Acceptance:**
  - [ ] Test cast vote happy path
  - [ ] Test change vote happy path
  - [ ] Test revoke vote happy path
  - [ ] Test idempotency
  - [ ] Test unauthenticated access (401)
  - [ ] Test unverified email (403)
  - [ ] Test bot detected (403)
  - [ ] Test unapproved model (403)
  - [ ] Test duplicate active vote (409)
  - [ ] Test rate limiting (429)

#### 5.2 Unit Tests
- **File:** `app/voting/tests/test_vote_service.py`
- **Acceptance:**
  - [ ] Test VoteService business logic
  - [ ] Test AuditService logging
  - [ ] Test repository CRUD

### Phase 6: Documentation (1 task)

#### 6.1 Update Audit Document
- **File:** `docs/audit/business-rules-compliance.md`
- **Acceptance:**
  - [ ] Mark RG-08, RG-09, RG-13, RG-14 as ✅
  - [ ] Mark Fase 1 as completed
  - [ ] Update checklist

## Task Dependency Graph

```
1.1 VoteEvent ─┐
1.2 UserVote ──┤
1.3 AuditLog ──┼── 1.5 Migration
1.4 Enums ─────┘
                │
                ▼
2.1 VoteEventRepo ─┐
2.2 UserVoteRepo ──┼── 3.2 VoteService ── 4.2 Vote API ── 5.1 Integration
2.3 AuditLogRepo ──┘         │                    │
                             ▼                    ▼
                      3.1 AuditService      4.1 Schemas
                                              │
                                              ▼
                                       4.3 Register Router
                                              │
                                              ▼
                                       5.2 Unit Tests
                                              │
                                              ▼
                                       6.1 Update Audit
```

## Definition of Done

- [ ] All tasks completed
- [ ] All tests passing
- [ ] `alembic upgrade head` succeeds
- [ ] `alembic downgrade -1` succeeds
- [ ] No lint errors (ruff)
- [ ] No type errors (mypy)
- [ ] Coverage >= 80%
- [ ] Audit document updated

## Chained PR Strategy

This change (~1200 lines) exceeds the 400-line budget. Recommended PR split:

1. **PR 1: Models + Migration** (~300 lines)
   - Tasks 1.1-1.5
   - VoteEvent, UserVote, AuditLog models + migration

2. **PR 2: Repositories + Services** (~500 lines)
   - Tasks 2.1-2.3, 3.1-3.2
   - Repositories + VoteService + AuditService

3. **PR 3: API + Tests** (~400 lines)
   - Tasks 4.1-4.3, 5.1-5.2
   - Schemas, routes, tests, documentation

## Artifact
- **Path:** `openspec/changes/voting/tasks.md`
- **Next:** `sdd-apply` — implement tasks in order
