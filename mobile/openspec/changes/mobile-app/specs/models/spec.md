# Spec: Models Screen — Mobile App

## Requirements

### REQ-01: Display Models List
**Priority**: MUST
**Description**: Show all approved models in a browsable list.

**Given** user is on the Models screen
**When** the screen loads
**Then** models are fetched from `GET /api/v1/models`
**And** each item shows avatar, name, provider, tags, and ELO

### REQ-02: Search Models
**Priority**: MUST
**Description**: Allow searching models by name or provider.

**Given** user is on the Models screen
**When** user types in search input
**Then** `GET /api/v1/models?search={query}` is called
**And** list filters in real-time

### REQ-03: Provider Filter
**Priority**: SHOULD
**Description**: Filter models by provider.

**Given** models list is displayed
**When** user taps a provider tab
**Then** `GET /api/v1/models?provider={prov}` is called
**And** list shows only models from that provider

### REQ-04: Model Detail
**Priority**: MUST
**Description**: View full model details.

**Given** models list is displayed
**When** user taps a model item
**Then** `GET /api/v1/models/{slug}` is called
**And** detail modal/sheet shows:
- Name, provider, avatar
- Context size
- Price per million tokens
- ELO rating with tier
- Categories/modalities
- Description

### REQ-05: Compare Models
**Priority**: SHOULD
**Description**: Select multiple models to compare.

**Given** models list is displayed
**When** user selects 2+ models
**Then** `GET /api/v1/models/compare?slugs={s1}&slugs={s2}` is called
**And** comparison view is shown

### REQ-06: Loading State
**Priority**: SHOULD
**Description**: Show skeleton while loading.

**Given** models are being fetched
**When** API call is in progress
**Then** skeleton loader is displayed

### REQ-07: Empty State
**Priority**: SHOULD
**Description**: Show empty state when no models match.

**Given** search returns no results
**When** list is empty
**Then** empty state component is displayed
**And** message says "No models match your search"

### REQ-08: Error Handling
**Priority**: MUST
**Description**: Handle API errors gracefully.

**Given** API call fails
**When** error occurs
**Then** error state is shown
**And** retry button is available

## API Endpoints Used
- `GET /api/v1/models` — List models with filters
- `GET /api/v1/models/{slug}` — Get model details
- `GET /api/v1/models/compare` — Compare models
- `GET /api/v1/meta` — Get categories, providers, modalities

## Mockup Reference
- `mobile/mockups/screens/models.html`
- `mobile/mockups/components/card.html`
