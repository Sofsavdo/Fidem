"""Lifecycle loop: plan-expiry reminders/downgrades, daily-picks pushes and
weekly stat digests.

One background pass every 6 hours (same pattern as winback.py) instead of
three separate loops - a single batched sweep keeps DB load predictable.
All sends go through push_notif with marketing=True where appropriate, so
user notification preferences and the 24h marketing cap are respected.
Texts are Uzbek, matching every other server-initiated notification.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from core import PAID_PLANS, db, get_webapp_url, iso, now_utc, parse_dt, push_notif
from services import send_telegram_message

# Between-send pause in the bulk notification loops below. push_notif fires
# its Telegram delivery as a fire-and-forget task, so a tight loop over
# hundreds of users schedules that many concurrent Telegram API calls almost
# at once - comfortably over Telegram's ~30 msg/sec global limit. This caps
# the rate at which new sends get scheduled instead.
SEND_PACING_SECONDS = 0.05

log = logging.getLogger("fidem.lifecycle")

CHECK_INTERVAL_SECONDS = 6 * 60 * 60
BATCH = 500

PLAN_LABEL = {"standard": "Standard", "premium": "Premium", "vip": "VIP"}


async def _plan_reminders() -> None:
    """3 days before plan_until: one reminder per paid period."""
    now = now_utc()
    soon = iso(now + timedelta(days=3))
    now_iso = iso(now)
    rows = await db.users.find(
        {"plan": {"$in": list(PAID_PLANS)}, "plan_until": {"$gt": now_iso, "$lte": soon}},
        {"_id": 0, "id": 1, "plan": 1, "plan_until": 1, "plan_reminder_for": 1},
    ).to_list(BATCH)
    for u in rows:
        # plan_reminder_for pins the reminder to THIS billing period - a
        # renewal writes a new plan_until, which re-arms the reminder.
        if u.get("plan_reminder_for") == u.get("plan_until"):
            continue
        try:
            days_left = max(1, (parse_dt(u["plan_until"]) - now).days)
        except Exception:
            days_left = 3
        await push_notif(
            u["id"], "premium",
            f"⏳ {PLAN_LABEL.get(u['plan'], u['plan'])} tarifingizga {days_left} kun qoldi.\n\n"
            "Imkoniyatlar uzilmasligi uchun tarifni hoziroq yangilang.",
            link="/premium?tab=plans",
            marketing=True,
        )
        await db.users.update_one({"id": u["id"]}, {"$set": {"plan_reminder_for": u["plan_until"]}})
        await asyncio.sleep(SEND_PACING_SECONDS)


async def _plan_expiry() -> None:
    """Downgrade expired plans proactively and TELL the user (get_user's lazy
    downgrade stays as a fallback, but it is silent). Users with no
    plan_until (bought before expiry existed) are never touched."""
    now_iso = iso(now_utc())
    rows = await db.users.find(
        {"plan": {"$in": list(PAID_PLANS)}, "plan_until": {"$lt": now_iso}},
        {"_id": 0, "id": 1, "plan": 1, "plan_until": 1},
    ).to_list(BATCH)
    for u in rows:
        if not u.get("plan_until"):
            continue
        res = await db.users.update_one(
            {"id": u["id"], "plan_until": u["plan_until"]},
            {"$set": {"plan": "free", "plan_expired_at": now_iso}},
        )
        if res.modified_count == 1:
            await push_notif(
                u["id"], "premium",
                f"💔 {PLAN_LABEL.get(u['plan'], u['plan'])} tarifingiz muddati tugadi.\n\n"
                "Imkoniyatlarni qaytarish uchun tarifni yangilang.",
                link="/premium?tab=plans",
            )
            await asyncio.sleep(SEND_PACING_SECONDS)


async def _daily_picks_push() -> None:
    """Once per calendar day, tell recently-active users their picks are
    ready. Import here (not at module top) to avoid a circular import."""
    from routers.picks_r import compute_daily_picks

    today = now_utc().date().isoformat()
    week_ago = iso(now_utc() - timedelta(days=7))
    rows = await db.users.find(
        {
            "onboarded": True,
            "blocked": {"$ne": True},
            "last_active": {"$gte": week_ago},
            "daily_picks_notified_on": {"$ne": today},
        },
        {"_id": 0},
    ).limit(BATCH).to_list(BATCH)
    for u in rows:
        # Mark first: even a failed/empty pass shouldn't retry until tomorrow.
        await db.users.update_one({"id": u["id"]}, {"$set": {"daily_picks_notified_on": today}})
        try:
            picks = await compute_daily_picks(u)
        except Exception:
            continue
        if not picks:
            continue
        first = picks[0]
        await push_notif(
            u["id"], "match",
            f"✨ Bugungi tanlov tayyor: {first.get('name', '')} va yana {max(0, len(picks) - 1)} nafar sizga mos nomzod.\n\n"
            "Birinchi bo'lib yozing — imkoniyatni boy bermang!",
            link="/",
            marketing=True,
        )
        await asyncio.sleep(SEND_PACING_SECONDS)


async def _weekly_digest() -> None:
    """Weekly 'X viewed / Y saved you' stat - only when there IS something to
    brag about; silence otherwise."""
    now = now_utc()
    week_ago = iso(now - timedelta(days=7))
    month_ago = iso(now - timedelta(days=30))
    rows = await db.users.find(
        {
            "onboarded": True,
            "blocked": {"$ne": True},
            "last_active": {"$gte": month_ago},
            "$or": [
                {"last_weekly_digest_at": {"$exists": False}},
                {"last_weekly_digest_at": {"$lt": week_ago}},
            ],
        },
        {"_id": 0, "id": 1},
    ).limit(BATCH).to_list(BATCH)
    for u in rows:
        await db.users.update_one({"id": u["id"]}, {"$set": {"last_weekly_digest_at": iso(now)}})
        views = await db.profile_views.count_documents({"target_id": u["id"], "at": {"$gte": week_ago}})
        saves = await db.saved.count_documents({"target_id": u["id"], "at": {"$gte": week_ago}})
        if views + saves == 0:
            continue
        await push_notif(
            u["id"], "view",
            f"📊 Bu hafta profilingizni {views} kishi ko'rdi, {saves} kishi saqladi.\n\n"
            "Kim ekanini bilish uchun FIDEM'ni oching.",
            link="/saved?tab=viewers",
            marketing=True,
        )
        await asyncio.sleep(SEND_PACING_SECONDS)


def _webapp_keyboard(button_text: str) -> dict:
    return {"inline_keyboard": [[{"text": button_text, "web_app": {"url": get_webapp_url()}}]]}


# Bot /start but Mini App never opened: up to 3 nudges, then silence forever.
# Hours are measured from the FIRST /start.
BOT_NUDGES = [
    (3, "👋 FIDEM'da sizni kutishyapti!\n\n"
        "Anketa yaratish atigi 2 daqiqa — mos nomzodlarni bepul ko'rasiz.\n\n"
        "👇 Bir bosishda oching"),
    (24, "💛 Bugun FIDEM'ga yangi a'zolar qo'shildi.\n\n"
         "Sizga mos insonlar allaqachon qidiryapti. Anketa ochish — bepul."),
    (72, "⏳ Oxirgi eslatma: FIDEM'dagi imkoniyatingiz kutmoqda.\n\n"
         "2 daqiqada anketani to'ldiring — balki taqdiringiz shu yerdadir 💖"),
]

# Account created but the profile was never finished: 2 nudges.
PROFILE_NUDGES = [
    (24, "✍️ Anketangiz chala qoldi.\n\n"
         "Tugatmaguningizcha nomzodlar sizni ko'ra olmaydi. Tugatish — 2 daqiqa!"),
    (72, "💔 Anketangiz hali ham chala.\n\n"
         "A'zolar har kuni juftini topmoqda — siz esa ro'yxatda ko'rinmayapsiz. Hoziroq tugating!"),
]


async def _onboarding_nudges() -> None:
    """Re-engage the two funnel drop-offs: (a) pressed /start in the bot but
    never opened the Mini App, (b) opened it and created an account but left
    the profile unfinished. Each nudge fires once (stage counter), the chain
    is short and then goes silent — no infinite spam."""
    now = now_utc()

    # (a) bot /start, no account yet
    rows = await db.bot_starts.find(
        {"nudge_stage": {"$lt": len(BOT_NUDGES)}},
        {"_id": 0, "telegram_id": 1, "chat_id": 1, "first_start_at": 1, "nudge_stage": 1},
    ).limit(BATCH).to_list(BATCH)
    for s in rows:
        # Opened the app since? Move them off this track for good.
        if await db.users.find_one({"telegram_id": s["telegram_id"]}, {"_id": 1}):
            await db.bot_starts.update_one(
                {"telegram_id": s["telegram_id"]}, {"$set": {"nudge_stage": 99}}
            )
            continue
        stage = s.get("nudge_stage", 0)
        hours_due, text = BOT_NUDGES[stage]
        try:
            started = parse_dt(s["first_start_at"])
        except Exception:
            continue
        if now - started < timedelta(hours=hours_due):
            continue
        # Bump first so a send failure (user blocked the bot etc.) never
        # turns into a retry loop on every pass.
        await db.bot_starts.update_one(
            {"telegram_id": s["telegram_id"], "nudge_stage": stage},
            {"$set": {"nudge_stage": stage + 1, "last_nudge_at": iso(now)}},
        )
        await send_telegram_message(s["chat_id"], text, reply_markup=_webapp_keyboard("💖 FIDEM'ni ochish"))
        await asyncio.sleep(SEND_PACING_SECONDS)

    # (b) account exists, profile unfinished
    rows = await db.users.find(
        {
            "telegram_id": {"$nin": [None, ""]},
            "onboarded": {"$ne": True},
            "blocked": {"$ne": True},
            "profile_nudge_stage": {"$not": {"$gte": len(PROFILE_NUDGES)}},
        },
        {"_id": 0, "id": 1, "telegram_id": 1, "created_at": 1, "profile_nudge_stage": 1},
    ).limit(BATCH).to_list(BATCH)
    for u in rows:
        stage = u.get("profile_nudge_stage", 0) or 0
        hours_due, text = PROFILE_NUDGES[stage]
        try:
            created = parse_dt(u["created_at"])
        except Exception:
            continue
        if now - created < timedelta(hours=hours_due):
            continue
        await db.users.update_one(
            {"id": u["id"]},
            {"$set": {"profile_nudge_stage": stage + 1, "profile_nudge_at": iso(now)}},
        )
        try:
            chat_id = int(u["telegram_id"])
        except (TypeError, ValueError):
            continue
        await send_telegram_message(chat_id, text, reply_markup=_webapp_keyboard("✍️ Anketani tugatish"))
        await asyncio.sleep(SEND_PACING_SECONDS)


async def _admin_daily_digest() -> None:
    """Once per calendar day, push the owner stats (/stats content) to every
    admin's Telegram — signups by hour, actives, pending P2P queue, money."""
    today = now_utc().date().isoformat()
    marker = await db.settings.find_one({"id": "admin_digest"}) or {}
    if marker.get("sent_on") == today:
        return
    await db.settings.update_one(
        {"id": "admin_digest"}, {"$set": {"sent_on": today}}, upsert=True
    )
    from admin_bot import build_stats_text, get_admin_chat_ids

    admins = await get_admin_chat_ids()
    if not admins:
        return
    text = await build_stats_text()
    for chat_id in admins:
        await send_telegram_message(chat_id, text)


