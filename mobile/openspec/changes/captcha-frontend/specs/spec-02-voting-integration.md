# Proposal: Voting UI Turnstile Integration — HU-A08

## Summary
Add TurnstileWidget to voting UI for first vote and burst detection scenarios.

## Problem
Backend requires Turnstile token for first votes and burst votes, but frontend has no UI to collect tokens.

## Solution
Create VoteButton component with conditional TurnstileWidget display.

## Scope

### In Scope
- VoteButton component with Turnstile integration
- First vote detection
- Burst detection (client-side hint)
- Token passing to API

### Out of Scope
- Backend changes (already done)
- New voting flows (existing API)

## Success Criteria
- [ ] Widget appears on first vote
- [ ] Widget appears on burst detection
- [ ] Token sent with vote request
- [ ] Error handling for failed verification
