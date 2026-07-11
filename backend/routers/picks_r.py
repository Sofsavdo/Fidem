"""Bugungi tanlov — daily picks: up to 3 best-matching candidates per day.

The selection is computed once per user per calendar day and cached in
db.daily_picks, so the section is instant on every open and the same three
people stay "today's picks" all day (stability builds the daily-habit loop;
recomputing per request would both be slower and feel random).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, strip_locked_photo, user_public_minimal
from services import compute_match
from models import new_id

router = APIRouter(tags=["picks"])

PICKS_PER_DAY = 3


async def compute_daily_picks(me_doc: dict) -> list[dict]:
    """Return today's picks for a user (cached per calendar day)."""
    uid = me_doc["id"]
    today = now_utc().date().isoformat()

    cached = await db.daily_picks.find_one({"user_id": uid, "date": today}, {"_id": 0})
    if cached is not None:
        ids = cached.get("candidate_ids", [])
        if not ids:
            return []
        docs = await db.users.find(
            {"id": {"$in": ids}, "onboarded": True, "blocked": {"$ne": True}, "hidden_profile": {"$ne": True}},
            {"_id": 0, "password_hash": 0},
        ).to_list(len(ids))
        by_id = {d["id"]: d for d in docs}
        docs = [by_id[i] for i in ids if i in by_id]
    else:
        query: dict = {
            "id": {"$ne": uid},
            "onboarded": True,
            "blocked": {"$ne": True},
            "hidden_profile": {"$ne": True},
        }
        if me_doc.get("search_gender"):
            query["gender"] = me_doc["search_gender"]
        a_lo = me_doc.get("search_age_min", 18)
        a_hi = me_doc.get("search_age_max", 60)
        try:
            today_d = now_utc().date()
            query["birth_date"] = {
                "$gte": today_d.replace(year=today_d.year - (a_hi + 1)).isoformat(),
                "$lte": today_d.replace(year=today_d.year - a_lo).isoformat(),
            }
        except Exception:
            pass

        docs = await db.users.find(query, {"_id": 0, "password_hash": 0}).limit(120).to_list(120)

        # Don't re-pitch people the user already saved.
        saved_rows = await db.saved.find({"owner_id": uid}, {"_id": 0, "target_id": 1}).to_list(1000)
        saved_ids = {r["target_id"] for r in saved_rows}
        docs = [d for d in docs if d["id"] not in saved_ids]

        my_region = me_doc.get("region") or ""

        def rank(d):
            score, _ = compute_match(me_doc, d, lang=me_doc.get("language", "uz"))
            same_region = bool(my_region) and d.get("region") == my_region
            return (0 if same_region else 1, -score)

        docs.sort(key=rank)
        docs = docs[:PICKS_PER_DAY]

        await db.daily_picks.update_one(
            {"user_id": uid, "date": today},
            {"$setOnInsert": {
                "id": new_id(), "user_id": uid, "date": today,
                "candidate_ids": [d["id"] for d in docs], "created_at": iso(now_utc()),
            }},
            upsert=True,
        )

    if not docs:
        return []

    unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "target_id": {"$in": [d["id"] for d in docs]}, "approved": True},
        {"_id": 0, "target_id": 1},
    ).to_list(50)
    unlocked = {u["target_id"] for u in unlocks}

    out = []
    for d in docs:
        pub = user_public_minimal(d)
        score, _ = compute_match(me_doc, d, lang=me_doc.get("language", "uz"))
        pub["match_score"] = score
        pub["photo_unlocked"] = d["id"] in unlocked
        out.append(strip_locked_photo(pub))
    return out


@router.get("/daily-picks")
async def daily_picks(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    if not me_doc.get("onboarded"):
        return []
    return await compute_daily_picks(me_doc)
