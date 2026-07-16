"""Growth & monetization features: boost, daily check-in, quiz, icebreakers, invites."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt, push_notif, user_public
from models import new_id

router = APIRouter(tags=["growth"])

# Pricing
BOOST_PRICE = 5000        # 24h boost in UZS (deducts from balance or paid via CLICK)
# Daily check-in rewards are paid in so'm into the internal `balance` (spendable
# on gifts/boost/plans, NOT withdrawable — only referral earnings withdraw).
# The reward DOUBLES each consecutive day (100 → 6,400 by day 7) and stays at
# 6,400 while the chain holds; missing a day drops it back to 100. A flat
# daily amount gave no reason to come back tomorrow — losing tomorrow's
# bigger bonus does.
STREAK_REWARDS = [100, 200, 400, 800, 1600, 3200, 6400]


def _streak_reward(day: int) -> int:
    """Reward for the given consecutive day (day 7+ stays at the max)."""
    return STREAK_REWARDS[min(max(day, 1), len(STREAK_REWARDS)) - 1]


# ---------- Daily check-in / Streak ----------
@router.get("/daily/status")
async def daily_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    last = me.get("daily_last_at")
    streak = me.get("daily_streak", 0)
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso = iso(today)
    yesterday_iso = iso(today - timedelta(days=1))
    claimed_today = last is not None and last >= today_iso
    # The day the NEXT claim will count as: chain continues from yesterday,
    # otherwise it restarts at day 1.
    chain_alive = bool(last and last >= yesterday_iso)
    next_streak = (streak + 1) if chain_alive else 1
    return {
        "claimed_today": claimed_today,
        "streak": streak,
        "next_streak": next_streak,
        "next_bonus": 0 if claimed_today else _streak_reward(next_streak),
        "tomorrow_bonus": _streak_reward(streak + 1 if claimed_today else next_streak + 1),
        "max_bonus": STREAK_REWARDS[-1],
        "rewards": STREAK_REWARDS,
        "currency": "sum",
        "balance": int(me.get("balance", 0) or 0),
    }


@router.post("/daily/claim")
async def daily_claim(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso_str = iso(today)
    yesterday_iso = iso(today - timedelta(days=1))
    last = me.get("daily_last_at")
    if last and last >= today_iso_str:
        raise HTTPException(400, "Bugun olingan")
    # Streak math: consecutive day continues the chain, a gap restarts it
    streak = me.get("daily_streak", 0)
    if last and last >= yesterday_iso:
        streak += 1
    else:
        streak = 1
    bonus = _streak_reward(streak)
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {"daily_last_at": iso(now_utc()), "daily_streak": streak},
            "$inc": {"balance": bonus, "xp": 20 + (50 if streak % 7 == 0 else 0)},
        },
    )
    await push_notif(uid, "balance", f"🔥 {streak} kunlik streak! +{bonus:,} so'm balansingizga tushdi. Ertaga: +{_streak_reward(streak + 1):,} so'm")
    return {
        "streak": streak,
        "bonus": bonus,
        "tomorrow_bonus": _streak_reward(streak + 1),
        "currency": "sum",
        "balance_after": int(me.get("balance", 0) or 0) + bonus,
    }


# ---------- Profile Boost (24h 5x visibility) ----------
@router.get("/boost/status")
async def boost_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    until = me.get("boost_until")
    active = bool(until and parse_dt(until) > now_utc())
    return {"active": active, "until": until, "price": BOOST_PRICE}


@router.post("/boost/activate")
async def boost_activate(request: Request, use_balance: bool = Body(True, embed=True), uid: str = Depends(get_current_user_id)):
    """Activate 24h boost. If use_balance=True, deduct from balance; otherwise client should redirect to CLICK payment."""
    # Boost is pure visibility; a hidden profile has none to multiply. Refuse
    # instead of silently taking money for nothing (settings_r enforces the
    # mirror rule: can't hide while a paid boost is running).
    me_check = await get_user(uid)
    if me_check.get("hidden_profile"):
        raise HTTPException(400, "boost_hidden")
    if not use_balance:
        # Route through the boost payment purpose so completing the CLICK
        # payment actually activates the boost (this used to create a plain
        # balance_topup, which paid money in but never started the boost).
        from routers.payments_r import create_payment
        from models import CreatePaymentRequest
        return await create_payment(CreatePaymentRequest(purpose="boost"), request, uid=uid)
    me = await get_user(uid)
    until = now_utc() + timedelta(hours=24)
    res = await db.users.update_one(
        {"id": uid, "balance": {"$gte": BOOST_PRICE}},
        {
            "$set": {
                "boost_until": iso(until),
                "boost_metrics.started_at": iso(now_utc()),
                "boost_metrics.impressions": 0,
                "boost_metrics.views": 0,
                "boost_metrics.likes": 0,
                "boost_metrics.messages": 0,
            },
            "$inc": {"balance": -BOOST_PRICE},
        },
    )
    if res.modified_count == 0:
        raise HTTPException(402, f"Need {BOOST_PRICE:,} so'm balance")
    await push_notif(uid, "boost", "Profile Boost faollashtirildi — 24 soat 5x ko'proq ko'rinish 🚀")
    return {"active": True, "until": iso(until), "balance_after": me.get("balance", 0) - BOOST_PRICE}


# ---------- Icebreaker prompts ----------
ICEBREAKERS_UZ = [
    "Sizning eng yoqimli xotirangiz qaysi?",
    "Hayotda 3 ta eng muhim narsa nima?",
    "Idealdagi dam olish kuni qanday o'tadi?",
    "Qaysi kitob/film sizga juda ta'sir qildi?",
    "Bo'sh vaqtingizda nima qilishni yoqtirasiz?",
    "Eng katta orzuingiz nima?",
    "Oilada nima eng muhim deb o'ylaysiz?",
    "Hayotda eng katta yutuq qaysi?",
    "Qayerda yashashni xohlaysiz?",
    "Eng yaxshi maslahatchingiz kim?",
]
ICEBREAKERS_RU = [
    "Какое ваше любимое воспоминание?",
    "Три самые важные вещи в жизни?",
    "Как выглядит идеальный выходной?",
    "Какая книга/фильм на вас сильнее всего повлияли?",
    "Чем любите заниматься в свободное время?",
    "Какая ваша самая большая мечта?",
    "Что самое важное в семье?",
    "Самое большое достижение в жизни?",
    "Где бы хотели жить?",
    "Кто ваш лучший советчик?",
]
ICEBREAKERS_EN = [
    "What's your favorite memory?",
    "Three most important things in life?",
    "What does your ideal day off look like?",
    "Which book/film impacted you the most?",
    "What do you like to do in free time?",
    "What's your biggest dream?",
    "What matters most in family?",
    "Your biggest achievement so far?",
    "Where would you want to live?",
    "Who's your best advisor?",
]


@router.get("/icebreakers")
async def icebreakers(lang: str = "uz"):
    pool = {"ru": ICEBREAKERS_RU, "en": ICEBREAKERS_EN}.get(lang, ICEBREAKERS_UZ)
    return pool


# ---------- Referral Username System (Phase 1.4) ----------
@router.get("/referral/username/available/{username}")
async def check_username_available(username: str):
    """Check if a referral username is available."""
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(400, "Username must be 3-30 characters")
    
    # Check allowed characters (a-z, 0-9, _)
    if not all(c.isalnum() or c == "_" for c in username):
        raise HTTPException(400, "Username can only contain a-z, 0-9, and _")
    
    # Check reserved names
    reserved = ["admin", "api", "www", "fidem", "support", "help"]
    if username.lower() in reserved:
        raise HTTPException(400, "This username is reserved")
    
    # Check if already taken
    existing = await db.referral_usernames.find_one({"username_lower": username.lower()})
    if existing:
        raise HTTPException(400, "Username already taken")
    
    return {"available": True}


@router.get("/referral/username/status")
async def username_status(uid: str = Depends(get_current_user_id)):
    """Get current username and change count."""
    me = await get_user(uid)
    return {
        "referral_username": me.get("referral_username"),
        "referral_id": me.get("referral_id") or uid[:8],
        "change_count": me.get("referral_username_change_count", 0),
        "last_changed": me.get("referral_username_last_changed"),
    }


@router.post("/referral/username/set")
async def set_username(
    username: str = Body(..., embed=True),
    uid: str = Depends(get_current_user_id),
):
    """Set custom referral username. First change is free, subsequent changes cost 10,000 so'm."""
    if len(username) < 3 or len(username) > 30:
        raise HTTPException(400, "Username must be 3-30 characters")
    
    # Check allowed characters (a-z, 0-9, _)
    if not all(c.isalnum() or c == "_" for c in username):
        raise HTTPException(400, "Username can only contain a-z, 0-9, and _")
    
    # Check reserved names
    reserved = ["admin", "api", "www", "fidem", "support", "help"]
    if username.lower() in reserved:
        raise HTTPException(400, "This username is reserved")
    
    me = await get_user(uid)
    change_count = me.get("referral_username_change_count", 0)
    last_changed = me.get("referral_username_last_changed")
    
    # Check cooldown (30 days between changes)
    if last_changed and change_count > 0:
        days_since_change = (now_utc() - parse_dt(last_changed)).days
        if days_since_change < 30:
            raise HTTPException(400, f"Wait {30 - days_since_change} days before changing username again")
    
    # Check if already taken (atomic check with unique index fallback)
    existing = await db.referral_usernames.find_one({"username_lower": username.lower()})
    if existing and existing["user_id"] != uid:
        raise HTTPException(400, "Username already taken")
    
    # Check if user already has this username
    if me.get("referral_username_lower") == username.lower():
        raise HTTPException(400, "You already have this username")

    username_lower = username.lower()

    # Charge for subsequent changes (10,000 so'm)
    if change_count > 0:
        res = await db.users.update_one(
            {"id": uid, "balance": {"$gte": 10000}},
            {"$inc": {"balance": -10000}}
        )
        if res.modified_count == 0:
            raise HTTPException(400, "Insufficient balance. Username change costs 10,000 so'm")

    # Atomic swap: remove old reservation, claim new one
    try:
        if me.get("referral_username_lower"):
            await db.referral_usernames.delete_one({"username_lower": me["referral_username_lower"]})

        await db.referral_usernames.update_one(
            {"user_id": uid},
            {"$set": {"username_lower": username_lower}},
            upsert=True
        )
    except Exception:
        # Handle duplicate key error from race condition
        raise HTTPException(400, "Username already taken")

    # Update user document
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {
                "referral_username": username,
                "referral_username_lower": username_lower,
                "referral_username_change_count": change_count + 1,
                "referral_username_last_changed": iso(now_utc())
            }
        }
    )
    
    return {
        "ok": True,
        "username": username,
        "change_count": change_count + 1,
        "cost": 0 if change_count == 0 else 10000
    }
