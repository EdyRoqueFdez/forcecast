# Tasks: HU-A07 — Base Reputation System

## Phase 1: Backend Infrastructure

### 1.1 Create Reputation Service
- [x] Create `app/auth/services/reputation.py`
- [x] Implement tenure_score calculation
- [x] Implement votes_score calculation
- [x] Implement consistency_score calculation
- [x] Implement reports_penalty calculation
- [x] Implement get_vote_weight method
- [x] Implement is_bot_like method

### 1.2 Update User Model
- [x] Change default reputation_score to 1.0
- [x] Update comment to reflect HU-A07

## Phase 2: Anti-Bot Integration

### 2.1 Update Anti-Bot Service
- [x] Update STRICT_THRESHOLD to 0.5
- [x] Add comment for HU-A07

## Phase 3: Tests

### 3.1 Backend Tests
- [x] Test tenure_score calculation
- [x] Test votes_score calculation
- [x] Test consistency_score calculation
- [x] Test reports_penalty calculation
- [x] Test vote weight calculation
- [x] Test bot detection
- [x] Test is_strict_mode integration

## Phase 4: Documentation

### 4.1 Update API Documentation
- [ ] Document reputation formula
- [ ] Document vote weight calculation
