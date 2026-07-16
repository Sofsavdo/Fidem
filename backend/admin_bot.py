"""Admin Telegram alerts: real-time P2P top-up review with inline
approve/reject buttons, on-demand /stats, and a daily digest.

Who counts as an admin for the bot: telegram_ids listed in the
ADMIN_TELEGRAM_IDS env var (comma-separated) PLUS any user document with
is_admin=true and a telegram_id. Callback taps from anyone else are ignored.
"""
from __future__ import annotations

import logging
import os
from datetime import timedelta

import httpx

from core import db, iso, now_utc, parse_dt

log = logging.getLogger("fidem.admin_bot")

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"


def _bot_own_id() -> int | None:
    """The numeric prefix of the bot token IS the bot's own Telegram user id
    — a common copy-paste mistake is pasting that number into
    ADMIN_TELEGRAM_IDS instead of a real admin's personal id. Telegram then
    rejects every send with 'Forbidden: the bot can't send messages to the
    bot', which otherwise looks identical to a misconfigured/missing admin."""
    try:
        return int(TG_BOT_TOKEN.split(":", 1)[0])
    except (ValueError, IndexError):
        return None


async def get_admin_chat_ids() -> list[int]:
    ids: set[int] = set()
    for part in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    rows = await db.users.find(
        {"is_admin": True, "telegram_id": {"$nin": [None, ""]}},
        {"_id": 0, "telegram_id": 1},
    ).to_list(20)
    for r in rows:
        try:
            ids.add(int(r["telegram_id"]))
        except (TypeError, ValueError):
            pass
    bot_id = _bot_own_id()
    if bot_id is not None and bot_id in ids:
        ids.discard(bot_id)
        log.warning(
            f"ADMIN_TELEGRAM_IDS (or an admin user's telegram_id) contains {bot_id}, "
            "which is the BOT's own id (the number before ':' in TELEGRAM_BOT_TOKEN), "
            "not a real admin's Telegram user id — ignoring it. Get your real id from "
            "@userinfobot in Telegram and use that instead."
        )
    return list(ids)


async def is_admin_tg(tg_id: int) -> bool:
    return tg_id in await get_admin_chat_ids()


async def _send_photo(chat_id: int, photo: bytes, caption: str, reply_markup: dict | None = None) -> bool:
    if not TG_BOT_TOKEN:
        return False
    import json as _json

    data = {"chat_id": str(chat_id), "caption": caption}
    if reply_markup:
        data["reply_markup"] = _json.dumps(reply_markup)
    try:
        async with httpx.AsyncClient(timeout=20.0) as cl:
            r = await cl.post(f"{TG_API}/sendPhoto", data=data, files={"photo": ("receipt.jpg", photo)})
            if r.status_code != 200:
                log.warning(f"sendPhoto failed: {r.status_code} {r.text[:200]}")
            return r.status_code == 200
    except Exception as e:
        log.warning(f"sendPhoto error: {e}")
        return False


async def answer_callback(callback_id: str, text: str) -> None:
    if not TG_BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            await cl.post(f"{TG_API}/answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})
    except Exception:
        pass


async def edit_caption(chat_id: int, message_id: int, caption: str) -> None:
    """Rewrite the alert caption after a decision so the buttons disappear
    and the thread shows what happened."""
    if not TG_BOT_TOKEN:
        return
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            await cl.post(
                f"{TG_API}/editMessageCaption",
                json={"chat_id": chat_id, "message_id": message_id, "caption": caption},
            )
    except Exception:
        pass


async def notify_admins_manual_topup(topup: dict) -> None:
    """Fire a real-time review card (receipt photo + approve/reject buttons)
    to every admin the moment a P2P top-up request lands."""
    admins = await get_admin_chat_ids()
    if not admins:
        log.warning("manual topup alert: no admin telegram ids configured")
        return

    u = await db.users.find_one(
        {"id": topup["user_id"]},
        {"_id": 0, "name": 1, "telegram_id": 1, "balance": 1, "region": 1},
    ) or {}
    caption = (
        "💳 YANGI P2P TO'LOV SO'ROVI\n\n"
        f"👤 {u.get('name') or topup['user_id']} ({u.get('region') or '—'})\n"
        f"💰 Summa: {topup['amount']:,} so'm\n"
        f"💼 Joriy balansi: {(u.get('balance') or 0):,} so'm\n"
        f"🆔 So'rov: {topup['id']}\n\n"
        "⚠️ Tasdiqlashdan oldin pul kartaga KELGANINI bank ilovangizda tekshiring."
    )
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Tasdiqlash", "callback_data": f"mtu:a:{topup['id']}"},
            {"text": "❌ Rad etish", "callback_data": f"mtu:r:{topup['id']}"},
        ]]
    }

    photo: bytes | None = None
    try:
        from storage import get_object

        oid = (topup.get("proof_url") or "").rstrip("/").rsplit("/", 1)[-1]
        if oid:
            photo, _ct = await get_object(oid)
    except Exception as e:
        log.warning(f"topup receipt fetch failed: {e}")

    from services import send_telegram_message

    for chat_id in admins:
        if photo:
            ok = await _send_photo(chat_id, photo, caption, reply_markup=keyboard)
            if ok:
                continue
        # No photo (or sendPhoto failed): still deliver the alert as text
        await send_telegram_message(chat_id, caption, reply_markup=keyboard)


