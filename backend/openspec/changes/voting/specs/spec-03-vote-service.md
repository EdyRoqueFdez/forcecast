# Spec: VoteService

- **Path:** `openspec/changes/voting/specs/spec-03-vote-service.md`
- **Version:** `1.0.0`
- **Status:** Draft
- **Owner:** Forcecast Core Team
- **Last Updated:** `2026-09-12`

## 1. Purpose

Define the service layer that orchestrates vote operations. This is the single entry point for all vote mutations, enforcing business rules, transactional guarantees, and idempotency.

## 2. Interface

```python
class VoteService:
    def __init__(self, session: AsyncSession, vote_event_repo: VoteEventRepository, user_vote_repo: UserVoteRepository, audit_service: AuditService):
        ...

    async def cast_vote(
        self,
        user: User,
        target_type: str,  # 'model' or 'orchestrator'
        target_id: str,
        category_id: str,
        idempotency_key: str,
        request_id: str | None = None,
    ) -> VoteEvent:
        """Cast a new vote. Raises DomainError on failure."""
        ...

    async def change_vote(
        self,
        user: User,
        target_type: str,
        target_id: str,
        category_id: str,
        idempotency_key: str,
        request_id: str | None = None,
    ) -> VoteEvent:
        """Change an existing vote. Raises DomainError on failure."""
        ...

    async def revoke_vote(
        self,
        user: User,
        target_type: str,
        category_id: str,
        idempotency_key: str,
        request_id: str | None = None,
    ) -> VoteEvent:
        """Revoke an existing vote. Raises DomainError on failure."""
        ...

    async def get_user_votes(
        self,
        user: User,
    ) -> list[UserVote]:
        """Get all active votes for a user."""
        ...

    async def get_target_votes(
        self,
        target_type: str,
        target_id: str,
    ) -> int:
        """Get total vote count for a target."""
        ...
```

## 3. Business Rules

### 3.1 Authentication (RG-03)

- User MUST be authenticated (JWT or API key)
- User MUST have `email_verified=true`
- User MUST NOT be in strict mode (anti_bot.is_strict_mode = false)
- If any condition fails, raise `DomainError(403, "Vote not allowed: ...")`

### 3.2 Model Validation (RG-36)

- If `target_type='model'`, the model MUST exist and have `status='approved'`
- If model is `draft`, `pending_review`, `rejected`, or `deprecated`, raise `DomainError(403, "Model not votable")`

### 3.3 Category Validation

- Category MUST exist and have `status='active'`
- If category is `deprecated`, raise `DomainError(403, "Category not active")`

### 3.4 Taxonomy Version (RG-35)

- Vote MUST reference the current TaxonomyVersion (`is_current=true`)
- The `taxonomy_version` field on VoteEvent is set to the current version

### 3.5 Idempotency (RG-29)

- If `idempotency_key` already exists in `vote_events`, return the existing event
- Do NOT create a new event
- Do NOT modify any state

### 3.6 One Vote Per Category (RG-08)

- User MUST have at most one active vote per category per target_type
- Enforced by `user_votes` composite PK: `(user_id, category_id, target_type)`

### 3.7 Atomic Vote Change (RG-09)

- Vote change MUST be atomic: -1 to old target, +1 to new target
- Use `BEGIN` transaction with `SELECT FOR UPDATE` on `user_votes`
- If any step fails, rollback entire transaction

### 3.8 Weight Calculation (Phase 2 placeholder)

- For MVP: `weight = 1.0` (constant)
- Phase 2: `weight = f(reputation, age, consistency, anti_bot_signals)`

### 3.9 Audit Logging (RG-07)

- Every vote action MUST be logged in `audit_logs`
- Log: actor_id, action, entity_type='vote', entity_id=vote_event.id, details={target_type, target_id, category_id}

## 4. Scenarios

### 4.1 Successful Cast

**Given** an authenticated user with `email_verified=true`
**And** a model with `status='approved'` in an active category
**And** the user has no active vote in that category
**When** `cast_vote()` is called with a valid `idempotency_key`
**Then** a VoteEvent MUST be created with `action='vote'`
**And** a UserVote MUST be created
**And** an AuditLog MUST be created
**And** the VoteEvent MUST be returned

### 4.2 Cast with Existing Active Vote

**Given** the user already has an active vote in the category for the same target_type
**When** `cast_vote()` is called
**Then** `DomainError(409, "Active vote exists in this category")` MUST be raised
**And** no VoteEvent MUST be created

### 4.3 Successful Change

**Given** the user has an active vote pointing to `target_id=A`
**When** `change_vote()` is called with `target_id=B`
**Then** a VoteEvent MUST be created with `action='change'`
**And** the UserVote MUST be updated to `target_id=B`
**And** the old target MUST receive `-1` adjustment
**And** the new target MUST receive `+1` adjustment

### 4.4 Successful Revoke

**Given** the user has an active vote in the category
**When** `revoke_vote()` is called
**Then** a VoteEvent MUST be created with `action='revoke'`
**And** the UserVote MUST be deleted
**And** the old target MUST receive `-1` adjustment

### 4.5 Idempotent Cast

**Given** a VoteEvent with `idempotency_key='abc123'` exists
**When** `cast_vote()` is called with the same `idempotency_key='abc123'`
**Then** the existing VoteEvent MUST be returned
**And** no new VoteEvent MUST be created

### 4.6 Unauthenticated User

**Given** no valid JWT or API key
**When** `cast_vote()` is called
**Then** `DomainError(401, "Missing authentication")` MUST be raised

### 4.7 Unverified Email

**Given** a user with `email_verified=false`
**When** `cast_vote()` is called
**Then** `DomainError(403, "Email verification required")` MUST be raised

### 4.8 Bot Detected

**Given** a user in strict mode (`reputation_score < 3.0`)
**When** `cast_vote()` is called
**Then** `DomainError(403, "Bot signals detected")` MUST be raised

### 4.9 Vote on Unapproved Model

**Given** a model with `status='draft'`
**When** `cast_vote()` is called for that model
**Then** `DomainError(403, "Model not votable")` MUST be raised

## 5. Non-Functional Requirements

- **Atomicity:** Vote changes MUST complete in a single transaction
- **Performance:** Vote operations MUST complete in < 200ms (p95)
- **Idempotency:** Duplicate requests MUST be handled within 1 second
- **Audit:** 100% of vote actions MUST be logged

## Artifact
- **Path:** `openspec/changes/voting/specs/spec-03-vote-service.md`
- **Next:** `spec-04-audit-log.md`
