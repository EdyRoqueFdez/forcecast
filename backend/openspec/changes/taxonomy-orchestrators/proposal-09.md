# Proposal: HU-T09 — View Orchestrator Details

## Epic
T — Taxonomy

## Sprint
0

## User Story
**As:** User or agent  
**I want:** To see full orchestrator information  
**So that:** I can decide whether to use or vote for it

## Acceptance Criteria
- `GET /api/v1/orchestrators/{slug}` returns: name, description, `maintainer`, version, license, `website`, `repo_url`, associated providers, categories, `locale_used`
- If slug not found, returns `404`
- Does not expose orchestrators in `pending_review`, `rejected`, or `deprecated` status
- An orchestrator can relate to one or more providers

## Scope
- Detail endpoint for orchestrators
- Include providers and categories
- i18n support

## Out of Scope
- Orchestrator voting (Voting module)
- Admin API for orchestrators

## Approach
1. Add `get_orchestrator(slug, locale)` to PublicService
2. Add `GET /api/v1/orchestrators/{slug}` endpoint
3. Include providers and categories in response

## Risks
- Need to handle 404 correctly
- Need to include categories (may need Category join)

## Ready for Proposal
Yes
