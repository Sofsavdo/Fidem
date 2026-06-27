"""Candidates, photo-unlock, saved routes."""
from __future__ import annotations

import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, log, manager, now_utc, push_notif, touch_active, user_public
from models import PhotoUnlockDecision, PhotoUnlockRequest, SaveRequest, new_id
from services import age_from_birth, compute_match

router = APIRouter(tags=["candidates"])


def candidate_can_message(target: dict, sender: dict) -> bool:
    f = target.get("message_filters") or {}
    if not f:
        return True
    age = age_from_birth(sender.get("birth_date", "2000-01-01"))
    if age < f.get("age_min", 18) or age > f.get("age_max", 60):
        return False
    if f.get("region") and f["region"] != sender.get("region"):
        return False
    if f.get("marital_status") and f["marital_status"] != sender.get("marital_status"):
        return False
    if f.get("has_children") is not None and f["has_children"] != bool(sender.get("has_children")):
        return False
    if f.get("height_min") and sender.get("height_cm", 0) < f["height_min"]:
        return False
    if f.get("height_max") and sender.get("height_cm", 999) > f["height_max"]:
        return False
    if f.get("weight_min") and sender.get("weight_kg", 0) < f["weight_min"]:
        return False
    if f.get("weight_max") and sender.get("weight_kg", 999) > f["weight_max"]:
        return False
    if f.get("require_verified") and not sender.get("verified_selfie"):
        return False
    if f.get("require_financial") and not sender.get("verified_financial"):
        return False
    return True


# ---------- Candidates ----------
@router.get("/candidates")
async def candidates(
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    region: Optional[str] = None,
    marital_status: Optional[str] = None,
    has_children: Optional[bool] = None,
    height_min: Optional[int] = None,
    height_max: Optional[int] = None,
    verified_only: bool = False,
    financial_only: bool = False,
    sort: str = "match",
    limit: int = 30,
    uid: str = Depends(get_current_user_id),
):
    me_doc = await get_user(uid)
    if not me_doc.get("onboarded"):
        return []
    await touch_active(uid)

    query: dict = {"id": {"$ne": uid}, "onboarded": True, "blocked": {"$ne": True}}
    if me_doc.get("search_gender"):
        query["gender"] = me_doc["search_gender"]
    if region:
        query["region"] = region
    if marital_status:
        query["marital_status"] = marital_status
    if has_children is not None:
        query["has_children"] = has_children
    if verified_only:
        query["verified_selfie"] = True
    if financial_only:
        query["verified_financial"] = True

    cursor = db.users.find(query, {"_id": 0, "password_hash": 0}).limit(500)
    docs = await cursor.to_list(length=500)

    a_lo = age_min or me_doc.get("search_age_min", 18)
    a_hi = age_max or me_doc.get("search_age_max", 60)
    photo_unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "approved": True}, {"_id": 0}
    ).to_list(2000)
    unlocked_set = {p["target_id"] for p in photo_unlocks}

    enriched = []
    for d in docs:
        age = age_from_birth(d.get("birth_date", "2000-01-01"))
        if age < a_lo or age > a_hi:
            continue
        if height_min and d.get("height_cm", 0) < height_min:
            continue
        if height_max and d.get("height_cm", 999) > height_max:
            continue
        score, reasons = compute_match(me_doc, d)
        pub = user_public(d)
        pub["match_score"] = score
        pub["match_reasons"] = reasons
        pub["photo_unlocked"] = d["id"] in unlocked_set
        pub["can_message"] = candidate_can_message(d, me_doc)
        enriched.append(pub)

    if sort == "match":
        enriched.sort(key=lambda x: (-x["match_score"], -x["completeness"]))
    elif sort == "active":
        enriched.sort(key=lambda x: (not x["online"], x["last_active"]), reverse=False)
    elif sort == "new":
        enriched.sort(key=lambda x: x["last_active"], reverse=True)
    return enriched[:limit]


@router.get("/candidates/{target_id}")
async def candidate_detail(target_id: str, uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "Cannot view self as candidate")
    target = await get_user(target_id)
    me_doc = await get_user(uid)
    await db.profile_views.update_one(
        {"viewer_id": uid, "target_id": target_id},
        {"$set": {"viewer_id": uid, "target_id": target_id, "at": iso(now_utc())}},
        upsert=True,
    )
    score, reasons = compute_match(me_doc, target)
    pub = user_public(target)
    pub["match_score"] = score
    pub["match_reasons"] = reasons
    unlock = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": target_id}, {"_id": 0}
    )
    pub["photo_unlocked"] = bool(unlock and unlock.get("approved"))
    pub["photo_unlock_status"] = unlock.get("status") if unlock else "none"
    pub["can_message"] = candidate_can_message(target, me_doc)
    asyncio.create_task(push_notif(target_id, "view", f"Profilingizni {me_doc.get('name','')} ko'rdi"))
    return pub


