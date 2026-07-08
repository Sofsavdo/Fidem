"""Gamification — XP, levels, badges, progression.

XP sources: profile completion, Big5, daily check-in, sending gifts, photos, referrals.
Levels: square-root scaling (xp / 100). Badges: milestone achievements.
"""
from __future__ import annotations
import math
from fastapi import APIRouter, Depends

from auth import get_current_user_id
from core import db, get_user

router = APIRouter(tags=["gamification"])

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
    xp += int(user.get("invited_count", 0)) * 100
    if user.get("verified_identity"): xp += 30
    if user.get("verified_selfie"): xp += 40
    if user.get("verified_financial"): xp += 80
    if user.get("plan") == "premium": xp += 100
    if user.get("plan") == "vip": xp += 200
    return xp
