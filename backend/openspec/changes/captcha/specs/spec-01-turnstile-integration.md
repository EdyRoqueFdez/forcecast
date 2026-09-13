# Spec: HU-A08 — CAPTCHA Turnstile Integration

## Requirements

### REQ-01: Turnstile on Registration
**Priority**: MUST
**Description**: When a user registers, they must complete Turnstile verification.

**Given** a user is on the registration page
**When** they submit the registration form
**Then** Turnstile widget must be displayed
**And** the `turnstile_token` must be sent with the request
**And** the backend must verify the token before creating the account

### REQ-02: Turnstile on First Vote
**Priority**: MUST
**Description**: When a user casts their first vote, they must complete Turnstile verification.

**Given** a user is authenticated
**When** they cast their first vote (vote_count == 0)
**Then** Turnstile widget must be displayed
**And** the `turnstile_token` must be sent with the vote request
**And** the backend must verify the token before recording the vote

### REQ-03: Turnstile on Burst Votes
**Priority**: MUST
**Description**: When a user votes too rapidly, they must complete Turnstile verification.

**Given** a user is authenticated
**When** they cast votes within 10 seconds of each other (burst detection)
**Then** Turnstile widget must be displayed
**And** the `turnstile_token` must be sent with the vote request
**And** the backend must verify the token before recording the vote

### REQ-04: Failed Verification Blocks Action
**Priority**: MUST
**Description**: If Turnstile verification fails, the action must be blocked.

**Given** a user submits a request with an invalid Turnstile token
**When** the backend verifies the token
**Then** the request must be rejected with HTTP 403
**And** the response must include `"detail": "CAPTCHA verification failed"`

### REQ-05: AuditLog for Failures
**Priority**: MUST
**Description**: Failed Turnstile verifications must be logged.

**Given** a Turnstile verification fails
**When** the failure is processed
**Then** an AuditLog entry must be created with:
- `action`: "captcha_failed"
- `user_id` (if authenticated)
- `ip_address`
- `timestamp`
- `reason`: "turnstile_verification_failed"

### REQ-06: Feature Flag Control
**Priority**: SHOULD
**Description**: Turnstile integration must be controlled by a feature flag.

**Given** the feature flag `captcha_turnstile_enabled` is disabled
**When** a user registers or votes
**Then** Turnstile verification must be skipped

**Given** the feature flag `captcha_turnstile_enabled` is enabled
**When** a user registers or votes
**Then** Turnstile verification must be enforced

### REQ-07: Invisible/Minimal UX
**Priority**: SHOULD
**Description**: Turnstile must not disrupt normal user experience.

**Given** a user is a legitimate human
**When** they interact with Turnstile
**Then** the widget must be invisible or minimal (no visible challenge)
**And** the verification must complete in < 500ms

## Non-Functional Requirements

### NFR-01: Performance
- Turnstile verification must add < 100ms latency
- Feature flag check must be < 10ms

### NFR-02: Security
- Turnstile tokens must be verified server-side only
- Tokens must not be cached or reused
- Failed verifications must be rate-limited

### NFR-03: Observability
- All Turnstile verifications must be logged
- Failed verifications must be alertable
- Feature flag changes must be auditable

## Testing Strategy

### Unit Tests
- `test_turnstile_middleware_valid_token`
- `test_turnstile_middleware_invalid_token`
- `test_turnstile_middleware_missing_token`
- `test_turnstile_middleware_feature_flag_disabled`
- `test_burst_detection_logic`
- `test_first_vote_detection_logic`

### Integration Tests
- `test_registration_with_turnstile`
- `test_registration_without_turnstile_blocked`
- `test_first_vote_with_turnstile`
- `test_burst_vote_with_turnstile`
- `test_auditlog_on_failure`

### E2E Tests
- `test_registration_flow_with_turnstile`
- `test_voting_flow_with_turnstile`
