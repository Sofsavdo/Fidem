"""Travel mode — temporarily browse candidates in another region (Premium+)."""
from __future__ import annotations

from datetime import timedelta
from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt

router = APIRouter(prefix="/travel", tags=["travel"])

MAX_DAYS = 30
MIN_DAYS = 1

# Available regions in Uzbekistan (legacy - for backward compatibility)
UZ_REGIONS = [
    "Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan",
    "Qashqadaryo", "Surxondaryo", "Sirdaryo", "Jizzax", "Navoiy", "Xorazm", "Qoraqalpog'iston",
]

# Countries list (for future global expansion - currently only Uzbekistan)
COUNTRIES = [
    {"code": "UZ", "name": "Uzbekistan", "name_uz": "O'zbekiston", "name_ru": "Узбекистан"},
]

# City list per country (for future expansion - currently Uzbekistan cities)
CITIES_BY_COUNTRY = {
    "UZ": [
        "Toshkent", "Samarqand", "Buxoro", "Andijon", "Farg'ona", "Namangan",
        "Qashqadaryo", "Surxondaryo", "Sirdaryo", "Jizzax", "Navoiy", "Xorazm", "Qoraqalpog'iston",
    ],
}


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
    # Backward compatibility: if travel_country is missing, assume Uzbekistan
    travel_country = me.get("travel_country") or "UZ"
    return {
        "active": active,
        "travel_country": travel_country if active else None,
        "travel_region": me.get("travel_region") if active else None,
        "travel_city": me.get("travel_city") if active else None,
        "travel_until": until if active else None,
        "home_region": me.get("region"),
        "plan": me.get("plan", "free"),
        "allowed": me.get("plan") in ("premium", "vip"),
        "regions": UZ_REGIONS,  # Legacy regions list for backward compatibility
        "countries": COUNTRIES,  # New countries list for future expansion
        "cities_by_country": CITIES_BY_COUNTRY,  # Cities per country
    }


@router.post("/activate")
async def activate_travel(
    region: str = Body(None, embed=True),
    country: str = Body(None, embed=True),
    city: str = Body(None, embed=True),
    days: int = Body(7, embed=True),
    uid: str = Depends(get_current_user_id),
):
    me = await get_user(uid)
    if me.get("plan") not in ("premium", "vip"):
        raise HTTPException(403, "Travel Mode faqat Premium/VIP foydalanuvchilar uchun")
    
    # Backward compatibility: if country not provided, default to Uzbekistan
    travel_country = country or "UZ"
    travel_region = region or city  # For legacy, region is required; for new, city may be used
    
    # Validate country (currently only Uzbekistan supported)
    if travel_country != "UZ":
        raise HTTPException(400, "Hozircha faqat O'zbekiston qo'llab-quvvatlanadi")
    
    # Validate region/city against Uzbekistan regions
    if travel_region not in UZ_REGIONS:
        raise HTTPException(400, "Noto'g'ri viloyat/shahar")
    
    if travel_region == me.get("region"):
        raise HTTPException(400, "Bu sizning hozirgi viloyatingiz — Travel Mode kerak emas")
    
    if days < MIN_DAYS or days > MAX_DAYS:
        raise HTTPException(400, f"Kunlar soni {MIN_DAYS}-{MAX_DAYS} oraliqda bo'lishi kerak")
    
    until = iso(now_utc() + timedelta(days=days))
    
    # Set new fields (travel_country, travel_city) while keeping legacy travel_region
    update_data = {
        "travel_country": travel_country,
        "travel_region": travel_region,
        "travel_city": city or travel_region,  # If city not provided, use region as city
        "travel_until": until,
        "travel_activated_at": iso(now_utc()),
    }
    await db.users.update_one(
        {"id": uid},
        {"$set": update_data},
    )
    return {"ok": True, "travel_country": travel_country, "travel_region": travel_region, "travel_city": city or travel_region, "travel_until": until}


@router.post("/deactivate")
async def deactivate_travel(uid: str = Depends(get_current_user_id)):
    await db.users.update_one(
        {"id": uid},
        {"$unset": {"travel_country": "", "travel_region": "", "travel_city": "", "travel_until": ""}},
    )
    return {"ok": True}