# ---------- Photo unlock ----------
@router.post("/photo-unlock/request")
async def request_photo_unlock(req: PhotoUnlockRequest, uid: str = Depends(get_current_user_id)):
    existing = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": req.target_user_id}
    )
    if existing and existing.get("approved"):
        return {"status": "approved"}
    if existing and existing.get("status") == "pending":
        return {"status": "pending"}
    doc = {
        "id": new_id(),
        "requester_id": uid,
        "target_id": req.target_user_id,
        "status": "pending",
        "approved": False,
        "created_at": iso(now_utc()),
    }
    await db.photo_unlocks.replace_one(
        {"requester_id": uid, "target_id": req.target_user_id}, doc, upsert=True
    )
    me_doc = await get_user(uid)
    await push_notif(
        req.target_user_id, "photo_request",
        f"{me_doc.get('name','')} rasmingizni ko'rishni so'rayapti"
    )
    return {"status": "pending"}


@router.get("/photo-unlock/requests")
async def list_photo_unlock_requests(uid: str = Depends(get_current_user_id)):
    rows = await db.photo_unlocks.find({"target_id": uid, "status": "pending"}, {"_id": 0}).to_list(200)
    enriched = []
    for r in rows:
        u = await db.users.find_one({"id": r["requester_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            enriched.append({"request": r, "requester": user_public(u)})
    return enriched


@router.post("/photo-unlock/decide")
async def decide_photo_unlock(req: PhotoUnlockDecision, uid: str = Depends(get_current_user_id)):
    row = await db.photo_unlocks.find_one({"id": req.request_id})
    if not row or row.get("target_id") != uid:
        raise HTTPException(404, "Request not found")
    new_status = "approved" if req.approve else "rejected"
    await db.photo_unlocks.update_one(
        {"id": req.request_id},
        {"$set": {"status": new_status, "approved": req.approve, "decided_at": iso(now_utc())}},
    )
    if req.approve:
        await push_notif(row["requester_id"], "photo_grant", "Rasm ochildi — endi ko'rishingiz mumkin")
    return {"ok": True, "status": new_status}


# ---------- Saved / Likes ----------
@router.post("/saved")
async def save_user(req: SaveRequest, uid: str = Depends(get_current_user_id)):
    if req.user_id == uid:
        raise HTTPException(400, "Cannot save self")
    await db.saved.update_one(
        {"owner_id": uid, "target_id": req.user_id},
        {"$set": {"owner_id": uid, "target_id": req.user_id, "at": iso(now_utc())}},
        upsert=True,
    )
    me_doc = await get_user(uid)
    await push_notif(req.user_id, "saved", f"{me_doc.get('name','')} sizni saqladi")
    return {"ok": True}


@router.delete("/saved/{target_id}")
async def unsave_user(target_id: str, uid: str = Depends(get_current_user_id)):
    await db.saved.delete_one({"owner_id": uid, "target_id": target_id})
    return {"ok": True}


@router.get("/saved/mine")
async def saved_mine(uid: str = Depends(get_current_user_id)):
    rows = await db.saved.find({"owner_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    for r in rows:
        u = await db.users.find_one({"id": r["target_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            result.append(user_public(u))
    return result


@router.get("/saved/by-others")
async def saved_by_others(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    rows = await db.saved.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    for r in rows:
        u = await db.users.find_one({"id": r["owner_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["region"] = "•••"
                pub["locked"] = True
            result.append(pub)
    return result


@router.get("/saved/viewers")
async def viewers(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    rows = await db.profile_views.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    seen = set()
    for r in rows:
        vid = r["viewer_id"]
        if vid in seen or vid == uid:
            continue
        seen.add(vid)
        u = await db.users.find_one({"id": vid}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["region"] = "•••"
                pub["locked"] = True
            result.append(pub)
    return result


@router.get("/saved/interested")
async def interested_in_me(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    saved_rows = await db.saved.find({"target_id": uid}, {"_id": 0}).to_list(500)
    msg_rows = await db.messages.find({"to_user_id": uid}, {"_id": 0}).to_list(500)
    user_ids = {r["owner_id"] for r in saved_rows} | {m["from_user_id"] for m in msg_rows}
    user_ids.discard(uid)
    result = []
    for vid in user_ids:
        u = await db.users.find_one({"id": vid}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["locked"] = True
            result.append(pub)
    return result
