"""Gamification — XP, levels, badges, progression.

XP sources: profile completion, Big5, daily check-in, sending roses/gifts, photos, referrals.
Levels: square-root scaling (xp / 100). Badges: milestone achievements.
"""
from __future__ import annotations
import math
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt

router = APIRouter(tags=["gamification"])

# Daily quests
DAILY_QUESTS = {
    "send_message": {
        "id": "send_message",
        "icon": "💬",
        "uz": "3 ta xabar yuborish",
        "ru": "Отправить 3 сообщения",
        "en": "Send 3 messages",
        "target": 3,
        "xp_reward": 30,
        "coins_reward": 10,
    },
    "view_profiles": {
        "id": "view_profiles",
        "icon": "👀",
        "uz": "5 ta profil ko'rish",
        "ru": "Просмотреть 5 профилей",
        "en": "View 5 profiles",
        "target": 5,
        "xp_reward": 20,
        "coins_reward": 5,
    },
    "save_profile": {
        "id": "save_profile",
        "icon": "❤️",
        "uz": "1 ta profilni saqlash",
        "ru": "Сохранить 1 профиль",
        "en": "Save 1 profile",
        "target": 1,
        "xp_reward": 25,
        "coins_reward": 8,
    },
    "complete_profile": {
        "id": "complete_profile",
        "icon": "✨",
        "uz": "Profilni to'ldirish (90%+)",
        "ru": "Заполнить профиль (90%+)",
        "en": "Complete profile (90%+)",
        "target": 90,
        "xp_reward": 50,
        "coins_reward": 15,
    },
    "send_rose": {
        "id": "send_rose",
        "icon": "🌹",
        "uz": "1 ta atirgul yuborish",
        "ru": "Отправить 1 розу",
        "en": "Send 1 rose",
        "target": 1,
        "xp_reward": 40,
        "coins_reward": 12,
    },
}

# Level titles
LEVEL_TITLES = {
    "uz": ["Yangi a'zo", "Faol qidiruvchi", "Tajribali", "Sovchi-pro", "FIDEM ustasi"],
    "ru": ["Новичок", "Активный", "Опытный", "Сваха-про", "Мастер FIDEM"],
    "en": ["Newcomer", "Active Seeker", "Experienced", "Pro Matchmaker", "FIDEM Master"],
}

# Badge definitions
BADGES = [
    {"id": "b_profile_complete", "icon": "🎯",
     "uz": "Profilim to'liq", "ru": "Профиль заполнен", "en": "Profile Complete",
     "check": lambda u: u.get("onboarded", False) and (u.get("about") or "")},
    {"id": "b_big5_done", "icon": "🧠",
     "uz": "Shaxsiyat aniqlangan", "ru": "Личность определена", "en": "Personality Discovered",
     "check": lambda u: bool(u.get("big5_scores"))},
    {"id": "b_streak_7", "icon": "🔥",
     "uz": "7 kunlik streak", "ru": "Серия 7 дней", "en": "7-Day Streak",
     "check": lambda u: u.get("daily_streak", 0) >= 7},
    {"id": "b_streak_30", "icon": "👑",
     "uz": "30 kunlik streak", "ru": "Серия 30 дней", "en": "30-Day Streak",
     "check": lambda u: u.get("daily_streak", 0) >= 30},
    {"id": "b_verified", "icon": "✅",
     "uz": "Tasdiqlangan", "ru": "Проверенный", "en": "Verified",
     "check": lambda u: u.get("verified_identity", False) or u.get("verified_selfie", False)},
    {"id": "b_financial", "icon": "💎",
     "uz": "Moliyaviy tasdiq", "ru": "Финансовая верификация", "en": "Financially Verified",
     "check": lambda u: u.get("verified_financial", False)},
    {"id": "b_premium", "icon": "⭐",
     "uz": "Premium", "ru": "Premium", "en": "Premium",
     "check": lambda u: u.get("plan") == "premium"},
    {"id": "b_vip", "icon": "👑",
     "uz": "VIP", "ru": "VIP", "en": "VIP",
     "check": lambda u: u.get("plan") == "vip"},
    {"id": "b_first_rose", "icon": "🌹",
     "uz": "Birinchi atirgul", "ru": "Первая роза", "en": "First Rose",
     "check": lambda u: u.get("roses_sent_total", 0) > 0},
    {"id": "b_rose_giver", "icon": "🌷",
     "uz": "Saxiy yurakli", "ru": "Щедрое сердце", "en": "Generous Heart",
     "check": lambda u: u.get("roses_sent_total", 0) >= 5},
    {"id": "b_prompts", "icon": "✍️",
     "uz": "Hikoyalovchi", "ru": "Рассказчик", "en": "Storyteller",
     "check": lambda u: len(u.get("prompts") or []) >= 3},
    {"id": "b_inviter", "icon": "👥",
     "uz": "Do'st chaqirgan", "ru": "Пригласил друга", "en": "Friend Inviter",
     "check": lambda u: u.get("invited_count", 0) > 0},
]


def compute_level(xp: int) -> tuple[int, int, int]:
    """Return (level, xp_in_level, xp_to_next_level).

    Formula: total_xp_for_level_N = 100 * N^2
    => level = floor(sqrt(xp/100))
    """
    xp = max(0, int(xp or 0))
    level = int(math.floor(math.sqrt(xp / 100))) if xp >= 100 else 0
    current_level_xp = 100 * level * level
    next_level_xp = 100 * (level + 1) * (level + 1)
    in_level = xp - current_level_xp
    to_next = next_level_xp - xp
    return level, in_level, to_next


