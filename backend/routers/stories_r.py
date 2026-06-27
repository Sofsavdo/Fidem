"""Success stories — couples who met via FIDEM share their nikoh story.

Powerful social-proof marketing tool. Admin-managed (mostly), with optional user submission for review.
"""
from __future__ import annotations
from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, iso, now_utc
from models import new_id

router = APIRouter(tags=["stories"])


def _is_admin(user: dict) -> bool:
    return bool(user.get("is_admin"))


@router.get("/stories")
async def list_stories(featured_only: bool = False, limit: int = 30):
    q = {"published": True}
    if featured_only:
        q["featured"] = True
    rows = await db.success_stories.find(q, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
    return rows


@router.get("/stories/{story_id}")
async def get_story(story_id: str):
    row = await db.success_stories.find_one({"id": story_id, "published": True}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Not found")
    # increment view count (non-blocking)
    try:
        await db.success_stories.update_one({"id": story_id}, {"$inc": {"views": 1}})
    except Exception:
        pass
    return row


@router.post("/stories/submit")
async def submit_story(
    payload: dict = Body(...),
    uid: str = Depends(get_current_user_id),
):
    """Users can submit their story for admin review (not auto-published)."""
    doc = {
        "id": new_id(),
        "submitted_by": uid,
        "couple_names": (payload.get("couple_names") or "")[:80],
        "region": (payload.get("region") or "")[:50],
        "year": int(payload.get("year") or 2025),
        "story_text": (payload.get("story_text") or "")[:2000],
        "photo_url": payload.get("photo_url"),
        "published": False,
        "featured": False,
        "views": 0,
        "created_at": iso(now_utc()),
    }
    if len(doc["story_text"]) < 30:
        raise HTTPException(400, "Hikoya kamida 30 belgi bo'lishi kerak")
    await db.success_stories.insert_one(doc)
    return {"ok": True, "id": doc["id"], "status": "pending_review"}


# ---------- Admin ----------
@router.post("/admin/stories")
async def admin_create_story(payload: dict = Body(...), uid: str = Depends(get_current_user_id)):
    me = await db.users.find_one({"id": uid})
    if not me or not _is_admin(me):
        raise HTTPException(403, "Admin only")
    doc = {
        "id": new_id(),
        "couple_names": (payload.get("couple_names") or "Aziza & Bobur")[:80],
        "region": (payload.get("region") or "Toshkent")[:50],
        "year": int(payload.get("year") or 2025),
        "story_text": (payload.get("story_text") or "")[:2000],
        "photo_url": payload.get("photo_url"),
        "published": bool(payload.get("published", True)),
        "featured": bool(payload.get("featured", False)),
        "views": 0,
        "created_at": iso(now_utc()),
    }
    await db.success_stories.insert_one(doc)
    return {"ok": True, "id": doc["id"]}


@router.patch("/admin/stories/{story_id}")
async def admin_update_story(story_id: str, payload: dict = Body(...), uid: str = Depends(get_current_user_id)):
    me = await db.users.find_one({"id": uid})
    if not me or not _is_admin(me):
        raise HTTPException(403, "Admin only")
    updatable = {k: v for k, v in payload.items() if k in {"couple_names", "region", "year", "story_text", "photo_url", "published", "featured"}}
    if not updatable:
        raise HTTPException(400, "Nothing to update")
    await db.success_stories.update_one({"id": story_id}, {"$set": updatable})
    return {"ok": True}


@router.delete("/admin/stories/{story_id}")
async def admin_delete_story(story_id: str, uid: str = Depends(get_current_user_id)):
    me = await db.users.find_one({"id": uid})
    if not me or not _is_admin(me):
        raise HTTPException(403, "Admin only")
    await db.success_stories.delete_one({"id": story_id})
    return {"ok": True}


@router.get("/admin/stories")
async def admin_list_stories(uid: str = Depends(get_current_user_id)):
    me = await db.users.find_one({"id": uid})
    if not me or not _is_admin(me):
        raise HTTPException(403, "Admin only")
    rows = await db.success_stories.find({}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows
