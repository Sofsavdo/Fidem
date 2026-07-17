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

from core import db, iso, now_utc
from services import (
    ADMIN_BOT_TOKEN,
    TELEGRAM_BOT_TOKEN,
    answer_admin_callback_query,
    answer_callback_query,
    edit_admin_message_caption,
    edit_message_caption,
    send_admin_bot_message,
    send_admin_bot_photo,
    send_telegram_message,
    send_telegram_photo,
)

log = logging.getLogger("fidem.admin_bot")

# Admin alerts (P2P review, /stats, daily digest) prefer the dedicated admin
# bot (Fidemadminbot) once ADMIN_BOT_TOKEN is configured; otherwise they fall
# back to the main user-facing bot so alerts never go silent just because the
# admin bot hasn't been set up yet - a real production incident (a P2P
# payment sat unreviewed for 46 minutes because no Telegram alert arrived)
# is exactly the failure mode this fallback guards against.
_USE_ADMIN_BOT = bool(ADMIN_BOT_TOKEN)


async def send_admin_alert(chat_id: int, text: str, reply_markup: dict | None = None) -> bool:
    fn = send_admin_bot_message if _USE_ADMIN_BOT else send_telegram_message
    return await fn(chat_id, text, reply_markup=reply_markup)


async def send_admin_alert_photo(chat_id: int, photo: bytes, caption: str, reply_markup: dict | None = None) -> bool:
    fn = send_admin_bot_photo if _USE_ADMIN_BOT else send_telegram_photo
    return await fn(chat_id, photo, caption, reply_markup=reply_markup)


async def answer_admin_alert_callback(callback_id: str, text: str) -> None:
    fn = answer_admin_callback_query if _USE_ADMIN_BOT else answer_callback_query
    await fn(callback_id, text)


async def edit_admin_alert_caption(chat_id: int, message_id: int, caption: str) -> None:
    fn = edit_admin_message_caption if _USE_ADMIN_BOT else edit_message_caption
    await fn(chat_id, message_id, caption)


def _own_bot_ids() -> set[int]:
    """The numeric prefix of a bot token IS that bot's own Telegram user id
    — a common copy-paste mistake is pasting that number into
    ADMIN_TELEGRAM_IDS instead of a real admin's personal id (now possible
    with either bot's token, since ADMIN_TELEGRAM_IDS gates both). Telegram
    then rejects every send with 'Forbidden: the bot can't send messages to
    the bot', which otherwise looks identical to a misconfigured/missing
    admin."""
    ids: set[int] = set()
    for token in (TELEGRAM_BOT_TOKEN, ADMIN_BOT_TOKEN):
        try:
            ids.add(int(token.split(":", 1)[0]))
        except (ValueError, IndexError):
            pass
    return ids


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
    bot_ids = _own_bot_ids()
    overlap = ids & bot_ids
    if overlap:
        ids -= bot_ids
        log.warning(
            f"ADMIN_TELEGRAM_IDS (or an admin user's telegram_id) contains {overlap}, "
            "which is a BOT's own id (the number before ':' in its token), not a real "
            "admin's Telegram user id — ignoring it. Get your real id from @userinfobot "
            "in Telegram and use that instead."
        )
    return list(ids)


async def is_admin_tg(tg_id: int) -> bool:
    return tg_id in await get_admin_chat_ids()


# Below this AI confidence, a P2P request always stays in the human queue.
# The model's own instructions already tell it to prefer "unsure" over a
# shaky "approve", so a high bar here is a second layer, not the only one.
AI_P2P_AUTO_APPROVE_CONFIDENCE = 75


async def notify_admins_manual_topup(topup: dict) -> None:
    """AI reviews the receipt first; a confident approval credits the
    balance immediately (decided_by="ai") and admins get an info-only
    recap. Anything else - low confidence, reject, unsure, or the AI call
    failing outright - falls through to the original real-time review
    card (receipt photo + approve/reject buttons), now with the AI's own
    read of the receipt shown alongside so a human isn't starting cold."""
    admins = await get_admin_chat_ids()
    if not admins:
        log.warning("manual topup alert: no admin telegram ids configured")
        return

    u = await db.users.find_one(
        {"id": topup["user_id"]},
        {"_id": 0, "name": 1, "telegram_id": 1, "balance": 1, "region": 1},
    ) or {}

    ai_review: dict | None = None
    try:
        from ai_service import analyze_p2p_receipt

        ai_review = await analyze_p2p_receipt(topup.get("proof_url", ""), topup["amount"])
    except Exception as e:
        log.warning(f"P2P AI review failed: {e}")

    await db.manual_topups.update_one({"id": topup["id"]}, {"$set": {"ai_review": ai_review}})

    auto_approved = False
    if (
        ai_review
        and ai_review.get("ai_generated")
        and ai_review.get("verdict") == "approve"
        and ai_review.get("confidence", 0) >= AI_P2P_AUTO_APPROVE_CONFIDENCE
    ):
        from routers.payments_r import decide_manual_topup

        decided = await decide_manual_topup(topup["id"], True, reason="", decided_by="ai")
        auto_approved = decided is not None

    ai_line = ""
    if ai_review and ai_review.get("ai_generated"):
        icon = {"approve": "✅", "reject": "❌", "unsure": "❓"}.get(ai_review["verdict"], "❓")
        ai_line = (
            f"\n\n🤖 AI xulosasi: {icon} {ai_review['verdict']} ({ai_review['confidence']}%)"
            f"\n{ai_review.get('reason') or '—'}"
        )

    caption = (
        "💳 YANGI P2P TO'LOV SO'ROVI\n\n"
        f"👤 {u.get('name') or topup['user_id']} ({u.get('region') or '—'})\n"
        f"💰 Summa: {topup['amount']:,} so'm\n"
        f"💼 Joriy balansi: {(u.get('balance') or 0):,} so'm\n"
        f"🆔 So'rov: {topup['id']}"
        f"{ai_line}"
    )

    if auto_approved:
        caption += "\n\n✅ AI TOMONIDAN AVTOMATIK TASDIQLANDI — balans tushdi.\n⚠️ Agar pul kartaga kelmagan bo'lsa, foydalanuvchi tafsilotlaridan \"Firibgarlik\" tugmasi orqali balansni 0 ga qaytarib, bloklang."
        keyboard = None
    else:
        caption += "\n\n⚠️ Tasdiqlashdan oldin pul kartaga KELGANINI bank ilovangizda tekshiring."
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

    for chat_id in admins:
        if photo:
            ok = await send_admin_alert_photo(chat_id, photo, caption, reply_markup=keyboard)
            if ok:
                continue
        # No photo (or sendPhoto failed): still deliver the alert as text
        await send_admin_alert(chat_id, caption, reply_markup=keyboard)


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
        await answer_admin_alert_callback(cb_id, "Ruxsat yo'q")
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
        await answer_admin_alert_callback(cb_id, "Allaqachon ko'rib chiqilgan")
        if chat_id and message_id:
            await edit_admin_alert_caption(chat_id, message_id, (msg.get("caption") or "") + "\n\n⚠️ Allaqachon ko'rib chiqilgan")
        return

    verdict = "✅ TASDIQLANDI — balans tushdi" if approve else "❌ RAD ETILDI"
    await answer_admin_alert_callback(cb_id, verdict)
    if chat_id and message_id:
        await edit_admin_alert_caption(chat_id, message_id, (msg.get("caption") or "") + f"\n\n{verdict}")
