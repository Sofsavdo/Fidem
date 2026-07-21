"""Referral cash-earning release: promotes paid-subscription referral
earnings from "pending" to "withdrawable" once their fraud-buffer hold
expires.

Runs as a background loop started at app startup - no external cron needed
(same pattern as winback.py / lifecycle.py).

Before this module existed, nothing anywhere transitioned an earning out of
"pending" - `hold_until` was written on every earning record but never read,
so `referral_earnings_withdrawable` stayed 0 forever for every user and the
"kamida 3 ta to'langan taklif" withdrawal gate (which counts earnings whose
status is in ("approved","withdrawable","paid")) could never be satisfied
either. Referrers were earning money they could mathematically never
withdraw.

Free-signup ("signup_free") earnings are NOT released here - they are
credited straight to the user's internal, non-withdrawable `balance` at
signup time (see auth_r.py's /profile/onboard) since they carry no real-cash
liability, so they never sit in "pending" waiting for this loop.
"""
from __future__ import annotations

import asyncio
import logging

from core import db, iso, now_utc, push_notif

log = logging.getLogger("fidem")

CHECK_INTERVAL_SECONDS = 60 * 60  # hourly - hold windows are measured in days


async def _release_once() -> tuple[int, int]:
    now_iso = iso(now_utc())
    query = {
        "referral_earnings": {
            "$elemMatch": {"status": "pending", "type": "paid_subscription", "hold_until": {"$lte": now_iso}}
        }
    }
    released = 0
    rejected = 0
    async for user in db.users.find(query, {"_id": 0, "id": 1, "blocked": 1, "flagged_as_bot": 1, "referral_earnings": 1}):
        for earning in user.get("referral_earnings", []):
            if earning.get("status") != "pending" or earning.get("type") != "paid_subscription":
                continue
            hold_until = earning.get("hold_until")
            if not hold_until or hold_until > now_iso:
                continue

            amount = int(earning.get("net_amount") or earning.get("amount") or 0)
            invitee = await db.users.find_one(
                {"id": earning.get("referred_user_id")}, {"_id": 0, "blocked": 1, "flagged_as_bot": 1}
            )
            # Re-check fraud signals at release time, not just at earn time -
            # an inviter or invitee flagged/blocked in the days since the
            # earning was recorded should not have it silently cash out.
            fraud_detected = bool(
                user.get("blocked")
                or user.get("flagged_as_bot")
                or (invitee and (invitee.get("blocked") or invitee.get("flagged_as_bot")))
            )
            new_status = "rejected" if fraud_detected else "withdrawable"

            res = await db.users.update_one(
                {"id": user["id"], "referral_earnings.id": earning["id"], "referral_earnings.status": "pending"},
                {
                    "$set": {
                        "referral_earnings.$.status": new_status,
                        "referral_earnings.$.approved_at": None if fraud_detected else now_iso,
                        "referral_earnings.$.rejected_at": now_iso if fraud_detected else None,
                        "referral_earnings.$.rejection_reason": "fraud_check_failed" if fraud_detected else None,
                    }
                },
            )
            if res.modified_count == 0:
                continue  # lost a race with something else touching this earning

            inc: dict = {"referral_earnings_pending": -amount}
            if fraud_detected:
                rejected += 1
            else:
                inc["referral_earnings_withdrawable"] = amount
                released += 1
            await db.users.update_one({"id": user["id"]}, {"$inc": inc})

            if not fraud_detected:
                await push_notif(
                    user["id"],
                    "referral",
                    f"🎉 {amount:,} so'm yechib olish uchun tayyor - referalingiz to'lovi tasdiqlandi!",
                )
    return released, rejected


async def referral_release_loop() -> None:
    while True:
        try:
            released, rejected = await _release_once()
            if released or rejected:
                log.info(f"referral earnings: released {released}, rejected {rejected}")
        except Exception as e:
            log.warning(f"referral release loop error: {e}")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
