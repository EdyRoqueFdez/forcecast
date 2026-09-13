# Proposal: HU-A07 — Base Reputation System

## Summary
Implement reputation system that reflects user activity and affects vote weight.

## Problem
All users have equal voting power regardless of experience or trustworthiness.

## Solution
Calculate reputation from tenure, votes, consistency, and reports. Use reputation to weight votes.

## Scope

### In Scope
- Reputation calculation service
- Reputation update triggers
- Vote weight calculation
- Profile reputation display

### Out of Scope
- Complex ML-based reputation
- External reputation sources
- Reputation trading

## Success Criteria
- [ ] New users start with reputation 1.0
- [ ] Reputation updated on vote cast
- [ ] Reputation updated on account age
- [ ] Vote weight scales with reputation
- [ ] Low reputation users have reduced weight
- [ ] Reputation visible in profile
