# Spec: Rankings Screen — Mobile App

## Requirements

### REQ-01: Display Rankings List
**Priority**: MUST
**Description**: Show models ranked by ELO in the selected category.

**Given** user is on the Rankings screen
**When** the screen loads
**Then** models are fetched from `GET /voting/rankings?category={cat}`
**And** each item shows rank number, avatar, name, provider, ELO, and delta

### REQ-02: Category Tabs
**Priority**: MUST
**Description**: Allow switching between categories.

**Given** user is on the Rankings screen
**When** user taps a category tab
**Then** rankings are fetched for the new category
**And** list updates with new data

### REQ-03: ELO Display
**Priority**: MUST
**Description**: Show ELO rating with tier color.

**Given** rankings are displayed
**When** ELO is shown
**Then** tier color is applied (Elite/Strong/Average/Emerging)
**And** 7-day trend delta is shown (+/-)

### REQ-04: Model Detail
**Priority**: SHOULD
**Description**: Tap on model to see details.

**Given** rankings list is displayed
**When** user taps a model item
**Then** `GET /api/v1/models/{slug}` is called
**And** model detail modal/sheet is shown

### REQ-05: Pull to Refresh
**Priority**: SHOULD
**Description**: Allow refreshing rankings data.

**Given** rankings are displayed
**When** user pulls down
**Then** rankings are re-fetched from API
**And** loading indicator is shown

### REQ-06: Empty State
**Priority**: SHOULD
**Description**: Show empty state when no rankings exist.

**Given** no rankings for category
**When** screen loads
**Then** empty state component is displayed
**And** message says "No votes in this category yet"

### REQ-07: Error Handling
**Priority**: MUST
**Description**: Handle API errors gracefully.

**Given** API call fails
**When** error occurs
**Then** error state is shown
**And** retry button is available

## API Endpoints Used
- `GET /voting/rankings?category={cat}` — Get rankings
- `GET /api/v1/models/{slug}` — Get model details
- `GET /api/v1/meta` — Get categories list

## Mockup Reference
- `mobile/mockups/screens/rankings.html`
- `mobile/mockups/components/elo-badge.html`
