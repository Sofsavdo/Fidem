# FIDEM 1.0 — PRD & Build Log

## Original Problem Statement
FIDEM — Telegram Mini App for serious dating, relationships and family-building. Premium matchmaking platform inside Telegram. Tagline: "Sizga mos insonni xavfsiz topishga yordam beramiz."

## Architecture (final)
- **Backend**: FastAPI + MongoDB + JWT + Telegram WebApp HMAC + CLICK + Emergent Object Storage + Telegram Bot webhook + **WebSocket real-time**
  - Modular: `server.py` (180 lines), `core.py` (shared helpers/DB/ConnectionManager/RateLimiter), `routers/{auth,candidates,chat,payments,admin,telegram}_r.py`
- **Frontend**: React 19 + Tailwind + shadcn + sonner + WebSocket auto-reconnect client
- **i18n**: uz/ru/en

## Iteration Log

### Iter 1 — MVP (26/26 tests pass)
Auth, onboarding, candidates, matching, blur+unlock, saved, messages, chat, premium, leaderboard, referral, admin, 3 languages.

### Iter 2 — Feature completion C (43/43)
Gift modal, settings filters, notifications page+bell, file upload via Object Storage, block/report menu, subscription expiry, Telegram bot webhook `/start <ref>`, marketing daily-cap, response-speed tracking, photoSrc() viewer-JWT helper.

### Iter 3 — Tech-debt cleanup (49/49)
- **Backend refactor**: monolithic server.py (1450 lines) → 6 domain routers + core.py (180 lines entrypoint)
- **WebSocket `/api/ws?token=`**: real-time messages, gifts, notifications. Multi-tab supported. Auto-reconnect on frontend with exponential backoff
- **RateLimiter**: 10 attempts / 5 min per IP for `/auth/login` + `/auth/register` (in-memory sliding window)
- **Content-Length pre-check** on `/files/upload`
- **Admin broadcast `dry_run`** flag
- Chat.jsx removes 5s polling, uses `wsEvent` from context

## What's Live
✅ All PRD requirements complete (~100%)
✅ All payment flows (CLICK + admin-confirm fallback)
✅ All admin tools
✅ Real-time chat + notifications via WebSocket
✅ Rate limit + Subscription expiry + Marketing cap

## Final Architecture Tree
```
/app/backend/
  server.py              # entrypoint + lifespan + CORS + seeding
  core.py                # DB, helpers, ConnectionManager, RateLimiter
  auth.py                # JWT + Telegram HMAC validators
  services.py            # match scoring, CLICK helpers, Telegram bot client
  storage.py             # Emergent Object Storage wrapper
  models.py              # Pydantic models
  routers/
    auth_r.py            # /auth, /profile, /files
    candidates_r.py      # /candidates, /photo-unlock, /saved
    chat_r.py            # /messages, /gifts, /leaderboard, /ws
    payments_r.py        # /payments, /verification, /notifications, /referral
    admin_r.py           # /admin
    telegram_r.py        # /telegram/webhook

/app/frontend/src/
  App.js                 # routes
  lib/{api,i18n,photo,ws,utils}.js
  contexts/AppContext.jsx
  components/{BottomNav,Layout,Badges,CandidateCard,GiftModal,PhotoUpload}.jsx
  pages/{Auth,Onboarding,Candidates,ProfileDetail,Messages,Chat,Saved,Me,Premium,Settings,Notifications,Admin}.jsx
```

## Remaining (P3 — production hardening)
- Multi-pod rate limit (Redis-backed)
- Bucket rate limit per-endpoint (login vs register)
- WebSocket auth via cookie/header instead of `?token=` (logs leakage)
- Token rotation for `/files/{path}?auth=` URLs
- Background job for subscription `plan_until` cleanup (currently lazy in `get_user()`)

## Test Credentials
See `/app/memory/test_credentials.md`

## Status (Faza 3.5 — Monetization Optimization + Analytics + PWA COMPLETE)
- ✅ Withdrawals (gift conversion, Bigo model, CLICK cash-out)
- ✅ Family Contact Share (VIP only, two-sided accept)
- ✅ Sovchi Concierge (199K UZS / 30d / 5 hand-picked matches)
- ✅ Travel Mode (Premium+ only)
- ✅ Admin panel: Withdrawals + Concierge tabs
- ✅ Boost & Spotlight Analytics (impressions/views/likes/leaderboard)
- ✅ Financial Verification UI (file upload + PDF + admin moderation + auto-badge)
- ✅ Telegram inline-link push notifications
- ✅ PWA setup (manifest + service worker + offline fallback)
- ❌ Pending: Payme integration (next sprint, user said CLICK enough)
