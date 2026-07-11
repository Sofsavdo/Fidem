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

from core import PAID_PLANS, db, iso, now_utc, parse_dt, push_notif

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


async def _run_pass() -> None:
    await _plan_reminders()
    await _plan_expiry()
    await _daily_picks_push()
    await _weekly_digest()


async def lifecycle_loop() -> None:
    await asyncio.sleep(120)  # let startup settle
    while True:
        try:
            await _run_pass()
        except Exception:
            log.warning("lifecycle pass failed", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
