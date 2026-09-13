# Proposal: HU-T11 — Filter Orchestrators by Category

## Epic
T — Taxonomy

## Sprint
0

## User Story
**As:** User or agent  
**I want:** To see orchestrators filtered by category  
**So that:** I can focus on the capability I'm interested in

## Acceptance Criteria
- `GET /api/v1/orchestrators?category=multi_agent` filters by category
- If category doesn't exist, returns `404`
- If category exists but no orchestrators, returns `200` with empty list
- Filter can be combined with search
- Response includes applied filters in metadata

## Scope
- Add category filtering to list_orchestrators
- Add OrchestratorCategory junction table
- Seed category associations

## Out of Scope
- Category admin API
- Category voting

## Approach
1. Add OrchestratorCategory junction table
2. Update list_orchestrators to filter by category
3. Seed category associations for example orchestrators

## Risks
- Need to handle 404 for non-existent categories

## Ready for Proposal
Yes
