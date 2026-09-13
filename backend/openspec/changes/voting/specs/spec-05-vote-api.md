# Spec: Vote API

- **Path:** `openspec/changes/voting/specs/spec-05-vote-api.md`
- **Version:** `1.0.0`
- **Status:** Draft
- **Owner:** Forcecast Core Team
- **Last Updated:** `2026-09-12`

## 1. Purpose

Define the REST API endpoints for voting operations. All endpoints require authentication.

## 2. Base Path

`/api/v1`

## 3. Endpoints

### 3.1 POST /votes — Cast or Change Vote

**Description:** Cast a new vote or change an existing vote in a category.

**Auth:** Required (JWT or API key with `write:votes` scope — but API keys are read-only per RG-05, so JWT only)

**Request Body:**
```json
{
  "target_type": "model",
  "target_id": "uuid-of-model",
  "category_id": "uuid-of-category",
  "idempotency_key": "unique-key-uuid"
}
```

**Response 201:**
```json
{
  "id": "uuid-of-vote-event",
  "user_id": "uuid-of-user",
  "target_type": "model",
  "target_id": "uuid-of-model",
  "category_id": "uuid-of-category",
  "action": "vote",
  "weight": 1.0,
  "created_at": "2026-09-12T10:00:00Z"
}
```

**Errors:**
| Code | Detail | Condition |
|------|--------|-----------|
| 401 | Missing authentication | No JWT |
| 403 | Email verification required | `email_verified=false` |
| 403 | Bot signals detected | `is_strict_mode=true` |
| 403 | Model not votable | Model status != approved |
| 403 | Category not active | Category status != active |
| 409 | Active vote exists | User already has active vote in category |
| 429 | Rate limit exceeded | Too many requests |

### 3.2 DELETE /votes/{category_id} — Revoke Vote

**Description:** Revoke the active vote in a category.

**Auth:** Required (JWT only)

**Path Parameters:**
- `category_id` (UUID) — the category to revoke vote from

**Request Body:** None

**Response 200:**
```json
{
  "id": "uuid-of-vote-event",
  "user_id": "uuid-of-user",
  "target_type": "model",
  "target_id": "uuid-of-model",
  "category_id": "uuid-of-category",
  "action": "revoke",
  "weight": -1.0,
  "created_at": "2026-09-12T10:05:00Z"
}
```

**Errors:**
| Code | Detail | Condition |
|------|--------|-----------|
| 401 | Missing authentication | No JWT |
| 404 | No active vote | User has no active vote in category |

### 3.3 GET /users/me/votes — List User's Votes

**Description:** Get all active votes for the authenticated user.

**Auth:** Required (JWT or API key)

**Response 200:**
```json
{
  "votes": [
    {
      "category_id": "uuid-of-category",
      "category_name": "Best Code Model",
      "target_type": "model",
      "target_id": "uuid-of-model",
      "target_name": "GPT-4",
      "weight": 1.0,
      "created_at": "2026-09-12T10:00:00Z",
      "updated_at": "2026-09-12T10:00:00Z"
    }
  ]
}
```

### 3.4 GET /models/{slug}/votes — Vote Count for Model

**Description:** Get total vote count and weighted score for a model.

**Auth:** Not required (public endpoint)

**Response 200:**
```json
{
  "model_id": "uuid-of-model",
  "total_votes": 42,
  "weighted_score": 38.5,
  "category_votes": [
    {
      "category_id": "uuid-of-category",
      "category_name": "Best Code Model",
      "votes": 15,
      "weighted_score": 14.2
    }
  ]
}
```

## 4. Request/Response Schemas

### VoteRequest
```python
class VoteRequest(BaseModel):
    target_type: Literal["model", "orchestrator"]
    target_id: str  # UUID
    category_id: str  # UUID
    idempotency_key: str  # UUID or unique string, max 255 chars

    @validator("target_id", "category_id")
    def validate_uuid(cls, v):
        # Validate UUID format
        ...

    @validator("idempotency_key")
    def validate_idempotency_key(cls, v):
        if len(v) > 255:
            raise ValueError("idempotency_key must be <= 255 chars")
        return v
```

### VoteResponse
```python
class VoteResponse(BaseModel):
    id: str
    user_id: str
    target_type: str
    target_id: str
    category_id: str
    action: str
    weight: Decimal
    created_at: datetime
```

### UserVoteResponse
```python
class UserVoteItem(BaseModel):
    category_id: str
    category_name: str
    target_type: str
    target_id: str
    target_name: str
    weight: Decimal
    created_at: datetime
    updated_at: datetime

class UserVotesResponse(BaseModel):
    votes: list[UserVoteItem]
```

### ModelVoteResponse
```python
class CategoryVoteCount(BaseModel):
    category_id: str
    category_name: str
    votes: int
    weighted_score: Decimal

class ModelVotesResponse(BaseModel):
    model_id: str
    total_votes: int
    weighted_score: Decimal
    category_votes: list[CategoryVoteCount]
```

## 5. Rate Limiting

- **Authenticated users:** 60 req/min per RG-01
- **Vote endpoints:** Additional per-user limit of 30 req/min
- **Headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`

## 6. Non-Functional Requirements

- **Versioning:** All endpoints under `/api/v1/` (RG-33)
- **Idempotency:** POST /votes supports idempotency keys (RG-29)
- **Performance:** All endpoints MUST respond in < 200ms (p95)

## Artifact
- **Path:** `openspec/changes/voting/specs/spec-05-vote-api.md`
- **Next:** `sdd-design` — create technical design with sequence diagrams