async def _cleanup_telegram_updates() -> None:
    """The webhook dedup table (routers/telegram_r.py) only needs to cover
    Telegram's actual retry window, which is minutes not days - drop
    anything older than a day so the collection doesn't grow forever."""
    cutoff = iso(now_utc() - timedelta(days=1))
    await db.telegram_updates.delete_many({"at": {"$lt": cutoff}})


async def _snapshot_daily_stats() -> None:
    """One row/day of the core growth numbers, so the AI insights endpoint
    (routers/admin_r.py) can say '7 kun oldin X edi, hozir Y' instead of only
    ever seeing a single point in time. Idempotent per calendar day via the
    same sent_on-marker pattern as _admin_daily_digest."""
    today = now_utc().date().isoformat()
    if await db.stats_snapshots.find_one({"date": today}, {"_id": 1}):
        return
    now = now_utc()
    today_iso = iso(now - timedelta(days=1))
    week_iso = iso(now - timedelta(days=7))
    month_iso = iso(now - timedelta(days=30))
    total, onboarded, dau, wau, mau, premium, vip = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"onboarded": True}),
        db.users.count_documents({"last_active": {"$gte": today_iso}}),
        db.users.count_documents({"last_active": {"$gte": week_iso}}),
        db.users.count_documents({"last_active": {"$gte": month_iso}}),
        db.users.count_documents({"plan": "premium"}),
        db.users.count_documents({"plan": "vip"}),
    )
    rev = await db.payments.aggregate([
        {"$match": {"status": "success", "created_at": {"$gte": iso(now.replace(hour=0, minute=0, second=0, microsecond=0))}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    await db.stats_snapshots.insert_one({
        "date": today, "total_users": total, "onboarded": onboarded,
        "dau": dau, "wau": wau, "mau": mau, "premium": premium, "vip": vip,
        "revenue_today": (rev[0]["total"] if rev else 0) or 0,
        "created_at": iso(now),
    })


async def _run_pass() -> None:
    await _plan_reminders()
    await _plan_expiry()
    await _daily_picks_push()
    await _weekly_digest()
    await _onboarding_nudges()
    await _admin_daily_digest()
    await _cleanup_telegram_updates()
    await _snapshot_daily_stats()


async def lifecycle_loop() -> None:
    await asyncio.sleep(120)  # let startup settle
    while True:
        try:
            await _run_pass()
        except Exception:
            log.warning("lifecycle pass failed", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
