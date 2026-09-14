# Spec: Profile Screen — Mobile App

## Requirements

### REQ-01: Display User Profile
**Priority**: MUST
**Description**: Show user profile information.

**Given** user is on the Profile screen
**When** the screen loads
**Then** `GET /auth/me` is called
**And** profile shows: name, email, avatar, member since, role

### REQ-02: Display Stats
**Priority**: MUST
**Description**: Show user statistics.

**Given** profile is loaded
**When** stats are displayed
**Then** three stat cards show:
- Votes cast (from `GET /voting/me/votes` total count)
- Categories voted (calculated from votes)
- Day streak (calculated from consecutive voting days)

### REQ-03: Recent Votes
**Priority**: SHOULD
**Description**: Show recent voting history.

**Given** user is on Profile screen
**When** recent votes section loads
**Then** `GET /voting/me/votes?limit=10` is called
**And** each item shows: model pair, category, timestamp, winner

### REQ-04: Edit Profile
**Priority**: SHOULD
**Description**: Allow editing display name and bio.

**Given** user is on Profile screen
**When** user taps edit button
**Then** edit form is shown
**And** user can update display name and bio
**And** `PATCH /auth/me` is called on save

### REQ-05: Theme Toggle
**Priority**: SHOULD
**Description**: Allow changing theme from profile.

**Given** user is on Profile screen
**When** user taps theme toggle
**Then** theme cycles through: dark → light → jedi-dark → jedi-light
**And** preference is saved locally

### REQ-06: Language Toggle
**Priority**: SHOULD
**Description**: Allow changing language.

**Given** user is on Profile screen
**When** user taps language toggle
**Then** language switches between EN/ES
**And** all text updates immediately

### REQ-07: Sign Out
**Priority**: MUST
**Description**: Allow user to sign out.

**Given** user is on Profile screen
**When** user taps "Sign Out"
**Then** `POST /auth/logout` is called
**And** tokens are cleared from storage
**And** user is redirected to login screen

### REQ-08: Auth Guard
**Priority**: MUST
**Description**: Redirect to login if not authenticated.

**Given** user is not authenticated
**When** Profile screen loads
**Then** user is redirected to login screen

### REQ-09: Loading State
**Priority**: SHOULD
**Description**: Show skeleton while loading.

**Given** profile is being fetched
**When** API call is in progress
**Then** skeleton loader is displayed

### REQ-10: Error Handling
**Priority**: MUST
**Description**: Handle API errors gracefully.

**Given** API call fails
**When** error occurs
**Then** error state is shown
**And** retry button is available

## API Endpoints Used
- `GET /auth/me` — Get current user
- `PATCH /auth/me` — Update profile
- `GET /voting/me/votes` — Get vote history
- `POST /auth/logout` — Logout

## Mockup Reference
- `mobile/mockups/screens/profile.html`
- `mobile/mockups/components/avatar.html`
