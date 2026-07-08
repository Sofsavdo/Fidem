"""Candidates, photo-unlock, saved routes."""
from __future__ import annotations

import asyncio
import random
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import PAID_PLANS, db, get_user, iso, log, manager, now_utc, parse_dt, push_notif, strip_locked_photo, touch_active, user_public, user_public_minimal
from models import PhotoUnlockDecision, PhotoUnlockRequest, SaveRequest, new_id
from services import age_from_birth, compute_match

router = APIRouter(tags=["candidates"])


def compute_ai_match(viewer: dict, candidate: dict, lang: str = "uz") -> tuple[int, list[str]]:
    """Enhanced AI-powered match calculation with premium features."""
    base_score, base_reasons = compute_match(viewer, candidate, lang)
    
    # AI enhancements for premium users
    ai_boost = 0
    ai_reasons = []
    
    # 1. Activity pattern matching (premium feature)
    viewer_active = viewer.get("last_active_minutes", 9999)
    candidate_active = candidate.get("last_active_minutes", 9999)
    if abs(viewer_active - candidate_active) < 60:  # Both active within 1 hour
        ai_boost += 5
        if lang == "uz":
            ai_reasons.append("Faollik vaqti mos")
        elif lang == "ru":
            ai_reasons.append("Активность совпадает")
        else:
            ai_reasons.append("Activity patterns match")
    
    # 2. Response time compatibility (premium feature)
    viewer_response = viewer.get("avg_response_min", 999)
    candidate_response = candidate.get("avg_response_min", 999)
    if viewer_response and candidate_response:
        if abs(viewer_response - candidate_response) < 30:
            ai_boost += 5
            if lang == "uz":
                ai_reasons.append("Javob tezligi mos")
            elif lang == "ru":
                ai_reasons.append("Скорость ответа совпадает")
            else:
                ai_reasons.append("Response speed compatible")
    
    # 3. Profile completeness bonus (premium feature)
    viewer_completeness = viewer.get("completeness", 0)
    candidate_completeness = candidate.get("completeness", 0)
    if viewer_completeness > 80 and candidate_completeness > 80:
        ai_boost += 5
        if lang == "uz":
            ai_reasons.append("Ikkala profil ham to'liq")
        elif lang == "ru":
            ai_reasons.append("Оба профиля полные")
        else:
            ai_reasons.append("Both profiles complete")
    
    # 4. Verification status alignment (premium feature)
    viewer_verified = viewer.get("verified_selfie", False) or viewer.get("verified_identity", False)
    candidate_verified = candidate.get("verified_selfie", False) or candidate.get("verified_identity", False)
    if viewer_verified and candidate_verified:
        ai_boost += 8
        if lang == "uz":
            ai_reasons.append("Ikkala taraf ham tasdiqlangan")
        elif lang == "ru":
            ai_reasons.append("Оба подтверждены")
        else:
            ai_reasons.append("Both verified")
    
    # 5. Plan compatibility (premium feature)
    viewer_plan = viewer.get("plan", "free")
    candidate_plan = candidate.get("plan", "free")
    if viewer_plan == candidate_plan and viewer_plan != "free":
        ai_boost += 5
        if lang == "uz":
            ai_reasons.append(f"{viewer_plan.capitalize()} foydalanuvchilar")
        elif lang == "ru":
            ai_reasons.append(f"{viewer_plan.capitalize()} пользователи")
        else:
            ai_reasons.append(f"{viewer_plan.capitalize()} users")
    
    # 6. Influence score proximity (premium feature)
    viewer_influence = viewer.get("influence_score", 0)
    candidate_influence = candidate.get("influence_score", 0)
    if viewer_influence > 0 and candidate_influence > 0:
        influence_diff = abs(viewer_influence - candidate_influence)
        if influence_diff < 1000:
            ai_boost += 5
            if lang == "uz":
                ai_reasons.append("Ta'sir darajasi yaqin")
            elif lang == "ru":
                ai_reasons.append("Уровень влияния близок")
            else:
                ai_reasons.append("Influence levels close")
    
    # 7. Big5 personality compatibility (if available)
    viewer_big5 = viewer.get("big5_scores", {})
    candidate_big5 = candidate.get("big5_scores", {})
    if viewer_big5 and candidate_big5:
        personality_match = 0
        for trait in ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]:
            v_score = viewer_big5.get(trait, 50)
            c_score = candidate_big5.get(trait, 50)
            # Complementary traits get bonus
            if trait == "extraversion":
                # Opposites attract for extraversion
                personality_match += (100 - abs(v_score - c_score)) / 5
            else:
                # Similar traits for others
                personality_match += (100 - abs(v_score - c_score)) / 10
        
        if personality_match > 30:
            ai_boost += int(personality_match / 10)
            if lang == "uz":
                ai_reasons.append("Shaxsiyat mosligi yuqori")
            elif lang == "ru":
                ai_reasons.append("Совпадение личности высокое")
            else:
                ai_reasons.append("High personality compatibility")
    
    # Combine base score with AI boost
    final_score = min(100, base_score + ai_boost)
    final_reasons = base_reasons + ai_reasons
    
    return final_score, final_reasons[:8]  # Return top 8 reasons


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
    district: Optional[str] = None,
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
    match_lang = me_doc.get("language", "uz")
    if match_lang not in ("uz", "ru", "en"):
        match_lang = "uz"
    if not me_doc.get("onboarded"):
        return []

    # "more_filters" (district, marital_status, has_children, height range) is
    # a Standard+ perk per the pricing page - free users keep age + region.
    is_paid = me_doc.get("plan", "free") in PAID_PLANS
    if not is_paid:
        district = None
        marital_status = None
        has_children = None
        height_min = None
        height_max = None

    await touch_active(uid)

    query: dict = {"id": {"$ne": uid}, "onboarded": True, "blocked": {"$ne": True}}

    if me_doc.get("search_gender"):
        query["gender"] = me_doc["search_gender"]

    # Travel Mode: if user has active travel_region, use it as filter unless explicit region passed
    if not region:
        travel_region = me_doc.get("travel_region")
        travel_until = me_doc.get("travel_until")
        if travel_region and travel_until:
            try:
                if parse_dt(travel_until) > now_utc():
                    region = travel_region
            except Exception:
                pass

    if region:
        query["region"] = region
    if district:
        query["district"] = district
    if marital_status:
        query["marital_status"] = marital_status
    if has_children is not None:
        query["has_children"] = has_children
    if verified_only:
        query["verified_selfie"] = True
    if financial_only:
        query["verified_financial"] = True

    # Perf: pre-filter age range at DB level via birth_date ISO string comparison.
    a_lo = age_min or me_doc.get("search_age_min", 18)
    a_hi = age_max or me_doc.get("search_age_max", 60)

    try:
        today = now_utc().date()
        bd_min = today.replace(year=today.year - (a_hi + 1)).isoformat()
        bd_max = today.replace(year=today.year - a_lo).isoformat()
        query["birth_date"] = {"$gte": bd_min, "$lte": bd_max}
    except Exception:
        pass

    cursor = db.users.find(query, {"_id": 0, "password_hash": 0}).limit(200)
    docs = await cursor.to_list(length=200)

    photo_unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "approved": True},
        {"_id": 0},
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

        # Use AI match calculation for premium users
        if me_doc.get("plan") in ("premium", "vip"):
            score, reasons = compute_ai_match(me_doc, d, lang=match_lang)
        else:
            score, reasons = compute_match(me_doc, d, lang=match_lang)

        pub = user_public_minimal(d)
        pub["match_score"] = score
        pub["match_reasons"] = reasons
        pub["photo_unlocked"] = d["id"] in unlocked_set
        pub["can_message"] = candidate_can_message(d, me_doc)
        pub = strip_locked_photo(pub)

        now_iso2 = iso(now_utc())
        pub["boosted"] = bool(d.get("boost_until") and d["boost_until"] > now_iso2)

        enriched.append(pub)

    if sort == "match":
        now_iso = iso(now_utc())

        def _rank(x):
            d = next((dd for dd in docs if dd["id"] == x["id"]), {})
            boosted = d.get("boost_until", "") > now_iso
            return (
                -1 if boosted else 0,
                -x.get("match_score", 0),
                -x.get("completeness", 0),
            )

        enriched.sort(key=_rank)

    elif sort == "active":
        enriched.sort(key=lambda x: (not x.get("online", False), x.get("last_active", "")), reverse=False)

    elif sort == "new":
        enriched.sort(key=lambda x: x.get("last_active", ""), reverse=True)

    result = enriched[:limit]

    try:
        now_iso3 = iso(now_utc())
        boosted_ids = [d["id"] for d in docs if d.get("boost_until") and d["boost_until"] > now_iso3]
        result_ids = {x["id"] for x in result}
        boosted_hit = [i for i in boosted_ids if i in result_ids]

        if boosted_hit:
            await db.users.update_many(
                {"id": {"$in": boosted_hit}},
                {"$inc": {"boost_metrics.impressions": 1, "impressions_total": 1}},
            )

    except Exception:
        pass

    return result


