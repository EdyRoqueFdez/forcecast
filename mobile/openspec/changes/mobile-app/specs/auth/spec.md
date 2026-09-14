# Spec: Auth Screen — Mobile App

## Requirements

### REQ-01: Login Form
**Priority**: MUST
**Description**: Allow user to login with email and password.

**Given** user is on Login screen
**When** user enters email and password
**Then** `POST /auth/login` is called
**And** tokens are stored securely
**And** user is redirected to Vote screen

### REQ-02: Register Form
**Priority**: MUST
**Description**: Allow user to register with email and password.

**Given** user is on Register screen
**When** user enters email, password, and name
**Then** `POST /auth/register` is called
**And** tokens are stored securely
**And** user is redirected to Vote screen

### REQ-03: OAuth GitHub
**Priority**: MUST
**Description**: Allow login with GitHub.

**Given** user is on Login screen
**When** user taps "Sign in with GitHub"
**Then** OAuth flow starts with `GET /auth/github`
**And** deep link handles callback
**And** tokens are stored

### REQ-04: OAuth Google
**Priority**: MUST
**Description**: Allow login with Google.

**Given** user is on Login screen
**When** user taps "Sign in with Google"
**Then** OAuth flow starts with `GET /auth/google`
**And** deep link handles callback
**And** tokens are stored

### REQ-05: Token Refresh
**Priority**: MUST
**Description**: Automatically refresh expired tokens.

**Given** access token is expired
**When** API call is made
**Then** `POST /auth/refresh` is called
**And** new tokens are stored
**And** original request is retried

### REQ-06: Secure Token Storage
**Priority**: MUST
**Description**: Store tokens securely on device.

**Given** user is authenticated
**When** tokens are received
**Then** tokens are stored in expo-secure-store
**And** refresh token is stored separately

### REQ-07: Error Handling
**Priority**: MUST
**Description**: Handle auth errors gracefully.

**Given** login/register fails
**When** error occurs
**Then** error message is shown
**And** form remains filled for retry

### REQ-08: Form Validation
**Priority**: SHOULD
**Description**: Validate form inputs before submission.

**Given** user fills form
**When** email is invalid or password too short
**Then** validation error is shown
**And** form is not submitted

## API Endpoints Used
- `POST /auth/login` — Login
- `POST /auth/register` — Register
- `GET /auth/github` — OAuth GitHub
- `GET /auth/google` — OAuth Google
- `POST /auth/refresh` — Refresh token
- `POST /auth/logout` — Logout

## Mockup Reference
- No direct mockup (auth flow not in mockups)
- Reference: `frontend/src/components/auth/`