def level_title(level: int, lang: str = "uz") -> str:
    titles = LEVEL_TITLES.get(lang, LEVEL_TITLES["uz"])
    return titles[min(level // 2, len(titles) - 1)]


def get_badges(user: dict, lang: str = "uz") -> list[dict]:
    out = []
    for b in BADGES:
        try:
            achieved = bool(b["check"](user))
        except Exception:
            achieved = False
        out.append({
            "id": b["id"],
            "icon": b["icon"],
            "name": b.get(lang, b["uz"]),
            "achieved": achieved,
        })
    return out


@router.get("/me/progress")
async def my_progress(lang: str = "uz", uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    # Backfill XP if missing — compute from existing actions
    xp = me.get("xp")
    if xp is None:
        xp = _backfill_xp(me)
        await db.users.update_one({"id": uid}, {"$set": {"xp": xp}})
    level, in_level, to_next = compute_level(xp)
    badges = get_badges(me, lang=lang)
    earned = sum(1 for b in badges if b["achieved"])
    return {
        "xp": xp,
        "level": level,
        "title": level_title(level, lang),
        "xp_in_level": in_level,
        "xp_to_next": to_next,
        "progress_pct": round(in_level / max(1, in_level + to_next) * 100),
        "badges": badges,
        "badges_earned": earned,
        "badges_total": len(badges),
    }


def _backfill_xp(user: dict) -> int:
    """Estimate XP based on existing user fields."""
    xp = 0
    if user.get("onboarded"):
        xp += 50
    if user.get("about"):
        xp += 30
    if user.get("big5_scores"):
        xp += 200
    streak = user.get("daily_streak", 0)
    xp += min(streak * 20, 600)
    xp += int(user.get("roses_sent_total", 0)) * 10
    xp += int(user.get("invited_count", 0)) * 100
    if user.get("verified_identity"): xp += 30
    if user.get("verified_selfie"): xp += 40
    if user.get("verified_financial"): xp += 80
    if user.get("plan") == "premium": xp += 100
    if user.get("plan") == "vip": xp += 200
    return xp


# ---------- Daily Quests ----------
@router.get("/quests/daily")
async def daily_quests(lang: str = "uz", uid: str = Depends(get_current_user_id)):
    """Get daily quests and their progress."""
    me = await get_user(uid)
    today = iso(now_utc().replace(hour=0, minute=0, second=0, microsecond=0))
    
    # Get or create today's quest progress
    quest_progress = await db.daily_quests.find_one({"user_id": uid, "date": today})
    if not quest_progress:
        quest_progress = {
            "user_id": uid,
            "date": today,
            "progress": {qid: 0 for qid in DAILY_QUESTS.keys()},
            "claimed": [],
            "created_at": iso(now_utc()),
        }
        await db.daily_quests.insert_one(quest_progress)
    
    # Calculate current progress for each quest
    quests = []
    for qid, quest in DAILY_QUESTS.items():
        current = quest_progress["progress"].get(qid, 0)
        completed = current >= quest["target"]
        claimed = qid in quest_progress["claimed"]
        
        # Special handling for profile completeness quest
        if qid == "complete_profile":
            from services import compute_completeness
            completeness = compute_completeness(me)
            current = completeness
            completed = completeness >= quest["target"]
        
        quests.append({
            "id": qid,
            "icon": quest["icon"],
            "title": quest.get(lang, quest["uz"]),
            "target": quest["target"],
            "current": current,
            "completed": completed,
            "claimed": claimed,
            "xp_reward": quest["xp_reward"],
            "coins_reward": quest["coins_reward"],
        })
    
    return {"date": today, "quests": quests}


@router.post("/quests/{quest_id}/claim")
async def claim_quest_reward(quest_id: str, uid: str = Depends(get_current_user_id)):
    """Claim reward for a completed daily quest."""
    if quest_id not in DAILY_QUESTS:
        raise HTTPException(404, "Quest not found")
    
    me = await get_user(uid)
    today = iso(now_utc().replace(hour=0, minute=0, second=0, microsecond=0))
    
    quest_progress = await db.daily_quests.find_one({"user_id": uid, "date": today})
    if not quest_progress:
        raise HTTPException(404, "No quest progress for today")
    
    if quest_id in quest_progress["claimed"]:
        raise HTTPException(400, "Already claimed")
    
    quest = DAILY_QUESTS[quest_id]
    current = quest_progress["progress"].get(quest_id, 0)
    
    # Special check for profile completeness
    if quest_id == "complete_profile":
        from services import compute_completeness
        current = compute_completeness(me)
    
    if current < quest["target"]:
        raise HTTPException(400, "Quest not completed")
    
    # Grant rewards
    await db.users.update_one(
        {"id": uid},
        {"$inc": {"xp": quest["xp_reward"], "coins": quest["coins_reward"]},
         "$set": {"daily_quests_last_claimed": iso(now_utc())}},
    )
    
    # Mark as claimed
    await db.daily_quests.update_one(
        {"user_id": uid, "date": today},
        {"$push": {"claimed": quest_id}},
    )
    
    return {
        "ok": True,
        "xp_gained": quest["xp_reward"],
        "coins_gained": quest["coins_reward"],
    }


@router.post("/quests/track")
async def track_quest_progress(quest_id: str, increment: int = 1, uid: str = Depends(get_current_user_id)):
    """Track progress for a daily quest (internal use by other endpoints)."""
    if quest_id not in DAILY_QUESTS:
        return {"ok": False, "error": "Invalid quest"}
    
    today = iso(now_utc().replace(hour=0, minute=0, second=0, microsecond=0))
    
    await db.daily_quests.update_one(
        {"user_id": uid, "date": today},
        {"$inc": {f"progress.{quest_id}": increment}},
        upsert=True,
    )
    
    return {"ok": True}
