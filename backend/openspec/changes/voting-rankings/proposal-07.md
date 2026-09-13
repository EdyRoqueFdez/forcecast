# Proposal: HU-V07 — Orchestrator Ranking Endpoint

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** User or agent  
**I want:** To see aggregated orchestrator rankings by category  
**So that:** I can decide which orchestrator to use

## Acceptance Criteria
- `GET /api/v1/rankings/orchestrators?category=multi_agent&lang=es` returns ranking
- Same rules as HU-V06 but for orchestrators
- Rankings independent from model rankings
- Optional combined endpoint: `GET /api/v1/rankings?scope=all`

## Scope
- Add orchestrator ranking to RankingService
- Add GET /api/v1/rankings/orchestrators endpoint

## Out of Scope
- Combined ranking endpoint (optional future)

## Approach
1. Extend RankingService with get_orchestrator_ranking
2. Add GET /api/v1/rankings/orchestrators endpoint

## Risks
- Need to handle orchestrator-specific categories

## Ready for Proposal
Yes
