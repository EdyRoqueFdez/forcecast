# Proposal: Frontend TurnstileWidget — HU-A08 CAPTCHA Integration

## Summary
Create a reusable Turnstile widget component and integrate it into registration and voting flows.

## Problem
Backend Turnstile verification is ready, but frontend has no widget to generate tokens.

## Solution
Create `TurnstileWidget` component using Cloudflare's `@marsidev/react-turnstile` library.

## Scope

### In Scope
- TurnstileWidget component
- Registration form integration (OAuth flow)
- Voting UI integration (first vote / burst detection)
- Token state management

### Out of Scope
- Backend changes (already done)
- Custom Turnstile themes (use defaults)
- Mobile native (same API)

## Technical Approach
1. Install `@marsidev/react-turnstile`
2. Create `TurnstileWidget` wrapper component
3. Add to registration page (before OAuth redirect)
4. Add to vote button (conditional display)

## Success Criteria
- [ ] Widget renders on registration
- [ ] Widget renders on first vote
- [ ] Token passed to backend
- [ ] Normal users see invisible/managed mode
