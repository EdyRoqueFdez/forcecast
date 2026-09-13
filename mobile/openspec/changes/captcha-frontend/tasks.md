# Tasks: Frontend TurnstileWidget — HU-A08

## Phase 1: Setup

### 1.1 Install Dependencies
- [x] Install `@marsidev/react-turnstile`
- [x] Add `VITE_TURNSTILE_SITE_KEY` to `.env.example`

### 1.2 Create Component
- [x] Create `src/components/auth/TurnstileWidget.tsx`
- [x] Implement props interface
- [x] Add error boundary

## Phase 2: Registration Integration

### 2.1 Update Registration Page
- [x] Add TurnstileWidget to OAuthButton
- [x] Capture token state
- [x] Pass token to OAuth redirect

### 2.2 Update OAuth Flow
- [x] Add `turnstile_token` to OAuth URL params
- [x] Handle missing token error

### 2.3 Add Tests
- [ ] Test widget renders
- [ ] Test token capture
- [ ] Test OAuth redirect with token

## Phase 3: Voting Integration

### 3.1 Create VoteButton Component
- [x] Create `src/components/voting/VoteButton.tsx`
- [x] Add TurnstileWidget integration
- [x] Add first vote detection
- [x] Add burst detection hint

### 3.2 Update API Client
- [x] Add `turnstile_token` to createVote request
- [x] Handle 403 error (CAPTCHA required)

### 3.3 Add Tests
- [ ] Test widget shows on first vote
- [ ] Test widget shows on burst
- [ ] Test token sent with vote

## Phase 4: Error Handling

### 4.1 Add Error States
- [x] Handle Turnstile load failure
- [x] Handle token expiration
- [x] Show retry option

### 4.2 Add Accessibility
- [ ] Add aria-labels
- [ ] Add keyboard navigation
- [ ] Add screen reader announcements

## Phase 5: Documentation

### 5.1 Update Storybook
- [ ] Add TurnstileWidget stories
- [ ] Document props

### 5.2 Update README
- [ ] Document setup instructions
- [ ] Document environment variables
