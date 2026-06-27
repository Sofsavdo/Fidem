# FIDEM 1.0 — PRD & Build Log

## Original Problem Statement
FIDEM — Telegram Mini App for serious dating, relationships and family-building. NOT Tinder, NOT Instagram, NOT a marriage agency. Premium matchmaking platform inside Telegram.

Tagline: "Sizga mos insonni xavfsiz topishga yordam beramiz."

## Architecture
- **Backend**: FastAPI + MongoDB (motor async) + JWT + Telegram WebApp HMAC + CLICK Merchant API + Emergent Object Storage + Telegram Bot webhook
- **Frontend**: React 19 + react-router v7 + Tailwind + shadcn/ui + sonner + axios. Mobile-first hybrid web + Telegram Mini App.
- **i18n**: 3 languages (uz/ru/en), auto-detect from Telegram/browser, persisted.

## Implementation Log

### Iteration 1 (2026-02-24) — MVP
- 40+ API endpoints across auth, profile, candidates, messages, photo-unlock, saved, gifts, leaderboard, verification, payments, notifications, referral, admin
- Backend startup auto-seeds 1 admin + 14 demo users
- JWT (email/password) + Telegram WebApp HMAC auth
- Match scoring with reasons
- CLICK pay-link + callback signature verification + admin-confirm fallback
- 10 frontend pages (Auth, Onboarding, Candidates, ProfileDetail, Messages, Chat, Saved, Me, Premium, Admin)
- 3 languages with selector
- Premium-gated lists with locked overlay
- **Tested: 26/26 backend, full frontend E2E pass**

### Iteration 2 (2026-02-27) — Feature completion ("C — hammasi")
- **Emergent Object Storage** integrated: `/api/files/upload` (image only, 8MB cap) + `/api/files/{path}` serve with viewer-JWT auth
- **4-Gift modal** (🌹50 / 🎁200 / 💎500 / 👑1500) replacing single-rose button across CandidateCard, ProfileDetail, Chat
- **Settings page** `/settings` for "Kim menga yozishi mumkin" filters (age/region/marital/children/height/weight/verified/financial)
- **Notifications page** `/notifications` + bell icon with unread badge in Me header
- **Block/Report 3-dot menu** in Chat header
- **Subscription expiry** auto-downgrade: `plan_until = now+30d` set on premium/vip purchase; `get_user()` downgrades expired plans
- **Telegram bot webhook** `/api/telegram/webhook?secret=` auto-set on backend startup; handles `/start <referral_code>` to attach referrer + reward +1000 so'm
- **Marketing notification daily cap** (max 2 per user per 24h) via admin broadcast endpoint `/api/admin/notification/broadcast`
- **Response time tracking** (`avg_response_min`) computed on /messages/send when replying; displayed on profile detail + Me
- **PhotoUpload** component (file upload + preview) integrated in Onboarding step 6 + Me profile card
- **photoSrc()** util appends viewer's JWT to backend-hosted image URLs so `<img>` tags can authenticate
- **Tested: 43/43 backend pytest pass; frontend Chat menu fix verified post-test**

## User Personas
1. Serious-minded woman — safe space, blurred photos, control over who messages
2. Serious-minded man — quality matches, willing to pay
3. Admin — manages users, payments, verifications, sees metrics

## What's Live / Working
✅ All PRD-listed features:
- 4 tab navigation, onboarding wizard, profile, candidates, matching, photo blur+unlock, messaging, applications, super-applications, gifts (4 kinds), leaderboard, referral, verification (3-tier), premium tiers, CLICK payment, admin panel, 3 languages, Telegram WebApp auth, Telegram bot webhook /start, notifications, settings filters, block/report, photo upload, response speed display, subscription expiry, marketing rate limit

## Remaining Backlog (P3 / nice-to-have)
- Refactor server.py (1450 lines) into per-domain routers
- Stream-check `Content-Length` before reading upload body
- Optional `dry_run` for admin broadcast
- Real-time chat (WebSocket) — currently 5s polling
- Rate-limit on /auth/login & /auth/register
- Token rotation policy for ?auth= query in photo URLs

## Test Credentials
See `/app/memory/test_credentials.md`
