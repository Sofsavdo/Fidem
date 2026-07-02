"""User settings management."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import get_current_user_id
from core import db, get_user
from models import NotificationPreferencesRequest

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
