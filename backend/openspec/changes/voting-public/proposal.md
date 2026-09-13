# Proposal: HU-V11 — View Other User's Public Votes

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** Authenticated user  
**I want:** To see public votes of other users  
**So that:** I can learn from community leaders

## Acceptance Criteria
- Only show votes if target profile is public
- `GET /api/v1/users/{username}/votes` returns authorized votes
- No private data exposed (email, IP, device)
- Respects privacy settings

## Scope
- Public votes endpoint
- Privacy checks

## Out of Scope
- Private profile viewing (future)

## Approach
1. Add GET /api/v1/users/{username}/votes endpoint
2. Check if profile is public before returning votes
3. Filter out sensitive data

## Risks
- Need to handle privacy settings properly

## Ready for Proposal
Yes
