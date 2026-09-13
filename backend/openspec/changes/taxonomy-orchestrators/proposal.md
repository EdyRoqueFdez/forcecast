# Proposal: HU-T08 — List Orchestrators

## Epic
T — Taxonomy

## Sprint
0

## User Story
**As:** User or agent  
**I want:** To see available orchestrators  
**So that:** I can vote or query rankings for orchestrators

## Acceptance Criteria
- `GET /api/v1/orchestrators` returns only orchestrators with `status=approved`
- Each item includes: `slug`, name, description, `maintainer`, associated providers, `website`, `repo_url`, version, `status`
- Includes examples: gentle-orchestrator, LangChain, LlamaIndex, AutoGen, CrewAI, Semantic Kernel, Haystack, DSPy
- Paginated, sorted by name
- Descriptions translated to EN, ES, PT, FR, ZH
- Cached with configurable TTL, default 60 seconds

## Scope
- New Orchestrator entity with translations
- New OrchestratorProvider association
- Public API endpoint with pagination, i18n, caching
- Seed data for examples

## Out of Scope
- Orchestrator detail endpoint (HU-T09)
- Orchestrator categories (HU-T10)
- Orchestrator voting (Voting module)
- Admin API for orchestrators

## Approach
1. Add Orchestrator, OrchestratorTranslation, OrchestratorProvider models
2. Add repository for orchestrator queries
3. Add public API endpoint with patterns from existing taxonomy API
4. Seed with example orchestrators

## Risks
- Need to create new database tables
- Migration required
- Need to maintain consistency with existing taxonomy patterns

## Ready for Proposal
Yes
