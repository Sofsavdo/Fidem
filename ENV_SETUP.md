# Environment Variables Setup

## Backend Environment Variables

Required environment variables for the backend:

```bash
# Database
MONGO_URL=mongodb+srv://username:password@cluster.mongodb.net/fidem
DB_NAME=fidem_database

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_BOT_USERNAME=Fidem_Appbot
TELEGRAM_WEBHOOK_SECRET=your_webhook_secret

# CORS & URLs
CORS_ORIGINS=https://fidem.up.railway.app
WEBAPP_URL=https://fidem.up.railway.app
BACKEND_URL=https://fidem-production.up.railway.app

# Environment
ENVIRONMENT=production

# Security (REQUIRED in production - backend refuses to start without them)
JWT_SECRET=long_random_string
ADMIN_PASSWORD=strong_admin_password

# AI verification (photo checks + selfie/identity/financial review).
# PRIMARY provider: Gemini (Google AI Studio) - set GEMINI_API_KEY.
# ANTHROPIC_API_KEY is an optional automatic fallback. If NEITHER is set,
# AI checks are effectively disabled and a warning is logged at startup.
GEMINI_API_KEY=AIza...
# GEMINI_MODEL=gemini-2.0-flash   # optional override
ANTHROPIC_API_KEY=sk-ant-...      # optional fallback
```

## Frontend Environment Variables

Required environment variables for the frontend:

```bash
REACT_APP_BACKEND_URL=https://fidem-production.up.railway.app

# Optional - "Contact admin" link on the Me page (Telegram username, no @).
# Defaults to FidemAppSupport if unset.
REACT_APP_ADMIN_TELEGRAM_USERNAME=FidemAppSupport
```

## Railway Deployment

Set these variables in Railway project settings for both backend and frontend services.
