"""Automated re-engagement (win-back) notifications for inactive users.

Runs as a background loop started at app startup - no external cron needed.
A per-user `last_winback_sent_at` cooldown keeps any one user from being
pinged more than once every COOLDOWN_DAYS; the message shown is picked by
how long they've actually been gone *at send time* (not a stored
progression), so a user who comes back and goes quiet again starts over at
the gentle tier instead of wherever they left off last time.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from core import db, iso, now_utc, parse_dt, push_notif

log = logging.getLogger("fidem")

CHECK_INTERVAL_SECONDS = 6 * 60 * 60  # every 6 hours
COOLDOWN_DAYS = 4  # don't re-ping the same user more often than this

# (days_inactive_threshold, kind, text, link) - checked longest-gone first,
# so someone gone 20 days gets the tier-3 message, not tier-1.
TIERS = [
    (14, "winback_3", "😢 FIDEM'da sizni sog'inishdi. Profilingiz sizni kutmoqda - 3 daqiqada qaytib keling.", "/"),
    (7, "winback_2", "💌 Kimdir profilingizga qiziqqan bo'lishi mumkin - qaytib ko'rmaysizmi?", "/saved?tab=interested"),
    (3, "winback_1", "👋 Sizni sog'indik! Shu vaqt ichida yangi profillar qo'shildi - orasida sizga mos kimdir bo'lishi mumkin.", "/"),
]


async def _run_once() -> int:
    now = now_utc()
    min_days = min(t[0] for t in TIERS)
    inactive_cutoff = iso(now - timedelta(days=min_days))
    cooldown_cutoff = iso(now - timedelta(days=COOLDOWN_DAYS))

    query = {
        "onboarded": True,
        "blocked": {"$ne": True},
        "last_active": {"$lt": inactive_cutoff},
        "$or": [
            {"last_winback_sent_at": {"$exists": False}},
            {"last_winback_sent_at": {"$lt": cooldown_cutoff}},
        ],
    }
    sent = 0
    async for u in db.users.find(query, {"_id": 0, "id": 1, "last_active": 1}):
        try:
            days_inactive = (now - parse_dt(u["last_active"])).days
        except Exception:
            continue
        tier = next((t for t in TIERS if days_inactive >= t[0]), None)
        if not tier:
            continue
        _, kind, text, link = tier
        ok = await push_notif(u["id"], kind, text, link=link, marketing=True)
        if ok:
            await db.users.update_one({"id": u["id"]}, {"$set": {"last_winback_sent_at": iso(now)}})
            sent += 1
    return sent


async def winback_loop() -> None:
    while True:
        try:
            sent = await _run_once()
            if sent:
                log.info(f"winback: sent {sent} re-engagement notifications")
        except Exception as e:
            log.warning(f"winback loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
