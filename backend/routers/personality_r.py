"""Personality (Big 5 / OCEAN) routes."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from big5 import (
    TRAIT_LABELS,
    big5_compatibility,
    compute_big5_scores,
    get_questions_localized,
)
from core import db, get_user, iso, now_utc, push_notif
from ai_service import compatibility_report

router = APIRouter(tags=["personality"])


@router.get("/personality/questions")
async def personality_questions(lang: str = "uz"):
    return {
        "questions": get_questions_localized(lang),
        "trait_labels": TRAIT_LABELS.get(lang, TRAIT_LABELS["uz"]),
    }


@router.post("/personality/submit")
async def personality_submit(
    answers: dict = Body(..., embed=False),
    uid: str = Depends(get_current_user_id),
):
    """answers = {"o1": 4, "o2": 5, ...}"""
    if not isinstance(answers, dict):
        raise HTTPException(400, "answers must be an object")
    scores = compute_big5_scores(answers)
    if not any(scores.values()):
        raise HTTPException(400, "No valid answers submitted")
    await db.users.update_one(
        {"id": uid},
        {"$set": {
            "big5_answers": {k: int(v) for k, v in answers.items() if isinstance(v, (int, str))},
            "big5_scores": scores,
            "big5_completed_at": iso(now_utc()),
        }, "$inc": {"balance": 200, "xp": 200}},
    )
    return {"ok": True, "scores": scores, "bonus": 200}


@router.get("/personality/mine")
async def personality_mine(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    return {
        "scores": me.get("big5_scores") or {},
        "completed_at": me.get("big5_completed_at"),
        "trait_labels": TRAIT_LABELS["uz"],
    }


@router.get("/personality/compatibility/{target_id}")
async def compatibility(target_id: str, lang: str = "uz", uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "Cannot compute self compatibility")
    me = await get_user(uid)
    target = await get_user(target_id)
    my_b5 = me.get("big5_scores") or {}
    tg_b5 = target.get("big5_scores") or {}
    score = big5_compatibility(my_b5, tg_b5) if my_b5 and tg_b5 else 0

    # Check if user has unlocked AI report (premium feature or paid one-off)
    plan = me.get("plan", "free")
    is_premium = plan in ("premium", "vip")

    unlocked = await db.compat_unlocks.find_one({"user_id": uid, "target_id": target_id})

    # Free preview: only score + trait labels
    if not is_premium and not unlocked:
        return {
            "score": score,
            "my_scores": my_b5,
            "their_scores": tg_b5,
            "locked": True,
            "unlock_price": 20000,
            "message": "Batafsil AI hisobotni qulflash uchun 20,000 so'm yoki Premium tarif kerak.",
        }

    # Full report
    report = await compatibility_report(me, target, my_b5, tg_b5, score, lang=lang)
    return {
        "score": score,
        "my_scores": my_b5,
        "their_scores": tg_b5,
        "report": report,
        "locked": False,
    }


@router.post("/personality/compatibility/{target_id}/unlock")
async def compatibility_unlock(target_id: str, uid: str = Depends(get_current_user_id)):
    """Pay 20,000 from balance to unlock detailed AI report."""
    PRICE = 20000
    if await db.compat_unlocks.find_one({"user_id": uid, "target_id": target_id}):
        me = await get_user(uid)
        return {"ok": True, "balance_after": me.get("balance", 0), "note": "already_unlocked"}
    res = await db.users.update_one(
        {"id": uid, "balance": {"$gte": PRICE}},
        {"$inc": {"balance": -PRICE}},
    )
    if res.modified_count == 0:
        raise HTTPException(402, f"Balansda {PRICE:,} so'm bo'lishi kerak")
    await db.compat_unlocks.update_one(
        {"user_id": uid, "target_id": target_id},
        {"$set": {"user_id": uid, "target_id": target_id, "unlocked_at": iso(now_utc()), "price": PRICE}},
        upsert=True,
    )
    me = await get_user(uid)
    return {"ok": True, "balance_after": me.get("balance", 0)}
