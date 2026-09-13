# Tasks: HU-A09 — API Keys for Agents (Read-Only)

## Phase 1: Model & Schema Updates

### 1.1 Update APIKey Model
- [x] Add last_used_at field (nullable datetime)
- [x] Add expires_at field (nullable datetime)

### 1.2 Update Schemas
- [x] Add last_used_at to APIKeyRead
- [x] Add expires_at to APIKeyRead
- [x] Add expires_at to APIKeyCreate

### 1.3 Update API Routes
- [x] Update _to_read to include new fields
- [x] Update create_api_key to set expires_at
- [x] Update require_api_key to check expiration
- [x] Update require_api_key to track last_used_at

## Phase 2: Voting Protection

### 2.1 Block API Keys from Voting
- [x] Add API key check to cast_or_change_vote
- [x] Add API key check to revoke_vote
- [x] Return 403 with clear error message

## Phase 3: Tests

### 3.1 Backend Tests
- [x] Test APIKey model has new fields
- [x] Test APIKeyRead schema includes new fields
- [x] Test APIKeyCreate schema allows expires_at
- [x] Test read scopes are allowed
- [x] Test write scopes are rejected
- [x] Test admin scopes are rejected
- [x] Test vote blocks API key
- [x] Test revoke vote blocks API key
