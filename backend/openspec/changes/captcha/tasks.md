# Tasks: HU-A08 — CAPTCHA Turnstile Integration

## Phase 1: Backend Infrastructure

### 1.1 Create Turnstile Middleware
- [x] Create `app/auth/middleware/turnstile.py`
- [x] Implement `TurnstileConfig` class
- [x] Implement `TurnstileMiddleware` dependency
- [x] Add token extraction from request body
- [x] Add Cloudflare verification
- [x] Add AuditLog integration

### 1.2 Create Burst Detection Service
- [x] Create `app/voting/services/burst_detection.py`
- [x] Implement `BurstDetector` class
- [x] Implement `is_burst()` method
- [x] Implement `record_vote()` method
- [x] Add Redis sliding window

### 1.3 Create Feature Flag Service
- [x] Create `app/core/feature_flags.py`
- [x] Implement `FeatureFlags` class
- [x] Implement `is_enabled()` method
- [x] Add PostHog integration

### 1.4 Update Configuration
- [x] Add Turnstile config to `app/core/config.py`
- [x] Add PostHog config to `app/core/config.py`
- [x] Add feature flag names to config

## Phase 2: Registration Integration

### 2.1 Update Registration Schema
- [x] Add `turnstile_token` field to `VoteRequest`
- [x] Make `turnstile_token` required when feature flag enabled

### 2.2 Update Registration Endpoint
- [x] Add Turnstile middleware to OAuth callback
- [x] Verify token before creating account
- [x] Log verification result to AuditLog

### 2.3 Update Registration Tests
- [x] Add test for successful registration with Turnstile
- [x] Add test for failed registration without token
- [x] Add test for failed registration with invalid token
- [x] Add test for registration with feature flag disabled

## Phase 3: Voting Integration

### 3.1 Update Voting Schema
- [x] Add `turnstile_token` field to `VoteRequest`
- [x] Make `turnstile_token` required when triggered

### 3.2 Update Voting Service
- [x] Add burst detection check
- [x] Add first vote detection
- [x] Add Turnstile verification when triggered

### 3.3 Update Voting Endpoint
- [x] Add Turnstile middleware to `POST /voting/votes`
- [x] Verify token when burst or first vote detected
- [x] Log verification result to AuditLog

### 3.4 Update Voting Tests
- [x] Add test for vote without Turnstile (normal)
- [x] Add test for first vote with Turnstile
- [x] Add test for burst vote with Turnstile
- [x] Add test for failed verification

## Phase 4: Frontend Integration

### 4.1 Create Turnstile Component
- [x] Create `src/components/auth/TurnstileWidget.tsx`
- [x] Implement Cloudflare Turnstile widget
- [x] Add token callback

### 4.2 Update Registration Form
- [x] Add TurnstileWidget to OAuthButton
- [x] Pass token to registration API

### 4.3 Update Voting UI
- [ ] Add TurnstileWidget to vote button
- [ ] Show widget on first vote
- [ ] Show widget on burst detection

### 4.4 Update Frontend Tests
- [ ] Add test for Turnstile widget rendering
- [ ] Add test for token passing

## Phase 5: Audit & Monitoring

### 5.1 Update AuditLog
- [x] Add `captcha_failed` action type
- [x] Add `captcha_success` action type
- [x] Add `burst_detected` action type

### 5.2 Add Monitoring
- [ ] Add Turnstile verification metrics
- [ ] Add burst detection metrics
- [ ] Add feature flag metrics

### 5.3 Add Alerting
- [ ] Alert on high failure rate
- [ ] Alert on high latency
- [ ] Alert on burst detection spikes

## Phase 6: Documentation

### 6.1 Update API Documentation
- [ ] Document Turnstile token field
- [ ] Document feature flags
- [ ] Document error responses

### 6.2 Update User Documentation
- [ ] Document CAPTCHA behavior
- [ ] Document feature flag rollout
- [x] Add `turnstile_token` field to `VoteRequest`
- [x] Make `turnstile_token` required when triggered

### 3.2 Update Voting Service
- [x] Add burst detection check
- [x] Add first vote detection
- [x] Add Turnstile verification when triggered

### 3.3 Update Voting Endpoint
- [x] Add Turnstile middleware to `POST /voting/votes`
- [x] Verify token when burst or first vote detected
- [x] Log verification result to AuditLog

### 3.4 Update Voting Tests
- [x] Add test for vote without Turnstile (normal)
- [x] Add test for first vote with Turnstile
- [x] Add test for burst vote with Turnstile
- [x] Add test for failed verification

## Phase 4: Frontend Integration

### 4.1 Create Turnstile Component
- [ ] Create `src/components/auth/TurnstileWidget.tsx`
- [ ] Implement Cloudflare Turnstile widget
- [ ] Add token callback

### 4.2 Update Registration Form
- [ ] Add TurnstileWidget to registration form
- [ ] Pass token to registration API

### 4.3 Update Voting UI
- [ ] Add TurnstileWidget to vote button
- [ ] Show widget on first vote
- [ ] Show widget on burst detection

### 4.4 Update Frontend Tests
- [ ] Add test for Turnstile widget rendering
- [ ] Add test for token passing

## Phase 5: Audit & Monitoring

### 5.1 Update AuditLog
- [x] Add `captcha_failed` action type
- [x] Add `captcha_success` action type
- [x] Add `burst_detected` action type

### 5.2 Add Monitoring
- [ ] Add Turnstile verification metrics
- [ ] Add burst detection metrics
- [ ] Add feature flag metrics

### 5.3 Add Alerting
- [ ] Alert on high failure rate
- [ ] Alert on high latency
- [ ] Alert on burst detection spikes

## Phase 6: Documentation

### 6.1 Update API Documentation
- [ ] Document Turnstile token field
- [ ] Document feature flags
- [ ] Document error responses

### 6.2 Update User Documentation
- [ ] Document CAPTCHA behavior
- [ ] Document feature flag rollout

## Dependencies

```
1.1 → 2.1, 3.1
1.2 → 3.2
1.3 → 2.2, 3.3
1.4 → 1.1, 1.3
2.1 → 2.2
2.2 → 2.3
3.1 → 3.2
3.2 → 3.3
3.3 → 3.4
4.1 → 4.2, 4.3
4.2 → 4.4
4.3 → 4.4
5.1 → 2.2, 3.3
5.2 → 5.3
```

## Risk Assessment

| Task | Risk | Mitigation |
|------|------|------------|
| 1.1 | Medium | Use existing anti_bot.py patterns |
| 1.2 | Low | Simple Redis sliding window |
| 1.3 | Low | PostHog SDK is well-documented |
| 2.2 | Medium | Feature flag allows gradual rollout |
| 3.2 | Medium | Burst detection thresholds tunable |
| 4.1 | Low | Turnstile widget is simple |
| 5.1 | Low | AuditLog already exists |

## Success Criteria

- [ ] All tasks completed
- [ ] All tests passing
- [ ] Feature flags configured
- [ ] Documentation updated
- [ ] Monitoring in place
- [ ] Rollout plan documented
