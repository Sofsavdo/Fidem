# Environment Variables Setup

Set these in Railway, on the **fidem-backend** and **fidem-frontend** services
(Variables → RAW Editor). Railway redeploys automatically when they change.

Current domains: backend `https://fidem-backend-production.up.railway.app`,
frontend `https://fidem-frontend-production.up.railway.app`.

## Backend (`fidem-backend`)

### Required - the backend does not start without these
```bash
MONGO_URL=mongodb+srv://USER:PASSWORD@cluster.mongodb.net/   # Atlas connection string
DB_NAME=                                                      # the existing database name
JWT_SECRET=                                                   # long random string
ADMIN_PASSWORD=                                               # required when ENVIRONMENT=production
ENVIRONMENT=production
```
MongoDB Atlas: under **Network Access** allow Railway to connect (Railway has
no fixed outbound IP, so add `0.0.0.0/0`) and keep a strong database password.

### URLs
```bash
BACKEND_URL=https://fidem-backend-production.up.railway.app
WEBAPP_URL=https://fidem-frontend-production.up.railway.app
CORS_ORIGINS=https://fidem-frontend-production.up.railway.app
```
On startup the backend registers the Telegram webhooks (`BACKEND_URL`) and the
Mini App menu button (`WEBAPP_URL`) from these two values.

### Telegram
```bash
TELEGRAM_BOT_TOKEN=            # main bot (Fidem_Appbot)
TELEGRAM_BOT_USERNAME=Fidem_Appbot
TELEGRAM_WEBHOOK_SECRET=       # any random string
ADMIN_BOT_TOKEN=               # admin bot
ADMIN_BOT_WEBHOOK_SECRET=      # any random string
ADMIN_TELEGRAM_IDS=            # comma-separated numeric Telegram ids of admins
```

### Payments (CLICK)
```bash
CLICK_MERCHANT_ID=54318
CLICK_SERVICE_ID=92585
CLICK_SECRET_KEY=
CLICK_RETURN_URL=https://fidem-frontend-production.up.railway.app/me
```
In the CLICK merchant cabinet set both **Prepare URL** and **Complete URL** to
`https://fidem-backend-production.up.railway.app/api/payments/click/callback`.

### AI verification
```bash
GEMINI_API_KEY=                # primary provider
ANTHROPIC_API_KEY=             # optional fallback
```
With neither key set, signup still works but no profile gets the verified badge.

### Feature switches
```bash
FREE_WEEKLY_INITIATIONS=0      # 0 disables the free weekly chat
DAILY_STREAK_ENABLED=0         # 0 disables the daily check-in bonus
```

### Optional
```bash
SOFSAVDO_INTEGRATION_SECRET=   # must equal the secret configured on the Sofsavdo side
SOFSAVDO_WEBHOOK_URL=          # defaults to https://api.sofsavdo.com/integrations/fidem/webhook
SENTRY_DSN=
PRICE_STANDARD_UZS=34900  PRICE_PREMIUM_UZS=79000  PRICE_VIP_UZS=199000
```

## Frontend (`fidem-frontend`)

`REACT_APP_*` values are baked in at **build** time, so changing one triggers a rebuild.
```bash
REACT_APP_BACKEND_URL=https://fidem-backend-production.up.railway.app
REACT_APP_ADMIN_TELEGRAM_USERNAME=FidemAppSupport   # "Contact admin" link on the Me page
```

Product-focus flags (build-time, all OFF by default; set to `1` to bring one back):
```bash
REACT_APP_FEATURE_RANKINGS=1      # gift leaderboard + "boost your rank"
REACT_APP_FEATURE_GIFT_SHOP=1     # gift shop link on the Me page
REACT_APP_FEATURE_BOOST=1         # paid profile boost
REACT_APP_FEATURE_LEGACY_TIERS=1  # sell Standard / VIP besides Premium
```
Only Free + Premium are on sale by default; existing Standard/VIP subscribers keep
their plan and benefits.

Runtime (not build-time) variable on the frontend service, optional but
recommended for speed:
```bash
BACKEND_INTERNAL_URL=http://<backend-service>.railway.internal:<PORT>
```
When set, `server.js` forwards `/api/*` (including the WebSocket) to the backend.
Then build the frontend with `REACT_APP_BACKEND_URL=https://<frontend-domain>` so
the browser talks to a single origin and skips the CORS preflight round trip
before every new API URL. Leave it unset to keep the browser calling the
backend domain directly.

## Railway notes
- Both services deploy from `Sofsavdo/Fidem` (`main`); the backend uses root
  directory `backend`, the frontend `frontend`.
- Pick a region close to your users and to the MongoDB cluster (Europe suits
  Uzbekistan better than the US West default).
