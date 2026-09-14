# Spec: Vote Screen — Mobile App

## Requirements

### REQ-01: Display Vote Pair
**Priority**: MUST
**Description**: Show two models side-by-side for comparison voting.

**Given** user is on the Vote screen
**When** the screen loads
**Then** two random models from the selected category are displayed
**And** each model shows name, provider, avatar, context size, and price
**And** ELO badge is displayed for each model

### REQ-02: Category Selection
**Priority**: MUST
**Description**: Allow user to switch between categories.

**Given** user is on the Vote screen
**When** user taps a category chip
**Then** the category changes
**And** a new pair of models is loaded from `GET /api/v1/models?category={cat}`
**And** progress counter updates

### REQ-03: Cast Vote
**Priority**: MUST
**Description**: User can vote for one of the two models.

**Given** two models are displayed
**When** user taps "Vote" button on a model
**Then** `POST /voting/votes` is called with `{ event_id, model_slug, vote_type: "upvote" }`
**And** a success toast is shown
**And** a new pair is loaded

### REQ-04: Skip Vote
**Priority**: SHOULD
**Description**: User can skip the current pair without voting.

**Given** two models are displayed
**When** user taps "Skip" button
**Then** no API call is made
**And** a new pair is loaded
**And** skip count is tracked locally

### REQ-05: Don't Know
**Priority**: SHOULD
**Description**: User can indicate they don't know enough to vote.

**Given** two models are displayed
**When** user taps "Don't Know" button
**Then** no API call is made
**And** a new pair is loaded

### REQ-06: Progress Indicator
**Priority**: SHOULD
**Description**: Show voting progress within the daily session.

**Given** user is voting
**When** votes are cast
**Then** progress bar updates
**And** counter shows "X / 50" format

### REQ-07: Error Handling
**Priority**: MUST
**Description**: Handle API errors gracefully.

**Given** API call fails
**When** error occurs
**Then** error toast is shown
**And** user can retry the action

### REQ-08: Loading State
**Priority**: SHOULD
**Description**: Show skeleton while loading models.

**Given** models are being fetched
**When** API call is in progress
**Then** skeleton loader is displayed
**And** no interaction is possible until loaded

## API Endpoints Used
- `GET /api/v1/models?category={cat}&limit=100` — Fetch models for category
- `POST /voting/votes` — Cast vote
- `GET /api/v1/meta` — Get categories list

## Mockup Reference
- `mobile/mockups/screens/vote.html`
- `mobile/mockups/components/vote-card.html`
- `mobile/mockups/components/chip.html`
