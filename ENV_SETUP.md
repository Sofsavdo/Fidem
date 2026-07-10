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
CORS_ORIGINS=https://fidem-frontend-production.up.railway.app
WEBAPP_URL=https://fidem-frontend-production.up.railway.app
BACKEND_URL=https://fidem-production.up.railway.app

# Environment
ENVIRONMENT=production

# Security (REQUIRED in production - backend refuses to start without them)
JWT_SECRET=long_random_string
ADMIN_PASSWORD=strong_admin_password

# AI photo verification + AI match/compatibility texts.
# Without this key photo verification is effectively DISABLED (all photos
# pass through unverified) and a warning is logged at startup.
ANTHROPIC_API_KEY=sk-ant-...
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
