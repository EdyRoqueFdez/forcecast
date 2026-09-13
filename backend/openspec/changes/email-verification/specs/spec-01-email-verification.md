# Spec: HU-A03 — Email Verification

## Requirements

### REQ-01: Verification Email on Registration
**Priority**: MUST
**Description**: Send verification email when user registers.

**Given** user completes registration
**When** account is created
**Then** verification email must be sent
**And** email must contain verification link with token
**And** token must expire in 24 hours

### REQ-02: Voting Gate
**Priority**: MUST
**Description**: Block voting until email is verified.

**Given** user is authenticated
**When** user tries to vote
**Then** check email_verified status
**And** if not verified, reject with 403
**And** response must indicate email verification required

### REQ-03: Resend Email
**Priority**: MUST
**Description**: Allow resending verification email with rate limiting.

**Given** user requests resend
**When** rate limit not exceeded
**Then** send new verification email
**And** invalidate previous token

**Given** rate limit exceeded
**When** user requests resend
**Then** reject with 429
**And** response must include retry-after

### REQ-04: Verify Email
**Priority**: MUST
**Description**: Verify email when user clicks link.

**Given** user clicks verification link
**When** token is valid and not expired
**Then** set email_verified = true
**And** set email_verified_at timestamp
**And** redirect to success page

### REQ-05: Expired Token
**Priority**: SHOULD
**Description**: Handle expired tokens gracefully.

**Given** user clicks verification link
**When** token is expired
**Then** show error message
**And** offer to resend verification email

## Non-Functional Requirements

### NFR-01: Security
- Tokens must be cryptographically random
- Tokens must be single-use
- Tokens must expire in 24 hours

### NFR-02: Deliverability
- Emails must pass SPF/DKIM
- Must include unsubscribe link
- Must include physical address

### NFR-03: Performance
- Email sending must be async
- Verification must complete in < 1s
