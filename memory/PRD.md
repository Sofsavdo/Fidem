# FIDEM 1.0 — PRD & Build Log

## Original Problem Statement
FIDEM — Telegram Mini App for serious dating, relationships and family-building. NOT Tinder, NOT Instagram, NOT a marriage agency. Premium matchmaking platform inside Telegram.

Tagline: "Sizga mos insonni xavfsiz topishga yordam beramiz."

## Architecture
- **Backend**: FastAPI (Python) + MongoDB (motor async) + JWT auth + Telegram WebApp initData HMAC verifier + CLICK Merchant API (prepare/complete callbacks + Shop pay-link)
- **Frontend**: React 19 + react-router v7 + Tailwind + shadcn/ui + sonner toasts + axios. Mobile-first (414px max-width), responsive web + Telegram Mini App hybrid.
- **i18n**: 3 languages (uz/ru/en) — single dict file, auto-detect from Telegram or browser, persisted to localStorage + user profile.

## User Personas
1. **Serious-minded woman** — wants safe space, default-blurred photos, control over who messages her.
2. **Serious-minded man** — wants quality matches, willing to pay (Premium / VIP / one-time super applications).
3. **Admin** — manages users, verifications, payments, reports, sees DAU/WAU/revenue.

## Core Requirements (static)
- 4 bottom-nav tabs: Candidates / Messages / Saved / Me
- Onboarding wizard (7 steps, 17 fields)
- Match score (0–100) with reasons
- Default blurred photos with unlock request flow
- Filter "who can message me" (age/region/marital/children/height/weight/verified/financial)
- Super application (paid) bypasses filters
- 3-tier verification (Identity ✓ / Selfie / Financial 💎)
- Premium 79,000 UZS / VIP 199,000 UZS / Super 15,000 UZS / Topup
- Gifts: 🌹 50 / 🎁 200 / 💎 500 / 👑 1500 (balance)
- Leaderboard TOP SUPPORTERS (day/week/month/all)
- Referral with telegram link
- CLICK payment (Prepare + Complete callbacks)
- Admin panel: stats, users, payments, verifications, reports
- 3 languages

## What's Been Implemented (2026-02-24)
- ✅ Backend: 40+ API endpoints across auth, profile, candidates, messages, applications, photo-unlock, saved, gifts, leaderboard, verification, payments, notifications, referral, admin
- ✅ Backend startup auto-seeds 1 admin + 14 demo users with photos
- ✅ JWT auth (email/password) + Telegram WebApp initData (HMAC-SHA256) auth
- ✅ Match scoring with weighted attributes + human-readable reasons
- ✅ CLICK pay-link generation + callback signature verification (prepare/complete)
- ✅ Subscription expiry set to now+30days on premium/vip
- ✅ Telegram bot notification integration (sends to user.telegram_id)
- ✅ Frontend: 10 pages (Auth, Onboarding, Candidates, ProfileDetail, Messages, Chat, Saved, Me, Premium, Admin)
- ✅ i18n in uz/ru/en with selector on auth and Me pages
- ✅ Premium-gated lists (locked overlay) for saved-by-others/viewers/interested
- ✅ Tested: 26/26 backend pass, full frontend E2E flow verified

## Prioritized Backlog (next phases)
### P1
- Object Storage for photo uploads (currently URL string input only)
- Subscription expiry background job (downgrade after plan_until)
- Pagination on /messages/{chat_id} and /messages/chats (currently 500 limit)
- Telegram bot commands (`/start <referral_code>` for invites)

### P2
- Real-time chat via WebSocket / SSE (currently polled every 5s)
- Smart greeting AI suggestions
- Match-quality boost for Premium/VIP users in feed sort
- Push notification settings (per-kind on/off in Me)
- Marketing notification daily cap enforcement (currently no rate limit)

### P3
- Refactor server.py into routers (1240 lines)
- Rate limiting on /auth/login & /auth/register
- Admin: bulk actions, CSV export, charts library

## Test Credentials
See /app/memory/test_credentials.md

## Known Limitations
- Photo upload is URL-only (no file upload in MVP)
- Real-time chat uses polling (5s interval)
- CLICK callback URL must be configured publicly for real payments to settle; admin-confirm endpoint provides manual fallback
