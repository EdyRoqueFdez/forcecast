# Spec: UserVote Model

- **Path:** `openspec/changes/voting/specs/spec-02-user-vote.md`
- **Version:** `1.0.0`
- **Status:** Draft
- **Owner:** Forcecast Core Team
- **Last Updated:** `2026-09-12`

## 1. Purpose

Define the materialized current vote state per user, category, and target type. This table is derived from VoteEvent and provides fast queries for "who voted what" without scanning the append-only log.

## 2. Entity: UserVote

### 2.1 Table Schema

```sql
CREATE TABLE user_votes (
    user_id VARCHAR(36) NOT NULL REFERENCES users(id),
    category_id VARCHAR(36) NOT NULL REFERENCES categories(id),
    target_type VARCHAR(50) NOT NULL,  -- 'model' or 'orchestrator'
    target_id VARCHAR(36) NOT NULL,
    weight DECIMAL(10,4) NOT NULL DEFAULT 1.0,
    vote_event_id VARCHAR(36) NOT NULL REFERENCES vote_events(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, category_id, target_type)
);
```

### 2.2 Constraints

| Constraint | Type | Description |
|------------|------|-------------|
| `pk_user_votes` | PRIMARY KEY | `(user_id, category_id, target_type)` |
| `fk_user_votes_user` | FOREIGN KEY | `user_id` → `users.id` |
| `fk_user_votes_category` | FOREIGN KEY | `category_id` → `categories.id` |
| `fk_user_votes_event` | FOREIGN KEY | `vote_event_id` → `vote_events.id` |
| `ck_user_votes_target_type` | CHECK | `target_type IN ('model', 'orchestrator')` |
| `ck_user_votes_weight_nonneg` | CHECK | `weight >= 0` |

### 2.3 Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `idx_user_votes_target` | `target_type, target_id` | All votes for a target |
| `idx_user_votes_user` | `user_id` | User's active votes |

### 2.4 Rules

- **RG-08:** One active vote per user per category per target_type. The composite PK enforces this.
- **RG-08:** When a vote changes, the materialized row is UPDATEd atomically with the VoteEvent INSERT.
- **RG-14:** When a vote is revoked, the materialized row is DELETEd atomically with the VoteEvent INSERT.

## 3. Scenarios

### 3.1 New Vote Creates Row

**Given** the user has no active vote in the category for target_type
**When** a vote is cast
**Then** a UserVote row MUST be inserted with `target_id`, `weight`, and `vote_event_id`

### 3.2 Change Vote Updates Row

**Given** the user has an active vote in the category for target_type pointing to `target_id=A`
**When** the user changes to `target_id=B`
**Then** the UserVote row MUST be updated: `target_id=B`, `vote_event_id=new_event`, `updated_at=NOW()`

### 3.3 Revoke Vote Deletes Row

**Given** the user has an active vote in the category for target_type
**When** the user revokes the vote
**Then** the UserVote row MUST be deleted
**And** the category MUST have no active vote for this user

### 3.4 Transaction Atomicity

**Given** a vote change is in progress
**When** the VoteEvent INSERT succeeds but the UserVote UPDATE fails
**Then** the entire transaction MUST be rolled back
**And** no VoteEvent MUST be persisted
**And** no UserVote MUST be modified

## 4. Materialization Strategy

UserVote is a **materialized view** of VoteEvent:
- On every VoteEvent INSERT (vote/change/revoke), the corresponding UserVote row is INSERT/UPDATE/DELETEd
- This happens in the same transaction (RG-09 atomicity)
- The `vote_event_id` column links to the latest VoteEvent that determined this state

### Why Materialize?
- **Performance:** Querying "who voted for X" is O(1) with UserVote vs O(n) scanning VoteEvent
- **RG-08 enforcement:** Composite PK prevents duplicate active votes at DB level
- **Ranking calculation:** Rankings need to iterate over active votes efficiently

## 5. Non-Functional Requirements

- **Consistency:** UserVote MUST always reflect the latest VoteEvent state
- **Atomicity:** UserVote mutation MUST be in the same transaction as VoteEvent INSERT
- **Performance:** Vote queries MUST complete in < 50ms (p95)

## Artifact
- **Path:** `openspec/changes/voting/specs/spec-02-user-vote.md`
- **Next:** `spec-03-vote-service.md`
