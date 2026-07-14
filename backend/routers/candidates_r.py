"""Candidates, photo-unlock, saved routes."""
from __future__ import annotations

import asyncio
import random
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import INCOGNITO_PLANS, PAID_PLANS, WHO_VIEWED_PLANS, chat_id_for, db, get_user, iso, log, manager, mask_name, now_utc, parse_dt, push_notif, strip_locked_photo, touch_active, user_public, user_public_minimal
from geo import distance_bucket, haversine_km
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
    vip_only: bool = False,
    verified_location_only: bool = False,
    max_distance_km: Optional[int] = None,
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
        # Distance-radius ("nearby") is a Premium perk; verified-location
        # filter and the badge itself stay free (trust is a base-tier value).
        max_distance_km = None

    await touch_active(uid)

    # hidden_profile users opted out of being discovered (they can still
    # browse and keep their existing chats) — never surface them in the feed.
    query: dict = {"id": {"$ne": uid}, "onboarded": True, "blocked": {"$ne": True}, "hidden_profile": {"$ne": True}}

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
    if vip_only:
        query["plan"] = "vip"
    if verified_location_only:
        query["location_verified"] = True

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

    # Coarse distance (Map M1). Raw coordinates stay server-side: we read both
    # parties' points from the isolated user_locations collection, compute the
    # real distance for filtering, but only ever attach a rounded bucket to
    # the payload. My own point is loaded once; candidates' in one batch.
    my_loc = await db.user_locations.find_one({"user_id": uid}, {"_id": 0, "geo_point": 1})
    my_pt = my_loc.get("geo_point") if my_loc else None
    cand_pts: dict = {}
    if my_pt:
        loc_rows = await db.user_locations.find(
            {"user_id": {"$in": [d["id"] for d in docs]}},
            {"_id": 0, "user_id": 1, "geo_point": 1},
        ).to_list(2000)
        cand_pts = {r["user_id"]: r["geo_point"] for r in loc_rows if r.get("geo_point")}

    enriched = []

    for d in docs:
        age = age_from_birth(d.get("birth_date", "2000-01-01"))

        if age < a_lo or age > a_hi:
            continue
        if height_min and d.get("height_cm", 0) < height_min:
            continue
        if height_max and d.get("height_cm", 999) > height_max:
            continue

        # distance bucket (only when both users shared a verified point)
        dist_km = None
        cpt = cand_pts.get(d["id"])
        if my_pt and cpt:
            dist_km = haversine_km(my_pt[1], my_pt[0], cpt[1], cpt[0])
        if max_distance_km is not None and (dist_km is None or dist_km > max_distance_km):
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
        pub["distance_bucket"] = distance_bucket(dist_km, match_lang) if dist_km is not None else None
        pub = strip_locked_photo(pub)

        now_iso2 = iso(now_utc())
        pub["boosted"] = bool(d.get("boost_until") and d["boost_until"] > now_iso2)

        enriched.append(pub)

    docs_by_id = {dd["id"]: dd for dd in docs}

    if sort == "match":
        # Default feed order, in strict priority tiers:
        #   1. Boosted profiles — boost buys the very top, above everything.
        #   2. The viewer's own region (a Farg'ona user sees Farg'ona people
        #      first) — explicit region/travel filters upstream still win
        #      because they narrow the query itself.
        #   3. Match score, with a freshness bonus so brand-new profiles get
        #      early visibility (+15 first 3 days, +8 first week).
        #   4. Profile completeness as the tie-breaker.
        now_iso = iso(now_utc())
        my_region = me_doc.get("region") or ""
        fresh_3d = iso(now_utc() - timedelta(days=3))
        fresh_7d = iso(now_utc() - timedelta(days=7))

        def _rank(x):
            d = docs_by_id.get(x["id"], {})
            boosted = d.get("boost_until", "") > now_iso
            same_region = bool(my_region) and d.get("region", "") == my_region
            created = d.get("created_at", "")
            fresh_bonus = 15 if created >= fresh_3d else (8 if created >= fresh_7d else 0)
            return (
                0 if boosted else 1,
                0 if same_region else 1,
                -(x.get("match_score", 0) + fresh_bonus),
                -x.get("completeness", 0),
            )

        enriched.sort(key=_rank)

    elif sort == "active":
        enriched.sort(key=lambda x: (not x.get("online", False), x.get("last_active", "")), reverse=False)

    elif sort == "new":
        # Genuinely new profiles (signup date), not merely recently active.
        enriched.sort(key=lambda x: docs_by_id.get(x["id"], {}).get("created_at", ""), reverse=True)

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

    # A hidden profile is undiscoverable: direct opens 404 exactly like a
    # nonexistent user, EXCEPT for admins and people who already have a chat
    # with them (an existing match must stay able to see who they talk to).
    if target.get("hidden_profile") and not me_doc.get("is_admin"):
        has_chat = await db.messages.find_one({"chat_id": chat_id_for(uid, target_id)}, {"_id": 1})
        if not has_chat:
            raise HTTPException(404, "User not found")

    match_lang = me_doc.get("language", "uz")
    if match_lang not in ("uz", "ru", "en"):
        match_lang = "uz"

    # Premium/VIP privacy perk: with hidden mode on, visits are incognito —
    # no profile_views record, no "kim ko'rdi" appearance, no notification,
    # and no bump to the target's view counters further below.
    incognito = bool(me_doc.get("hidden_profile")) and me_doc.get("plan") in INCOGNITO_PLANS

    should_notify_view = False
    if not incognito:
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

    # Coarse distance — both parties must have a verified point; only the
    # rounded bucket is exposed, never the raw coordinates.
    pub["distance_bucket"] = None
    my_loc = await db.user_locations.find_one({"user_id": uid}, {"_id": 0, "geo_point": 1})
    t_loc = await db.user_locations.find_one({"user_id": target_id}, {"_id": 0, "geo_point": 1})
    if my_loc and t_loc and my_loc.get("geo_point") and t_loc.get("geo_point"):
        mp, tp = my_loc["geo_point"], t_loc["geo_point"]
        pub["distance_bucket"] = distance_bucket(haversine_km(mp[1], mp[0], tp[1], tp[0]), match_lang)

    try:
        if not incognito:
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


