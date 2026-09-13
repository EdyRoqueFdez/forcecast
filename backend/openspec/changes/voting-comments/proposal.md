# Proposal: HU-V03 — Comment with Vote

## Epic
V — Voting & Opinions

## Sprint
2

## User Story
**As:** Authenticated user  
**I want:** To attach a comment to my vote  
**So that:** I can explain why I chose that model/orchestrator

## Acceptance Criteria
- Comment is optional
- Length: 0-1000 characters
- Supports plain text (optional basic markdown)
- Saved associated with VoteEvent
- Can edit comment while vote is active
- Comment inherits profile privacy level (pseudonym or public)
- Moderation applied (reports and spam detection)
- Edits logged in AuditLog

## Scope
- Add comment field to vote endpoints
- Add comment editing endpoint
- Add comment validation

## Out of Scope
- Full markdown rendering
- Real-time comment updates
- Comment threading

## Approach
1. Add comment field to VoteRequest schema
2. Add comment field to vote_event model
3. Add edit comment endpoint
4. Add comment validation (length, content)

## Risks
- Need to handle comment editing carefully
- Need to maintain audit trail

## Ready for Proposal
Yes
