# Proposal: HU-T10 — List Orchestrator Categories

## Epic
T — Taxonomy

## Sprint
0

## User Story
**As:** User or agent  
**I want:** To see orchestrator-specific categories  
**So that:** I can vote and query orchestrator rankings by capability

## Acceptance Criteria
- `GET /api/v1/categories?scope=orchestrators` returns orchestrator categories
- Base categories: `multi_agent`, `tool_use`, `planning`, `memory`, `rag`, `workflow`, `evaluation`, `routing`, `observability`, `cost_optimization`
- Each category has independent `taxonomy_version` from model categories
- Translated to EN, ES, PT, FR, ZH
- One-level hierarchy

## Scope
- Add scope parameter to categories endpoint
- Seed orchestrator categories
- Independent taxonomy version

## Out of Scope
- Category admin API
- Category voting

## Approach
1. Add `scope` parameter to `GET /api/v1/categories`
2. Filter by taxonomy_version based on scope
3. Seed orchestrator categories

## Risks
- Need to maintain separate taxonomy versions for models and orchestrators

## Ready for Proposal
Yes
