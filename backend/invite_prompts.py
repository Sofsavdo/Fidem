"""Invite-a-friend: the bonus, and the notification that offers it.

Bonus (real, immediate, capped):
- the friend finishes their profile -> the inviter gets BONUS_DAYS_PER_FRIEND
  days of Premium (on top of the 100 so'm balance that was already there),
  up to BONUS_DAYS_CAP days in total per inviter;
- the friend later buys Premium -> the old cash reward (half of the payment,
  paid after a 14-day hold) still applies. That part lives in payments_r.py.

The notification must not turn into spam, so every prompt goes through
`maybe_prompt`, which enforces:
- at most MAX_PROMPTS prompts per person, ever;
- at least MIN_GAP_DAYS between two prompts (the old one-time "referral
  awareness" push counts as one);
- nothing for people who already take part (they have referral earnings),
  and nothing once the bonus cap is used up (the offer would be empty);
- the shared marketing cap in core.push_notif (2 per 24 hours) on top;
- prompts are tied to good moments (a new match, a few days of use), never
  to a timer alone, and the timed one only runs in daytime in Uzbekistan.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import timedelta

import core
from core import iso, now_utc, parse_dt

log = logging.getLogger("fidem.invite")

BONUS_DAYS_PER_FRIEND = int(os.environ.get("INVITE_BONUS_DAYS", "2"))
BONUS_DAYS_CAP = int(os.environ.get("INVITE_BONUS_MAX_DAYS", "14"))
MAX_PROMPTS = 3
MIN_GAP_DAYS = 14

_TEXTS = {
    "lifecycle": (
        "🎁 Do'stingizni FIDEM'ga taklif qiling: u profilini to'ldirsa — sizga +{days} kun Premium, "
        "Premium olsa — to'lovning yarmi ham sizga. Havola shu yerda 👇"
    ),
    "match": (
        "💞 Moslik topildi! Do'stingiz ham o'z yarmini shu yerda topsin: u profilini to'ldirsa — "
        "sizga +{days} kun Premium 🎁"
    ),
}

_FIELDS = {
    "_id": 0, "id": 1, "onboarded": 1, "blocked": 1, "is_ai": 1, "invite_prompt_at": 1,
    "invite_prompt_count": 1, "referral_awareness_sent_at": 1, "referral_earnings": 1, "invite_bonus_days": 1,
}


def bonus_left(user: dict) -> int:
    return max(0, BONUS_DAYS_CAP - int(user.get("invite_bonus_days") or 0))


def _last_prompt(user: dict):
    stamps = [parse_dt(s) for s in (user.get("invite_prompt_at"), user.get("referral_awareness_sent_at")) if s]
    return max(stamps) if stamps else None


def eligible(user: dict | None) -> bool:
    if not user or not user.get("onboarded") or user.get("blocked") or user.get("is_ai"):
        return False
    if int(user.get("invite_prompt_count") or 0) >= MAX_PROMPTS:
        return False
    if user.get("referral_earnings"):          # already takes part
        return False
    if bonus_left(user) <= 0:
        return False
    last = _last_prompt(user)
    return not (last and now_utc() - last < timedelta(days=MIN_GAP_DAYS))


async def maybe_prompt(uid: str, trigger: str) -> bool:
    """Send the invite prompt if the rules allow it. Never raises."""
    try:
        user = await core.db.users.find_one({"id": uid}, _FIELDS)
        if not eligible(user):
            return False
        text = _TEXTS[trigger].format(days=BONUS_DAYS_PER_FRIEND)
        now = now_utc()
        # Claim first, atomically: two triggers firing together send one prompt.
        prev = user.get("invite_prompt_at")
        claimed = await core.db.users.update_one(
            {"id": uid, "invite_prompt_at": prev} if prev else {"id": uid, "invite_prompt_at": {"$exists": False}},
            {"$set": {"invite_prompt_at": iso(now)}, "$inc": {"invite_prompt_count": 1}},
        )
        if not claimed.modified_count:
            return False
        sent = await core.push_notif(uid, "referral", text, link="/referral", marketing=True)
        if not sent:                           # hit the daily marketing cap: give the slot back
            undo = {"$inc": {"invite_prompt_count": -1}}
            undo["$set" if prev else "$unset"] = {"invite_prompt_at": prev if prev else ""}
            await core.db.users.update_one({"id": uid}, undo)
        return bool(sent)
    except Exception:
        log.warning("invite prompt failed", exc_info=True)
        return False


async def grant_friend_bonus(inviter_id: str) -> int:
    """Premium days for an inviter whose friend finished the profile. Returns
    the days granted (0 when the cap is used up). An active plan is never cut
    short: the days are added to it; with no active plan Premium starts now."""
    inviter = await core.db.users.find_one(
        {"id": inviter_id}, {"_id": 0, "plan": 1, "plan_until": 1, "invite_bonus_days": 1},
    )
    if inviter is None:          # {} is a real user who simply has no plan yet
        return 0
    days = min(BONUS_DAYS_PER_FRIEND, bonus_left(inviter))
    if days <= 0:
        return 0
    now = now_utc()
    until = inviter.get("plan_until")
    active = bool(until and parse_dt(until) > now)
    if active and inviter.get("plan") in ("standard", "premium", "vip"):
        plan, start = inviter["plan"], parse_dt(until)    # add to what they already have
    else:
        plan, start = "premium", now
    await core.db.users.update_one(
        {"id": inviter_id},
        {"$set": {"plan": plan, "plan_until": iso(start + timedelta(days=days))},
         "$inc": {"invite_bonus_days": days}},
    )
    return days


MATCH_PROMPT_DELAY = 120.0   # seconds: after the match notification itself, not on top of it


def prompt_after_match(*uids: str, delay: float = MATCH_PROMPT_DELAY) -> None:
    """A new match is the best moment to ask: both people just had good news."""
    async def later():
        await asyncio.sleep(delay)
        for uid in uids:
            await maybe_prompt(uid, "match")
    asyncio.ensure_future(later())