@router.get("/candidates/{target_id}")
async def candidate_detail(target_id: str, uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "Cannot view self as candidate")

    target = await get_user(target_id)
    me_doc = await get_user(uid)
    match_lang = me_doc.get("language", "uz")
    if match_lang not in ("uz", "ru", "en"):
        match_lang = "uz"

    existing_view = await db.profile_views.find_one(
        {"viewer_id": uid, "target_id": target_id},
        {"_id": 0, "at": 1},
    )
    should_notify_view = existing_view is None
    if existing_view and existing_view.get("at"):
        try:
            if (now_utc() - parse_dt(existing_view["at"])) >= timedelta(hours=24):
                should_notify_view = True
        except Exception:
            pass

    await db.profile_views.update_one(
        {"viewer_id": uid, "target_id": target_id},
        {"$set": {"viewer_id": uid, "target_id": target_id, "at": iso(now_utc())}},
        upsert=True,
    )

    # Use AI match calculation for premium users in detail view too
    if me_doc.get("plan") in ("premium", "vip"):
        score, reasons = compute_ai_match(me_doc, target, lang=match_lang)
    else:
        score, reasons = compute_match(me_doc, target, lang=match_lang)

    pub = user_public(target)
    pub["match_score"] = score
    pub["match_reasons"] = reasons

    unlock = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": target_id},
        {"_id": 0},
    )

    pub["photo_unlocked"] = bool(unlock and unlock.get("approved"))
    pub["photo_unlock_status"] = unlock.get("status") if unlock else "none"
    pub["can_message"] = candidate_can_message(target, me_doc)

    try:
        now_iso = iso(now_utc())
        inc = {"views_total": 1}

        if target.get("boost_until") and target["boost_until"] > now_iso:
            inc["boost_metrics.views"] = 1

        await db.users.update_one({"id": target_id}, {"$inc": inc})

    except Exception:
        pass

    if should_notify_view:
        asyncio.create_task(
            push_notif(
                target_id,
                "view",
                "👀 Profilingizni yangi foydalanuvchi ko‘rdi.\n\n"
                "Kim qiziqqanini bilish uchun FIDEM’ni oching.",
                link="/saved?tab=viewers",
            )
        )

    return strip_locked_photo(pub)


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
        {"requester_id": uid, "target_id": req.target_user_id},
        doc,
        upsert=True,
    )

    me_doc = await get_user(uid)

    await push_notif(
        req.target_user_id,
        "photo_request",
        f"📸 {me_doc.get('name', '')} rasmlaringizni ko‘rish uchun ruxsat so‘radi.\n\n"
        "Ruxsat berish yoki rad etish uchun FIDEM’ni oching.",
        link="/saved",
    )

    return {"status": "pending"}


