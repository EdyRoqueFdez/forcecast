# Proposal: HU-A03 — Email Verification

## Summary
Implement email verification flow to confirm user identity and unlock voting.

## Problem
Users can vote without verifying their email, allowing fake accounts and bots.

## Solution
Send verification email on registration, block voting until verified.

## Scope

### In Scope
- Email verification token generation
- Verification email sending (Resend)
- Verification endpoint
- Rate limiting for resend (3/hour)
- Voting gate (email_verified check)

### Out of Scope
- Custom email templates (use defaults)
- SMS verification
- Social provider email verification

## Success Criteria
- [ ] Verification email sent on registration
- [ ] Token expires in 24h
- [ ] Voting blocked until verified
- [ ] Resend limited to 3/hour
- [ ] Verification sets email_verified = true
