# Tasks: HU-A03 — Email Verification

## Phase 1: Backend Infrastructure

### 1.1 Create Email Verification Service
- [x] Create `app/auth/services/email_verification.py`
- [x] Implement token generation
- [x] Implement token verification
- [x] Implement rate limiting (3/hour)

### 1.2 Create Email Service
- [x] Create `app/auth/services/email.py`
- [x] Implement Resend integration
- [x] Create verification email template

### 1.3 Create Verification Endpoints
- [x] Create `app/auth/api/verification.py`
- [x] Add GET `/auth/verify` endpoint
- [x] Add POST `/auth/resend-verification` endpoint

### 1.4 Update Configuration
- [x] Add Resend config to `app/core/config.py`
- [x] Add email verification config

## Phase 2: Registration Integration

### 2.1 Update Registration Flow
- [x] OAuth users auto-verified (email verified by provider)
- [x] Add email_verified_at field to User model

### 2.2 Update OAuth Flow
- [x] OAuth users marked as verified
- [x] Include verification router in main.py

## Phase 3: Voting Integration

### 3.1 Update Vote Service
- [x] Add email_verified check to `_validate_user`
- [x] Return appropriate error message

## Phase 4: Tests

### 4.1 Backend Tests
- [x] Test token generation
- [x] Test token verification
- [x] Test rate limiting
- [x] Test email sending

## Phase 5: Documentation

### 5.1 Update API Documentation
- [ ] Document verification endpoints
- [ ] Document error responses
