# Proposal: HU-V06 — Model Ranking Endpoint

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** User or agent  
**I want:** To see aggregated model rankings by category  
**So that:** I can decide which model to use or recommend

## Acceptance Criteria
- `GET /api/v1/rankings/models?category=coding&lang=es` returns ranking
- Response includes: model, weighted votes, raw votes, percentage of total, trend (7d/30d), confidence, sample_size, taxonomy_version
- Only models with minimum votes (default 5) appear
- Results sorted by weighted votes descending
- Response includes `locale_used`
- Results cached for 5 minutes
- Results are paginated

## Scope
- New ranking service for aggregating votes
- New public API endpoint
- Caching with 5-minute TTL

## Out of Scope
- Real-time ranking updates
- Ranking visualization
- Ranking export

## Approach
1. Create RankingService for vote aggregation
2. Add GET /api/v1/rankings/models endpoint
3. Implement caching with 5-minute TTL
4. Add pagination support

## Risks
- Need to handle large vote datasets efficiently
- Need to calculate confidence scores

## Ready for Proposal
Yes
