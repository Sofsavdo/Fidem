"""Fidemadminbot webhook + setup: a second, admin-only Telegram bot whose
only job is to hand the owner a one-tap Mini App button into /admin. It
does not talk to regular users and carries none of the referral/onboarding
logic of routers/telegram_r.py - /start is the only command it understands.
"""
from __future__ import annotations

import hmac
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from pymongo.errors import DuplicateKeyError

from core import ADMIN_BOT_TOKEN, ADMIN_BOT_WEBHOOK_SECRET, db, get_admin_webapp_url, iso, now_utc
from services import admin_bot_set_menu_button, admin_bot_set_webhook, send_admin_bot_message

log = logging.getLogger("fidem.admin_telegram")
router = APIRouter(tags=["admin-telegram"])


def get_backend_url() -> str:
    return os.environ.get(
        "BACKEND_URL",
        "https://fidem-production.up.railway.app",
    ).rstrip("/")


async def setup_admin_telegram_webhook() -> None:
    if not ADMIN_BOT_TOKEN:
        log.info("ADMIN_BOT_TOKEN not set; admin bot webhook skipped (optional feature)")
        return

    public_base = get_backend_url()
    if not public_base:
        log.warning("BACKEND_URL not set; admin bot webhook skipped")
        return

    webhook_url = f"{public_base}/api/admin-telegram/webhook"
    try:
        await admin_bot_set_webhook(webhook_url, ADMIN_BOT_WEBHOOK_SECRET)
        await admin_bot_set_menu_button(get_admin_webapp_url())
    except Exception as e:
        log.warning(f"admin bot setWebhook/menu failed: {e}")


async def _handle_start(chat_id: int, tg_user_id: str) -> None:
    from admin_bot import is_admin_tg

    if not await is_admin_tg(int(tg_user_id)):
        await send_admin_bot_message(
            chat_id,
            "⛔ Bu bot faqat FIDEM adminlari uchun. Sizning Telegram ID'ingiz "
            "admin ro'yxatida (ADMIN_TELEGRAM_IDS) yo'q.",
        )
        return

    keyboard = {
        "inline_keyboard": [[
            {"text": "🛠 Admin panelni ochish", "web_app": {"url": get_admin_webapp_url()}},
        ]]
    }
    await send_admin_bot_message(
        chat_id,
        "🛠 FIDEM Admin\n\nPanelni Telegram ichida ochish uchun tugmani bosing.",
        reply_markup=keyboard,
    )


async def _dispatch(body: dict) -> None:
    # P2P approve/reject inline buttons (see admin_bot.notify_admins_manual_topup,
    # which sends them through this bot once ADMIN_BOT_TOKEN is configured).
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

    if text.startswith("/stats"):
        from admin_bot import build_stats_text, is_admin_tg

        if await is_admin_tg(int(tg_user_id)):
            await send_admin_bot_message(chat_id, await build_stats_text())
        return

    if text.startswith("/start"):
        await _handle_start(chat_id, tg_user_id)


@router.post("/admin-telegram/webhook")
async def admin_telegram_webhook(request: Request):
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not secret or not hmac.compare_digest(secret, ADMIN_BOT_WEBHOOK_SECRET):
        raise HTTPException(403, "bad secret")

    body = await request.json()

    # Shares the telegram_updates dedup collection with the user bot's
    # webhook, but the two bots' update_id sequences are independent and
    # can collide (e.g. both legitimately emit update_id=1) - the "admin:"
    # prefix keeps this bot's dedup keys in their own namespace so a
    # coincidental collision never silently drops a real admin-bot update.
    update_id = body.get("update_id")
    if update_id is not None:
        try:
            await db.telegram_updates.insert_one({"update_id": f"admin:{update_id}", "at": iso(now_utc())})
        except DuplicateKeyError:
            return {"ok": True}

    try:
        await _dispatch(body)
    except Exception:
        log.warning("admin telegram webhook dispatch failed", exc_info=True)

    return {"ok": True}