async def build_stats_text() -> str:
    """Admin /stats: the numbers an owner actually checks from the phone."""
    now = now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_ago = iso(now - timedelta(hours=24))
    week_ago = iso(now - timedelta(days=7))

    total = await db.users.count_documents({})
    onboarded = await db.users.count_documents({"onboarded": True})
    today_new = await db.users.count_documents({"created_at": {"$gte": iso(today_start)}})
    active_24h = await db.users.count_documents({"last_active": {"$gte": day_ago}})
    active_7d = await db.users.count_documents({"last_active": {"$gte": week_ago}})
    bot_starts = await db.bot_starts.count_documents({})
    pending_topups = await db.manual_topups.count_documents({"status": "pending"})

    # Signups by hour, today
    hourly = await db.users.aggregate([
        {"$match": {"created_at": {"$gte": iso(today_start)}}},
        {"$project": {"h": {"$substrBytes": ["$created_at", 11, 2]}}},
        {"$group": {"_id": "$h", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]).to_list(24)
    hours_line = "  ".join(f"{r['_id']}:00→{r['n']}" for r in hourly) or "—"

    # Money: sum of user balances (liability) + payments today
    bal = await db.users.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$balance"}}}
    ]).to_list(1)
    total_balance = (bal[0]["total"] if bal else 0) or 0
    pay = await db.payments.aggregate([
        {"$match": {"status": {"$in": ["paid", "success"]}, "created_at": {"$gte": iso(today_start)}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}, "n": {"$sum": 1}}},
    ]).to_list(1)
    pay_today = pay[0] if pay else {"total": 0, "n": 0}

    return (
        f"📊 FIDEM STATISTIKA ({now.strftime('%d.%m %H:%M')} UTC)\n\n"
        f"👥 Jami: {total} (anketali: {onboarded})\n"
        f"🆕 Bugun qo'shildi: {today_new}\n"
        f"🕐 Soatlar bo'yicha: {hours_line}\n"
        f"🟢 Faol 24 soat: {active_24h} · 7 kun: {active_7d}\n"
        f"🤖 Bot /start (jami): {bot_starts}\n\n"
        f"💳 Kutilayotgan P2P so'rovlar: {pending_topups}\n"
        f"💰 Bugungi to'lovlar: {pay_today['n']} ta, {pay_today['total']:,} so'm\n"
        f"🏦 Userlar balansi (majburiyat): {total_balance:,} so'm\n\n"
        "Buyruqlar: /stats — shu hisobot"
    )


async def handle_admin_callback(cb: dict) -> None:
    """callback_query router for admin inline buttons (mtu:a/r:<id>)."""
    cb_id = cb.get("id", "")
    from_id = int(cb.get("from", {}).get("id", 0) or 0)
    data = cb.get("data", "") or ""
    msg = cb.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id")
    message_id = msg.get("message_id")

    if not data.startswith("mtu:"):
        return
    if not await is_admin_tg(from_id):
        await answer_callback(cb_id, "Ruxsat yo'q")
        return

    _, action, tid = data.split(":", 2)
    approve = action == "a"
    from routers.payments_r import decide_manual_topup

    res = await decide_manual_topup(
        tid,
        approve,
        reason="" if approve else "Chek tasdiqlanmadi — to'lovni tekshirib qayta yuboring yoki admin bilan bog'laning",
        decided_by=f"tg:{from_id}",
    )
    if res is None:
        await answer_callback(cb_id, "Allaqachon ko'rib chiqilgan")
        if chat_id and message_id:
            await edit_caption(chat_id, message_id, (msg.get("caption") or "") + "\n\n⚠️ Allaqachon ko'rib chiqilgan")
        return

    verdict = "✅ TASDIQLANDI — balans tushdi" if approve else "❌ RAD ETILDI"
    await answer_callback(cb_id, verdict)
    if chat_id and message_id:
        await edit_caption(chat_id, message_id, (msg.get("caption") or "") + f"\n\n{verdict}")
