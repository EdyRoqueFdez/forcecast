# Proposal: HU-V08 — Report Abusive Vote/Comment

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** Authenticated user  
**I want:** To report spam/abusive votes or comments  
**So that:** Ranking quality is maintained

## Acceptance Criteria
- `POST /api/v1/votes/report` with target_id, target_type, reason, details
- Reasons: spam, offensive, false, duplicate, other
- Creates Report with status `pending`
- Admin endpoint: `GET /api/v1/admin/votes/reports`
- Admin can approve/reject reports
- Confirmed reports reduce author reputation

## Scope
- Report model
- Report submission endpoint
- Admin review endpoints

## Out of Scope
- Auto-removal (future)
- Appeal process (future)

## Approach
1. Create Report model
2. Add POST /api/v1/votes/report endpoint
3. Add GET/PUT /api/v1/admin/votes/reports endpoints

## Risks
- Need to handle duplicate reports

## Ready for Proposal
Yes
