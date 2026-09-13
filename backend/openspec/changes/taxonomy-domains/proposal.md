# Proposal: HU-T05 — List Problem Domains

## Epic
T — Taxonomy

## Sprint
0

## User Story
**As:** User or agent  
**I want:** To see available problem domains  
**So that:** I can classify problems in the correct category

## Acceptance Criteria
- `GET /api/v1/domains` returns active domains
- Base domains: `healthcare`, `travel`, `finance`, `legal`, `retail`, `education`, `logistics`, `other`
- Each domain includes: `slug`, translated name, description, optional subdomains
- Hierarchy is one level: domain to subdomain
- Versioned with independent TaxonomyVersion from models and orchestrators
- Supports i18n in EN, ES, PT, FR, ZH

## Scope
- New Domain, DomainTranslation models
- New TaxonomyVersion for domains
- Public API endpoint
- Seed data for base domains

## Out of Scope
- Domain admin API
- Domain voting

## Approach
1. Add Domain, DomainTranslation models
2. Add repository for domain queries
3. Add public API endpoint
4. Seed with base domains

## Risks
- Need separate TaxonomyVersion for domains
- Need to maintain independence from model/orchestrator versions

## Ready for Proposal
Yes