@router.get("/photo-unlock/requests")
async def list_photo_unlock_requests(uid: str = Depends(get_current_user_id)):
    rows = await db.photo_unlocks.find(
        {"target_id": uid, "status": "pending"},
        {"_id": 0},
    ).to_list(200)

    requester_ids = [r["requester_id"] for r in rows]
    users = await db.users.find(
        {"id": {"$in": requester_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(requester_ids))
    users_by_id = {u["id"]: u for u in users}

    enriched = []

    for r in rows:
        u = users_by_id.get(r["requester_id"])

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
        {
            "$set": {
                "status": new_status,
                "approved": req.approve,
                "decided_at": iso(now_utc()),
            }
        },
    )

    if req.approve:
        await push_notif(
            row["requester_id"],
            "photo_grant",
            "✅ Rasmga ruxsat berildi.\n\n"
            "Endi profilni to‘liq ko‘rishingiz mumkin.",
            link=f"/candidate/{uid}",
        )

    return {"ok": True, "status": new_status}


# ---------- Saved / Likes ----------
@router.post("/saved")
async def save_user(req: SaveRequest, uid: str = Depends(get_current_user_id)):
    if req.user_id == uid:
        raise HTTPException(400, "Cannot save self")

    is_new = await db.saved.find_one({"owner_id": uid, "target_id": req.user_id}) is None

    await db.saved.update_one(
        {"owner_id": uid, "target_id": req.user_id},
        {"$set": {"owner_id": uid, "target_id": req.user_id, "at": iso(now_utc())}},
        upsert=True,
    )

    # Mutual save = a match (also what unlocks free chat, see chat_r.can_initiate_chat).
    # Only worth celebrating the instant it newly forms, not on every re-save.
    mutual_match = False
    if is_new:
        mutual_match = await db.saved.find_one({"owner_id": req.user_id, "target_id": uid}) is not None

    if is_new:
        try:
            target = await get_user(req.user_id)
            now_iso = iso(now_utc())
            inc = {"likes_received_total": 1}

            if target.get("boost_until") and target["boost_until"] > now_iso:
                inc["boost_metrics.likes"] = 1

            await db.users.update_one({"id": req.user_id}, {"$inc": inc})

        except Exception:
            pass

        await push_notif(
            req.user_id,
            "saved",
            "❤️ Sizda yangi qiziqish mavjud.\n\n"
            "Kim sizni yoqtirganini bilish uchun FIDEM’ni oching.",
            link="/saved?tab=by_others",
        )

    return {"ok": True, "mutual_match": mutual_match}


@router.delete("/saved/{target_id}")
async def unsave_user(target_id: str, uid: str = Depends(get_current_user_id)):
    await db.saved.delete_one({"owner_id": uid, "target_id": target_id})
    return {"ok": True}


@router.get("/saved/mine")
async def saved_mine(uid: str = Depends(get_current_user_id)):
    rows = await db.saved.find({"owner_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)

    target_ids = [r["target_id"] for r in rows]
    unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "target_id": {"$in": target_ids}, "approved": True},
        {"_id": 0, "target_id": 1},
    ).to_list(500)
    unlocked_set = {p["target_id"] for p in unlocks}

    users = await db.users.find(
        {"id": {"$in": target_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(target_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for r in rows:
        u = users_by_id.get(r["target_id"])

        if u:
            pub = user_public(u)
            pub["photo_unlocked"] = u["id"] in unlocked_set
            result.append(strip_locked_photo(pub))

    return result


@router.get("/saved/by-others")
async def saved_by_others(uid: str = Depends(get_current_user_id)):
    """Legacy endpoint kept for backward compatibility with old notification links.
    Frontend now uses /saved?tab=by_others but this endpoint remains functional."""
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")

    rows = await db.saved.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)

    owner_ids = [r["owner_id"] for r in rows]
    users = await db.users.find(
        {"id": {"$in": owner_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(owner_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for r in rows:
        u = users_by_id.get(r["owner_id"])

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
    """Legacy endpoint kept for backward compatibility with old notification links.
    Frontend now uses /saved?tab=viewers but this endpoint remains functional."""
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")

    rows = await db.profile_views.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)

    ordered_ids = []
    seen = set()

    for r in rows:
        vid = r["viewer_id"]

        if vid in seen or vid == uid:
            continue

        seen.add(vid)
        ordered_ids.append(vid)

    users = await db.users.find(
        {"id": {"$in": ordered_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(ordered_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for vid in ordered_ids:
        u = users_by_id.get(vid)

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
    user_ids = list(user_ids)

    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(user_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for vid in user_ids:
        u = users_by_id.get(vid)

        if u:
            pub = user_public(u)

            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["locked"] = True

            result.append(pub)

    return result
