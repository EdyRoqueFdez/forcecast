# Proposal: Voting System for Forcecast

- **Change:** voting
- **Date:** 2026-09-12
- **Status:** Draft
- **Author:** Forcecast Core Team

## 1. Intent

Forcecast is an AI model catalog and comparator. The core value proposition is **community-driven rankings** of AI models. Without a voting system, there is no product — just a static catalog.

This change implements the foundational voting mechanism that enables:
- Users to vote on AI models within categories
- Atomic, transactional vote changes with full audit trail
- Foundation for ranking calculation (next phase)
- Compliance with MVP non-negotiable business rules (RG-08, RG-09, RG-13, RG-14)

**Why now:** The taxonomy system is complete (archived). Auth is complete. The next logical step is voting — without it, no other feature (rankings, collusion detection, GDPR) can proceed.

## 2. Scope

### In Scope (This Change)
- VoteEvent model (append-only vote log)
- UserVote model (materialized current state)
- VoteService with transactional vote/change/revoke
- Vote API routes with auth guards
- AuditLog model + AuditService
- Alembic migration for new tables
- Tests (TDD: RED-GREEN-REFACTOR)

### Out Scope (Future Changes)
- Ranking calculation service (Phase 3)
- Orchestrator voting (same mechanism, different target_type)
- Collusion detection (requires vote history analysis)
- Data export / GDPR (requires vote anonymization)
- Weighted voting by reputation (Phase 2)
- Anti-bot signals in vote weight (Phase 2)

## 3. Approach

### Architecture
Follow existing hexagonal patterns:
- **Models:** `app/voting/models/` — VoteEvent, UserVote, AuditLog
- **Services:** `app/voting/services/` — VoteService, AuditService
- **Repositories:** `app/voting/repositories/` — VoteEventRepository, UserVoteRepository, AuditLogRepository
- **Schemas:** `app/voting/schemas/` — VoteRequest, VoteResponse, AuditEvent
- **API:** `app/voting/api/` — vote routes

### Data Model
```
vote_events (append-only)
├── id: UUID PK
├── user_id: FK → users.id
├── target_type: enum (model, orchestrator)
├── target_id: UUID (model.id or orchestrator.id)
├── category_id: FK → categories.id
├── taxonomy_version: FK → taxonomy_versions.version
├── action: enum (vote, change, revoke)
├── weight: Decimal (computed at vote time)
├── idempotency_key: String, UNIQUE
├── device_fingerprint: String
├── ip_address: String
└── created_at: DateTime

user_votes (materialized current state)
├── user_id: UUID PK (part of composite)
├── category_id: UUID PK (part of composite)
├── target_type: enum PK (part of composite)
├── target_id: UUID
├── weight: Decimal
├── vote_event_id: FK → vote_events.id
├── created_at: DateTime
└── updated_at: DateTime

audit_logs (append-only)
├── id: UUID PK
├── actor_id: FK → users.id
├── action: String
├── entity_type: String
├── entity_id: UUID
├── details: JSONB
├── request_id: String
├── ip_address: String
├── user_agent: String
└── created_at: DateTime
```

### Vote Flow
1. **Authenticate** — get_current_user (JWT or API key)
2. **Validate** — email_verified, not bot, model status == approved
3. **Check idempotency** — if idempotency_key exists, return existing vote
4. **Get current vote** — SELECT FOR UPDATE on user_votes
5. **Compute weight** — for now, weight = 1.0 (reputation weighting in Phase 2)
6. **Transaction:**
   - If existing vote: UPDATE user_votes SET target_id=new, weight=new, vote_event_id=new
   - If no existing vote: INSERT user_votes
   - INSERT vote_events (append-only)
   - INSERT audit_logs
7. **Commit** — atomic, all or nothing

### API Design
```
POST   /api/v1/votes              # cast or change vote
DELETE /api/v1/votes/{category_id} # revoke vote
GET    /api/v1/users/me/votes      # list user's votes
GET    /api/v1/models/{slug}/votes # vote count for model (public)
```

## 4. Rollback Plan

1. **Database:** Alembic migration is reversible — `alembic downgrade` removes new tables
2. **Code:** Git revert of the voting commit(s)
3. **Data:** No existing data is modified — only new tables created
4. **Risk:** LOW — greenfield addition, no changes to existing tables

## 5. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Race conditions on concurrent votes | Medium | High | SELECT FOR UPDATE on user_votes, advisory locks |
| Idempotency key collisions | Low | Medium | UUID-based keys, UNIQUE constraint |
| VoteEvent table growth | High | Low | Partition by month, archive old data (deferred) |
| Weight computation complexity | Low | Medium | Start with weight=1.0, add reputation later |

## 6. Dependencies

- ✅ TaxonomyVersion model (exists)
- ✅ AIModel with status field (exists)
- ✅ User with reputation_score and email_verified (exists)
- ✅ Auth middleware (exists)
- ✅ Category model (exists)
- ✅ Alembic setup (exists)

No external dependencies required.

## 7. Success Criteria

- [ ] User can cast a vote on an approved model in a category
- [ ] User can change their vote (atomic -1/+1)
- [ ] User can revoke their vote
- [ ] Duplicate requests (same idempotency_key) return existing vote, not error
- [ ] Vote is recorded in vote_events (append-only)
- [ ] Current state is reflected in user_votes
- [ ] All vote actions are logged in audit_logs
- [ ] Only authenticated + email_verified users can vote
- [ ] Only approved models are votable
- [ ] All tests pass (TDD: RED-GREEN-REFACTOR)
- [ ] Alembic migration runs cleanly up and down

## Artifact
- **Path:** `openspec/changes/voting/proposal.md`
- **Next:** `sdd-spec` — create detailed specifications with Given/When/Then scenarios