# ---------- VIP photo peek (privacy tier 3) ----------
@router.post("/photo-peek/{target_id}")
async def photo_peek(target_id: str, uid: str = Depends(get_current_user_id)):
    """VIP + hidden-mode perk: reveal a locked photo once per profile, for a
    few seconds (the frontend enforces the 5s display; the once-per-profile
    rule is enforced here). Deliberately silent — no notification to the
    target, it's part of the incognito package."""
    if target_id == uid:
        raise HTTPException(400, "Cannot peek own photo")
    me_doc = await get_user(uid)
    if me_doc.get("plan") != "vip" or not me_doc.get("hidden_profile"):
        raise HTTPException(403, "peek_requires_vip")
    target = await get_user(target_id)
    # Atomic once-per-(viewer,target): the upsert only inserts the first time.
    res = await db.photo_peeks.update_one(
        {"viewer_id": uid, "target_id": target_id},
        {"$setOnInsert": {"id": new_id(), "viewer_id": uid, "target_id": target_id, "at": iso(now_utc())}},
        upsert=True,
    )
    if res.upserted_id is None:
        raise HTTPException(409, "peek_used")
    return {"photo_url": target.get("photo_url"), "seconds": 5}


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

    # Rejected recently: don't let the requester spam the same person with a
    # new popup every minute - one re-ask per week.
    if existing and existing.get("status") == "rejected" and existing.get("decided_at"):
        try:
            if now_utc() - parse_dt(existing["decided_at"]) < timedelta(days=7):
                return {"status": "rejected_wait"}
        except Exception:
            pass

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
        link="/saved?tab=requests",
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

        # Mark all messages in this chat as "match" status for Matches tab visibility
        if mutual_match:
            cid = chat_id_for(uid, req.user_id)
            await db.messages.update_many(
                {"chat_id": cid},
                {"$set": {"status": "match"}},
            )

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

    # Users who hid their profile after being saved drop out of the list —
    # their card would 404 on open anyway.
    users = await db.users.find(
        {"id": {"$in": target_ids}, "hidden_profile": {"$ne": True}},
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
    is_premium = me_doc.get("plan") in WHO_VIEWED_PLANS

    rows = await db.saved.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)

    owner_ids = [r["owner_id"] for r in rows]
    # Hidden profiles never appear in interaction lists (undiscoverable).
    users = await db.users.find(
        {"id": {"$in": owner_ids}, "hidden_profile": {"$ne": True}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(owner_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for r in rows:
        u = users_by_id.get(r["owner_id"])

        if u:
            pub = user_public(u)

            if not is_premium:
                # Age and region stay visible — only the identity (name,
                # photo) is locked pre-unlock, so the teaser still feels
                # like a real person instead of an opaque blur.
                pub["name"] = mask_name(u.get("name"))
                pub["photo_url"] = None
                pub["locked"] = True

            result.append(pub)

    return result


@router.get("/saved/viewers")
async def viewers(uid: str = Depends(get_current_user_id)):
    """Legacy endpoint kept for backward compatibility with old notification links.
    Frontend now uses /saved?tab=viewers but this endpoint remains functional."""
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in WHO_VIEWED_PLANS

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
        {"id": {"$in": ordered_ids}, "hidden_profile": {"$ne": True}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(ordered_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for vid in ordered_ids:
        u = users_by_id.get(vid)

        if u:
            pub = user_public(u)

            if not is_premium:
                pub["name"] = mask_name(u.get("name"))
                pub["photo_url"] = None
                pub["locked"] = True

            result.append(pub)

    return result


@router.get("/saved/interested")
async def interested_in_me(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in WHO_VIEWED_PLANS

    saved_rows = await db.saved.find({"target_id": uid}, {"_id": 0}).to_list(500)
    msg_rows = await db.messages.find({"to_user_id": uid}, {"_id": 0}).to_list(500)

    user_ids = {r["owner_id"] for r in saved_rows} | {m["from_user_id"] for m in msg_rows}
    user_ids.discard(uid)
    user_ids = list(user_ids)

    users = await db.users.find(
        {"id": {"$in": user_ids}, "hidden_profile": {"$ne": True}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(user_ids))
    users_by_id = {u["id"]: u for u in users}

    result = []

    for vid in user_ids:
        u = users_by_id.get(vid)

        if u:
            pub = user_public(u)

            if not is_premium:
                pub["name"] = mask_name(u.get("name"))
                pub["photo_url"] = None
                pub["locked"] = True

            result.append(pub)

    return result


@router.get("/saved/summary")
async def saved_summary(uid: str = Depends(get_current_user_id)):
    """Compact teaser for Me: who viewed or saved me, deduped and sorted by
    recency. Returns up to 5 masked profiles plus the true total count, so
    the UI can show real (if locked) cards instead of a blind redirect."""
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in WHO_VIEWED_PLANS

    view_rows = await db.profile_views.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    save_rows = await db.saved.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)

    latest_at: dict[str, str] = {}
    for r in view_rows:
        vid = r.get("viewer_id")
        if vid and vid != uid and vid not in latest_at:
            latest_at[vid] = r.get("at", "")
    for r in save_rows:
        oid = r.get("owner_id")
        if oid and oid != uid and oid not in latest_at:
            latest_at[oid] = r.get("at", "")

    ordered_ids = sorted(latest_at.keys(), key=lambda k: latest_at[k], reverse=True)

    # Exclude hidden profiles from both the preview AND the advertised total —
    # a "12 kishi qiziqdi" teaser must not count people the list won't show.
    if ordered_ids:
        hidden_rows = await db.users.find(
            {"id": {"$in": ordered_ids}, "hidden_profile": True},
            {"_id": 0, "id": 1},
        ).to_list(len(ordered_ids))
        hidden_ids = {h["id"] for h in hidden_rows}
        ordered_ids = [i for i in ordered_ids if i not in hidden_ids]

    total = len(ordered_ids)
    preview_ids = ordered_ids[:5]

    users = await db.users.find(
        {"id": {"$in": preview_ids}},
        {"_id": 0, "password_hash": 0},
    ).to_list(len(preview_ids))
    users_by_id = {u["id"]: u for u in users}

    items = []
    for pid in preview_ids:
        u = users_by_id.get(pid)
        if not u:
            continue
        pub = user_public(u)
        if not is_premium:
            pub["name"] = mask_name(u.get("name"))
            pub["photo_url"] = None
            pub["locked"] = True
        items.append(pub)

    return {"items": items, "total": total, "unlocked": is_premium}
