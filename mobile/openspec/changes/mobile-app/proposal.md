# Proposal: Forcecast Mobile App — React Native Expo

## Summary

Build a production React Native Expo app that replicates the mobile mockups and connects every interaction to the real Forcecast backend API. The app must work offline-first with cached data and sync when online.

## Problem

Forcecast has a working web frontend and backend API, but no native mobile app. Users need a fast, native experience for voting on AI models, viewing rankings, and managing their profile — all connected to the real backend.

## Solution

Create a React Native Expo app with:
- 4 main screens: Vote, Rankings, Models, Profile
- Every button connected to the backend API
- Offline-first with cached data
- Theme switching (dark/light × emerald/jedi)
- i18n (EN/ES)

## Scope

### In Scope
- Expo Router for navigation
- All 4 screens from mockups
- API integration for all endpoints
- Auth flow (OAuth + email)
- Theme system (4 themes)
- i18n (EN/ES)
- Offline caching
- Error handling

### Out of Scope
- Push notifications (future)
- Deep linking (future)
- App Store submission (future)
- EAS Build configuration (future)

## Backend API Endpoints

### Models
- `GET /api/v1/models` — List models with filters
- `GET /api/v1/models/{slug}` — Get model details
- `GET /api/v1/models/compare` — Compare models
- `GET /api/v1/meta` — Get categories, providers, modalities

### Auth
- `POST /auth/register` — Register with email
- `POST /auth/login` — Login with email
- `POST /auth/refresh` — Refresh access token
- `POST /auth/logout` — Logout
- `GET /auth/me` — Get current user
- `GET /auth/github` — OAuth GitHub
- `GET /auth/google` — OAuth Google

### Voting
- `POST /voting/votes` — Cast vote
- `DELETE /voting/votes` — Delete vote
- `GET /voting/me/votes` — Get my votes
- `GET /voting/events` — Get vote events
- `GET /voting/rankings` — Get rankings

### Taxonomy
- `GET /api/v1/providers` — List providers
- `GET /api/v1/categories` — List categories
- `GET /api/v1/models/approved` — List approved models

## Screen → API Mapping

### Vote Screen
| Button | API Call | Method |
|--------|----------|--------|
| Category chip | `GET /api/v1/models?category={cat}` | GET |
| Vote button | `POST /voting/votes` | POST |
| Skip button | No API call (next pair) | — |
| Don't Know | No API call (next pair) | — |

### Rankings Screen
| Button | API Call | Method |
|--------|----------|--------|
| Category tab | `GET /voting/rankings?category={cat}` | GET |
| Model item | `GET /api/v1/models/{slug}` | GET |

### Models Screen
| Button | API Call | Method |
|--------|----------|--------|
| Search input | `GET /api/v1/models?search={query}` | GET |
| Provider tab | `GET /api/v1/models?provider={prov}` | GET |
| Model item | `GET /api/v1/models/{slug}` | GET |

### Profile Screen
| Button | API Call | Method |
|--------|----------|--------|
| Load profile | `GET /auth/me` | GET |
| Recent votes | `GET /voting/me/votes` | GET |
| Sign out | `POST /auth/logout` | POST |

## Success Criteria
- [ ] App builds and runs on iOS/Android
- [ ] All 4 screens render correctly
- [ ] Every button triggers the correct API call
- [ ] Auth flow works (login/register/logout)
- [ ] Theme switching works (4 themes)
- [ ] i18n works (EN/ES)
- [ ] Offline caching works
- [ ] Error states display correctly

## Risks
- Backend API might have CORS issues for mobile
- OAuth redirect needs deep linking setup
- Token refresh logic needs careful handling
