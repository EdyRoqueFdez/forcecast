# Proposal: HU-V10 — Vote History Endpoint

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** Authenticated user  
**I want:** To see all my votes and changes  
**So that:** I can audit my own contribution

## Acceptance Criteria
- `GET /api/v1/me/votes/history` returns my vote history
- Each entry shows VoteEvent with timestamp, type, previous target, new target, category, comment
- Filter by category, target, date, type
- Paginated results
- Export to JSON or CSV

## Scope
- Vote history endpoint
- Filtering and pagination
- Export functionality

## Out of Scope
- Other users' history (future)

## Approach
1. Add GET /api/v1/me/votes/history endpoint
2. Support query parameters for filtering
3. Add export endpoint

## Risks
- Need to handle large histories efficiently

## Ready for Proposal
Yes
