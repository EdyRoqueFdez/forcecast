# Proposal: HU-A08 — CAPTCHA Turnstile Integration

## Summary
Integrate Cloudflare Turnstile CAPTCHA at critical points to prevent bots and automated votes.

## Problem
Currently, the Turnstile verification service exists but is not integrated into any endpoints. Bots could:
- Create multiple accounts
- Submit automated votes
- Manipulate rankings

## Solution
Integrate Turnstile at:
1. **Registration** — verify human before account creation
2. **First vote** — verify human before first vote
3. **Burst votes** — verify human when detecting rapid voting pattern

## Scope
### In Scope
- Backend: Turnstile middleware for registration and voting
- Backend: Feature flag integration (PostHog)
- Backend: AuditLog for failed verifications
- Frontend: Turnstile widget on affected forms

### Out of Scope
- hCaptcha (future option)
- Mobile native CAPTCHA (uses same API)
- Admin panel CAPTCHA settings

## Technical Approach
1. Create `TurnstileMiddleware` dependency
2. Add `turnstile_token` field to registration/voting schemas
3. Integrate PostHog feature flag checks
4. Log failures to AuditLog

## Risk Assessment
- **Low risk**: Turnstile is invisible/minimal for normal users
- **Medium risk**: Feature flag misconfiguration could block all users
- **Mitigation**: Feature flag defaults to disabled, gradual rollout

## Success Criteria
- [ ] Turnstile widget appears on registration
- [ ] Turnstile widget appears on first vote
- [ ] Failed verification blocks action
- [ ] Failed verification logged to AuditLog
- [ ] Feature flag controls rollout
- [ ] Normal users see no visible CAPTCHA
