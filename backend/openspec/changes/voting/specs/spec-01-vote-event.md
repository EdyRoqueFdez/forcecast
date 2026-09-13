# Spec: VoteEvent Model

- **Path:** `openspec/changes/voting/specs/spec-01-vote-event.md`
- **Version:** `1.0.0`
- **Status:** Draft
- **Owner:** Forcecast Core Team
- **Last Updated:** `2026-09-12`

## 1. Purpose

Define the append-only vote event log that records every vote action (vote, change, revoke) with full traceability. This is the source of truth for vote history (RG-13).

## 2. Conventions

- `MUST` / `SHALL`: obligatory requirement
- `SHOULD`: recommended, requires justification if not applied
- `MAY`: optional behavior
- All times in UTC
- All IDs are UUID v4 strings

## 3. Entity: VoteEvent

### 3.1 Table Schema

```sql
CREATE TABLE vote_events (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    target_type VARCHAR(50) NOT NULL,  -- 'model' or 'orchestrator'
    target_id VARCHAR(36) NOT NULL,
    category_id VARCHAR(36) NOT NULL REFERENCES categories(id),
    taxonomy_version VARCHAR(50) NOT NULL REFERENCES taxonomy_versions(version),
    action VARCHAR(50) NOT NULL,  -- 'vote', 'change', 'revoke'
    weight DECIMAL(10,4) NOT NULL DEFAULT 1.0,
    idempotency_key VARCHAR(255) UNIQUE NOT NULL,
    device_fingerprint VARCHAR(64),
    ip_address VARCHAR(45),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Append-only: no UPDATE or DELETE allowed
CREATE RULE vote_events_no_update AS ON UPDATE TO vote_events DO INSTEAD NOTHING;
CREATE RULE vote_events_no_delete AS ON DELETE TO vote_events DO INSTEAD NOTHING;
```

### 3.2 Constraints

| Constraint | Type | Description |
|------------|------|-------------|
| `pk_vote_events_id` | PRIMARY KEY | `id` |
| `fk_vote_events_user` | FOREIGN KEY | `user_id` → `users.id` |
| `fk_vote_events_category` | FOREIGN KEY | `category_id` → `categories.id` |
| `fk_vote_events_taxonomy` | FOREIGN KEY | `taxonomy_version` → `taxonomy_versions.version` |
| `uq_vote_events_idempotency` | UNIQUE | `idempotency_key` |
| `ck_vote_events_target_type` | CHECK | `target_type IN ('model', 'orchestrator')` |
| `ck_vote_events_action` | CHECK | `action IN ('vote', 'change', 'revoke')` |
| `ck_vote_events_weight_positive` | CHECK | `weight >= 0` |

### 3.3 Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_vote_events_user` | `user_id` | User's vote history |
| `idx_vote_events_target` | `target_type, target_id` | Target's vote count |
| `idx_vote_events_category` | `category_id` | Category vote queries |
| `idx_vote_events_created` | `created_at` | Time-range queries |

### 3.4 Rules

- **RG-13:** VoteEvent MUST be append-only. No UPDATE or DELETE operations.
- **RG-35:** Every vote MUST reference the current TaxonomyVersion at vote time.
- **RG-29:** `idempotency_key` MUST be unique. Duplicate requests MUST return existing event, not error.

## 4. Scenarios

### 4.1 Cast Vote

**Given** an authenticated user with `email_verified=true` and `reputation_score >= 0`
**And** a model with `status='approved'` in a category
**And** the user has no active vote in that category
**When** the user casts a vote with a valid `idempotency_key`
**Then** a VoteEvent MUST be created with `action='vote'`
**And** the event MUST reference the current TaxonomyVersion
**And** the event MUST include `device_fingerprint` and `ip_address`
**And** the operation MUST be idempotent (same key returns same event)

### 4.2 Change Vote

**Given** an authenticated user with an active vote in a category
**When** the user changes to a different target with a new `idempotency_key`
**Then** a VoteEvent MUST be created with `action='change'`
**And** the previous vote MUST receive weight `-1` adjustment
**And** the new vote MUST receive weight `+1` adjustment
**And** both adjustments MUST be atomic (transaction)

### 4.3 Revoke Vote

**Given** an authenticated user with an active vote in a category
**When** the user revokes the vote with a new `idempotency_key`
**Then** a VoteEvent MUST be created with `action='revoke'`
**And** the previous vote MUST receive weight `-1` adjustment
**And** the category MUST have no active vote for this user

### 4.4 Idempotent Request

**Given** a VoteEvent with `idempotency_key='abc123'` already exists
**When** a new request arrives with the same `idempotency_key='abc123'`
**Then** the system MUST return the existing VoteEvent
**And** MUST NOT create a new VoteEvent
**And** MUST NOT modify any state

### 4.5 Unauthenticated Vote

**Given** no authentication token is provided
**When** the user attempts to cast a vote
**Then** the API MUST return `401 Unauthorized`

### 4.6 Vote on Unapproved Model

**Given** a model with `status='draft'` or `status='rejected'` or `status='deprecated'`
**When** the user attempts to vote on that model
**Then** the API MUST return `403 Forbidden`
**And** MUST NOT create a VoteEvent

### 4.7 Duplicate Active Vote

**Given** the user already has an active vote in the category for the same target
**When** the user attempts to cast the same vote again
**Then** the API MUST return `409 Conflict`
**And** MUST NOT create a duplicate VoteEvent

## 5. Non-Functional Requirements

- **Performance:** Vote event creation MUST complete in < 100ms (p95)
- **Storage:** Append-only, no UPDATE/DELETE rules enforced at DB level
- **Audit:** Every vote event MUST be traceable to a user, target, category, and timestamp
- **Idempotency:** Duplicate requests MUST be handled gracefully within 1 second

## Artifact
- **Path:** `openspec/changes/voting/specs/spec-01-vote-event.md`
- **Next:** `spec-02-user-vote.md`
