"""Telegram bot webhook + setup helper."""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from core import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_BOT_USERNAME,
    TELEGRAM_WEBHOOK_SECRET,
    db,
    iso,
    now_utc,
    push_notif,
)
from services import send_telegram_message

log = logging.getLogger("fidem.telegram")
router = APIRouter(tags=["telegram"])


def get_webapp_url() -> str:
    return os.environ.get(
        "WEBAPP_URL",
        "https://fidem-frontend-production.up.railway.app",
    ).rstrip("/")


def get_backend_url() -> str:
    return os.environ.get(
        "BACKEND_URL",
        "https://fidem-production.up.railway.app",
    ).rstrip("/")


async def setup_telegram_webhook() -> None:
    if not TELEGRAM_BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set; Telegram webhook skipped")
        return

    public_base = get_backend_url()
    if not public_base:
        log.warning("BACKEND_URL not set; Telegram webhook skipped")
        return

    webapp_url = get_webapp_url()
    webhook_url = f"{public_base}/api/telegram/webhook?secret={TELEGRAM_WEBHOOK_SECRET}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as cl:
            r = await cl.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={
                    "url": webhook_url,
                    "allowed_updates": ["message"],
                },
            )
            log.info(f"Telegram webhook set: {r.status_code} {r.text[:200]}")

            menu = await cl.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setChatMenuButton",
                json={
                    "menu_button": {
                        "type": "web_app",
                        "text": "💖 FIDEM",
                        "web_app": {
                            "url": webapp_url,
                        },
                    }
                },
            )
            log.info(f"Telegram menu button set: {menu.status_code} {menu.text[:200]}")

    except Exception as e:
        log.warning(f"setWebhook/menu failed: {e}")


@router.post("/telegram/webhook")
async def telegram_webhook(request: Request, secret: Optional[str] = Query(None)):
    if secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(403, "bad secret")

    body = await request.json()
    msg = body.get("message")

    if not msg:
        return {"ok": True}

    text = (msg.get("text") or "").strip()
    chat_id = msg["chat"]["id"]
    tg_user_id = str(msg["from"]["id"])

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        ref_code = parts[1].strip() if len(parts) > 1 else None

        existing = await db.users.find_one(
            {"telegram_id": tg_user_id},
            {"_id": 0, "id": 1, "referred_by": 1},
        )

        if ref_code and (not existing or not existing.get("referred_by")):
            ref_owner = await db.users.find_one(
                {"referral_code": ref_code},
                {"_id": 0, "id": 1},
            )

            if ref_owner and (not existing or existing["id"] != ref_owner["id"]):
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

                await db.users.update_one(
                    {"id": ref_owner["id"]},
                    {"$inc": {"balance": 1000, "ref_count": 1}},
                )

                await push_notif(
                    ref_owner["id"],
                    "referral",
                    "🎁 Yangi taklif bonusi\n\nSizning havolangiz orqali yangi foydalanuvchi qo‘shildi.\n\n+1000 so‘m bonus hisoblandi.",
                    link="/referral",
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

    return {"ok": True}
