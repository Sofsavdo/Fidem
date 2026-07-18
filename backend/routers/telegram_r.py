"""Telegram bot webhook + setup helper."""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from core import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_WEBHOOK_SECRET,
    db,
    get_webapp_url,
    iso,
    now_utc,
)
from services import (
    send_telegram_message,
    telegram_set_menu_button,
    telegram_set_my_commands,
    telegram_set_my_description,
    telegram_set_my_name,
    telegram_set_my_short_description,
    telegram_set_webhook,
)

log = logging.getLogger("fidem.telegram")
router = APIRouter(tags=["telegram"])


def get_backend_url() -> str:
    return os.environ.get(
        "BACKEND_URL",
        "https://fidem-production.up.railway.app",
    ).rstrip("/")


# Bot profile shown to users who haven't opened the Mini App yet: the "/"
# command menu, the short description (bot's profile page + link-share
# previews), and the description (empty chat before /start is pressed).
# Keyed by Telegram client language_code; "" is the default every other
# language falls back to - kept as Uzbek since that's the primary market.
BOT_COMMANDS = {
    "": [{"command": "start", "description": "FIDEM'ni ishga tushirish"}],
    "ru": [{"command": "start", "description": "Запустить FIDEM"}],
    "en": [{"command": "start", "description": "Launch FIDEM"}],
}
BOT_SHORT_DESCRIPTION = {
    "": "Jiddiy munosabat va oila qurish uchun ishonchli platforma. Tasdiqlangan profillar, xavfsiz muloqot.",
    "ru": "Платформа для серьёзных отношений и создания семьи. Проверенные анкеты, безопасное общение.",
    "en": "A trusted platform for serious relationships and family. Verified profiles, safe messaging.",
}
BOT_DESCRIPTION = {
    "": (
        "💖 FIDEM — jiddiy munosabat va oila qurish uchun platforma.\n\n"
        "✅ Aniq moslik algoritmi\n✅ Tasdiqlangan profillar\n✅ Xavfsiz chat\n✅ Premium imkoniyatlar\n\n"
        "👇 Boshlash uchun pastdagi Start tugmasini bosing"
    ),
    "ru": (
        "💖 FIDEM — платформа для серьёзных отношений и создания семьи.\n\n"
        "✅ Точный алгоритм подбора\n✅ Проверенные анкеты\n✅ Безопасный чат\n✅ Премиум-возможности\n\n"
        "👇 Нажмите Start, чтобы начать"
    ),
    "en": (
        "💖 FIDEM — a platform for serious relationships and family.\n\n"
        "✅ Precise matching algorithm\n✅ Verified profiles\n✅ Safe chat\n✅ Premium features\n\n"
        "👇 Tap Start to begin"
    ),
}


async def setup_telegram_webhook() -> None:
    if not TELEGRAM_BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set; Telegram webhook skipped")
        return

    public_base = get_backend_url()
    if not public_base:
        log.warning("BACKEND_URL not set; Telegram webhook skipped")
        return

    webapp_url = get_webapp_url()
    webhook_url = f"{public_base}/api/telegram/webhook"

    try:
        await telegram_set_webhook(webhook_url, TELEGRAM_WEBHOOK_SECRET)
        await telegram_set_menu_button(webapp_url)
        await telegram_set_my_name("FIDEM")
        for lang, commands in BOT_COMMANDS.items():
            await telegram_set_my_commands(commands, lang)
        for lang, text in BOT_SHORT_DESCRIPTION.items():
            await telegram_set_my_short_description(text, lang)
        for lang, text in BOT_DESCRIPTION.items():
            await telegram_set_my_description(text, lang)
    except Exception as e:
        log.warning(f"setWebhook/menu/profile failed: {e}")


