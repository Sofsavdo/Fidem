"""User settings management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import PAID_PLANS, db, get_user, iso, now_utc
from models import NotificationPreferencesRequest, PrivacySettingsRequest

router = APIRouter(tags=["settings"])


@router.get("/settings/notifications")
async def get_notification_preferences(uid: str = Depends(get_current_user_id)):
    """Get user's notification preferences."""
    me = await get_user(uid)
    prefs = me.get("notification_prefs", {})
    
    return {
        "disable_general": prefs.get("disable_general", False),
        "disable_match": prefs.get("disable_match", False),
        "disable_message": prefs.get("disable_message", False),
        "disable_premium": prefs.get("disable_premium", False),
        "disable_community": prefs.get("disable_community", False),
        "disable_referral": prefs.get("disable_referral", False),
        "disable_balance": prefs.get("disable_balance", False),
    }


@router.post("/settings/notifications")
async def update_notification_preferences(req: NotificationPreferencesRequest, uid: str = Depends(get_current_user_id)):
    """Update user's notification preferences."""
    prefs = {
        "disable_general": req.disable_general,
        "disable_match": req.disable_match,
        "disable_message": req.disable_message,
        "disable_premium": req.disable_premium,
        "disable_community": req.disable_community,
        "disable_referral": req.disable_referral,
        "disable_balance": req.disable_balance,
    }
    
    await db.users.update_one(
        {"id": uid},
        {"$set": {"notification_prefs": prefs}}
    )

    return {"ok": True, "preferences": prefs}


# ---------- Privacy (photo visibility + hidden profile) ----------
@router.get("/settings/privacy")
async def get_privacy_settings(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    boost_active = bool(me.get("boost_until") and me["boost_until"] > iso(now_utc()))
    return {
        "photo_public": bool(me.get("photo_public", False)),
        "hidden_profile": bool(me.get("hidden_profile", False)),
        "boost_active": boost_active,
    }


@router.post("/settings/privacy")
async def update_privacy_settings(req: PrivacySettingsRequest, uid: str = Depends(get_current_user_id)):
    """Update photo visibility and/or hidden-profile mode.

    Hidden mode is a PAID, plan-tiered feature (see INCOGNITO_PLANS in
    core.py): standard hides the profile, premium also makes visits
    incognito, vip additionally unlocks /photo-peek. Free users get a 403
    that the frontend turns into a plan upsell.

    Hidden profile and boost are mutually exclusive by design: boost sells
    visibility, hiding removes all of it, so paying for both at once is
    always a mistake. The boost side of the same rule lives in
    growth_r.boost_activate / payments_r.create_payment ("boost_hidden").
    """
    me = await get_user(uid)
    updates: dict = {}
    if req.photo_public is not None:
        updates["photo_public"] = bool(req.photo_public)
    if req.hidden_profile is not None:
        plan = me.get("plan", "free")
        now_iso = iso(now_utc())
        boost_until = me.get("boost_until") or ""
        boost_active = bool(boost_until and boost_until > now_iso)
        # Premium/VIP bundle a boost that lasts exactly as long as the plan
        # (boost_until == plan_until). That bundled boost must not lock the
        # plan's own privacy perks (hidden mode / incognito) - only a boost the
        # user bought separately conflicts with hiding.
        bundled_boost = boost_active and plan in ("premium", "vip") and boost_until == me.get("plan_until")
        if req.hidden_profile:
            if plan not in PAID_PLANS:
                raise HTTPException(403, "privacy_requires_plan")
            if boost_active and not bundled_boost:
                # An active (paid) boost would keep charging for zero visibility.
                raise HTTPException(400, "privacy_boost_active")
            if bundled_boost:
                updates["boost_until"] = ""  # paused while invisible
        elif me.get("hidden_profile") and plan in ("premium", "vip") and (me.get("plan_until") or "") > now_iso:
            # Visible again: hand back the boost that comes with the plan.
            updates["boost_until"] = me["plan_until"]
        updates["hidden_profile"] = bool(req.hidden_profile)
    if updates:
        await db.users.update_one({"id": uid}, {"$set": updates})
    merged = {**me, **updates}
    return {
        "ok": True,
        "photo_public": bool(merged.get("photo_public", False)),
        "hidden_profile": bool(merged.get("hidden_profile", False)),
    }
