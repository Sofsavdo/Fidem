"""AI features router — personalized icebreakers and moderation status."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import get_user
from ai_service import personalized_icebreakers

router = APIRouter(tags=["ai"])


@router.get("/ai/icebreakers/{target_id}")
async def ai_icebreakers(target_id: str, lang: str = "uz", uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "Cannot generate for self")
    me = await get_user(uid)
    target = await get_user(target_id)
    questions = await personalized_icebreakers(me, target, lang=lang)
    return {"questions": questions, "ai_generated": True}