async def _handle_start(chat_id: int, tg_user_id: str, text: str) -> None:
    """Everything a bare '/start [ref_code]' message does: record the
    funnel event, attribute (but never pay) a referral code, and reply with
    the Mini App button. Split out of the webhook route so it's a plain
    function - the route itself should only parse the Telegram update and
    dispatch, not carry this much domain logic inline."""
    parts = text.split(maxsplit=1)
    ref_code = parts[1].strip() if len(parts) > 1 else None

    # Record every /start so the onboarding funnel is measurable and the
    # lifecycle nudger can re-engage people who never open the Mini App.
    await db.bot_starts.update_one(
        {"telegram_id": tg_user_id},
        {
            "$set": {"chat_id": chat_id, "last_start_at": iso(now_utc())},
            "$setOnInsert": {
                "telegram_id": tg_user_id,
                "first_start_at": iso(now_utc()),
                "nudge_stage": 0,
            },
        },
        upsert=True,
    )

    existing = await db.users.find_one(
        {"telegram_id": tg_user_id},
        {"_id": 0, "id": 1, "referred_by": 1},
    )

    if ref_code and (not existing or not existing.get("referred_by")):
        # Try referral_id first (old system)
        ref_owner = await db.users.find_one(
            {"referral_id": ref_code},
            {"_id": 0, "id": 1},
        )

        # Fallback to referral_username_lower (new custom username system)
        if not ref_owner:
            ref_owner = await db.users.find_one(
                {"referral_username_lower": ref_code.lower()},
                {"_id": 0, "id": 1},
            )

        if ref_owner and (not existing or existing["id"] != ref_owner["id"]):
            # Just record the attribution here - do NOT pay any bonus yet.
            # A bare "/start CODE" text message costs the sender nothing
            # and proves nothing (no Mini App session, no real account),
            # so paying out on it is a free-money farm: script N throwaway
            # Telegram accounts to message /start, collect N x reward,
            # never touch the app again. The click-bonus is paid instead
            # in routers/auth_r.py at real account creation (/auth/telegram),
            # which requires a verified Telegram WebApp session and runs
            # through the existing IP-based fraud scoring.
            if existing:
                await db.users.update_one(
                    {"id": existing["id"]},
                    {"$set": {"referred_by": ref_code}},
                )
            else:
                await db.pending_refs.update_one(
                    {"telegram_id": tg_user_id},
                    {
                        "$set": {
                            "telegram_id": tg_user_id,
                            "ref_code": ref_code,
                            "at": iso(now_utc()),
                        }
                    },
                    upsert=True,
                )

    webapp_url = get_webapp_url()

    reply = (
        "💖 FIDEM\n\n"
        "Jiddiy munosabat va oila qurish uchun platforma.\n\n"
        "✅ Mos nomzodlar\n"
        "✅ Xavfsiz chat\n"
        "✅ Premium imkoniyatlar\n"
        "✅ Telegram ichida ishlaydi\n\n"
        "👇 Ilovani ochish uchun tugmani bosing"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "💖 FIDEM'ni ochish",
                    "web_app": {
                        "url": webapp_url,
                    },
                }
            ]
        ]
    }

    await send_telegram_message(
        chat_id,
        reply,
        reply_markup=keyboard,
    )


async def _dispatch(body: dict) -> None:
    # Admin inline buttons (P2P top-up approve/reject) arrive as
    # callback_query updates, not messages.
    cb = body.get("callback_query")
    if cb:
        from admin_bot import handle_admin_callback

        await handle_admin_callback(cb)
        return

    msg = body.get("message")
    if not msg:
        return

    text = (msg.get("text") or "").strip()
    chat_id = msg["chat"]["id"]
    tg_user_id = str(msg["from"]["id"])

    # Admin-only /stats: owner metrics straight in the bot chat
    if text.startswith("/stats"):
        from admin_bot import build_stats_text, is_admin_tg

        if await is_admin_tg(int(tg_user_id)):
            await send_telegram_message(chat_id, await build_stats_text())
        return

    if text.startswith("/start"):
        await _handle_start(chat_id, tg_user_id, text)


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    # Telegram's own webhook-authentication mechanism (Bot API 6.0+): the
    # secret set via setWebhook's secret_token is echoed back on every call
    # as this header. A URL query parameter was used here previously, which
    # is what a hand-rolled (rather than Telegram-native) check looks like -
    # it leaks the secret into access logs/proxies and isn't what Telegram
    # itself verifies.
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret or not hmac.compare_digest(secret, TELEGRAM_WEBHOOK_SECRET):
        raise HTTPException(403, "bad secret")

    body = await request.json()

    # Telegram guarantees at-least-once delivery and retries any update that
    # didn't get a fast 2xx - without tracking update_id, a slow response or
    # a transient error reprocesses (and can re-send messages for) the same
    # update. First-write-wins via a unique index makes this a no-op retry.
    update_id = body.get("update_id")
    if update_id is not None:
        try:
            await db.telegram_updates.insert_one({"update_id": update_id, "at": iso(now_utc())})
        except DuplicateKeyError:
            return {"ok": True}

    try:
        await _dispatch(body)
    except Exception:
        # Never let our own bug turn into a 500 - Telegram would just retry
        # the same update indefinitely (and now duplicate-process it, since
        # the dedup row above is already written).
        log.warning("telegram webhook dispatch failed", exc_info=True)

    return {"ok": True}
