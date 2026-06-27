"""Travel mode — temporarily browse candidates in another region (Premium+)."""
from __future__ import annotations

from datetime import timedelta
from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt

router = APIRouter(prefix="/travel", tags=["travel"])

MAX_DAYS = 30
MIN_DAYS = 1

# Available regions in Uzbekistan
UZ_REGIONS = [
    "Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan",
    "Qashqadaryo", "Surxondaryo", "Sirdaryo", "Jizzax", "Navoiy", "Xorazm", "Qoraqalpog'iston",
]


@router.get("/status")
async def travel_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    until = me.get("travel_until")
    active = False
    if until:
        try:
            active = parse_dt(until) > now_utc()
        except Exception:
            active = False
    return {
        "active": active,
        "travel_region": me.get("travel_region") if active else None,
        "travel_until": until if active else None,
        "home_region": me.get("region"),
        "plan": me.get("plan", "free"),
        "allowed": me.get("plan") in ("premium", "vip"),
        "regions": UZ_REGIONS,
    }


@router.post("/activate")
async def activate_travel(
    region: str = Body(..., embed=True),
    days: int = Body(7, embed=True),
    uid: str = Depends(get_current_user_id),
):
    me = await get_user(uid)
    if me.get("plan") not in ("premium", "vip"):
        raise HTTPException(403, "Travel Mode faqat Premium/VIP foydalanuvchilar uchun")
    if region not in UZ_REGIONS:
        raise HTTPException(400, "Noto'g'ri viloyat")
    if region == me.get("region"):
        raise HTTPException(400, "Bu sizning hozirgi viloyatingiz — Travel Mode kerak emas")
    if days < MIN_DAYS or days > MAX_DAYS:
        raise HTTPException(400, f"Kunlar soni {MIN_DAYS}-{MAX_DAYS} oraliqda bo'lishi kerak")
    until = iso(now_utc() + timedelta(days=days))
    await db.users.update_one(
        {"id": uid},
        {"$set": {"travel_region": region, "travel_until": until, "travel_activated_at": iso(now_utc())}},
    )
    return {"ok": True, "travel_region": region, "travel_until": until}


@router.post("/deactivate")
async def deactivate_travel(uid: str = Depends(get_current_user_id)):
    await db.users.update_one(
        {"id": uid},
        {"$unset": {"travel_region": "", "travel_until": ""}},
    )
    return {"ok": True}
