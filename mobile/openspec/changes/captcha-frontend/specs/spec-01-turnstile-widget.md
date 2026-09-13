# Spec: Frontend TurnstileWidget — HU-A08

## Requirements

### REQ-01: TurnstileWidget Component
**Priority**: MUST
**Description**: Reusable component wrapping Cloudflare Turnstile.

**Given** the component is rendered
**When** Turnstile loads
**Then** widget must be invisible or managed mode
**And** token must be returned via callback

### REQ-02: Registration Integration
**Priority**: MUST
**Description**: Widget appears before OAuth redirect.

**Given** user is on registration page
**When** they click "Sign up with Google/GitHub"
**Then** Turnstile widget must be visible
**And** token must be captured before redirect

### REQ-03: Voting Integration
**Priority**: MUST
**Description**: Widget appears on first vote or burst detection.

**Given** user clicks vote button
**When** backend requires CAPTCHA (first vote or burst)
**Then** widget must appear inline
**And** token must be sent with vote request

### REQ-04: Error Handling
**Priority**: SHOULD
**Description**: Graceful handling of Turnstile failures.

**Given** Turnstile fails to load
**When** user tries to proceed
**Then** error message must be displayed
**And** retry option must be available

## Non-Functional Requirements

### NFR-01: Performance
- Widget must load in < 1s
- Token refresh must be silent

### NFR-02: Accessibility
- Widget must be keyboard navigable
- Screen reader must announce widget presence

### NFR-03: UX
- Widget must not block user flow
- Invisible mode preferred, managed as fallback
