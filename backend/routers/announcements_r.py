"""Anonslar — platform announcements/news feed (photo + text posts).

Users see a feed (bottom-nav tab); the admin creates/deletes posts and can
optionally fan out an in-app notification. Later this also carries match /
wedding success stories.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel

from auth import get_current_admin, get_current_user_id
from core import db, iso, now_utc, push_notif
from models import new_id

log = logging.getLogger("fidem.announcements")

router = APIRouter(tags=["announcements"])


class AnnouncementCreate(BaseModel):
    title: str
    text: str = ""
    image_url: Optional[str] = None
    # Optional call-to-action button rendered at the end of the post.
    # action_url: "/referral" (internal route, in-app navigation) or a real
    # external URL (e.g. an Instagram post, an admin's t.me link) - the
    # frontend tells the two apart by whether it starts with "/".
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    notify: bool = False


class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    image_url: Optional[str] = None
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    # Explicit clear flags - a plain None means "leave unchanged" (the admin
    # didn't touch that field), so clearing an image/action needs its own
    # signal rather than overloading None for both meanings.
    clear_image: bool = False
    clear_action: bool = False


@router.get("/announcements")
async def list_announcements(uid: str = Depends(get_current_user_id)):
    rows = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return rows


@router.post("/announcements/{aid}/view")
async def mark_viewed(aid: str, uid: str = Depends(get_current_user_id)):
    """Records a unique viewer, not a raw view count - opening the same post
    twice (or scrolling past it again) must not inflate the number the admin
    sees ("necha kishi ko'rdi", not "necha marta ko'rilgan")."""
    await db.announcement_views.update_one(
        {"announcement_id": aid, "user_id": uid},
        {"$setOnInsert": {
            "id": new_id(), "announcement_id": aid, "user_id": uid, "created_at": iso(now_utc()),
        }},
        upsert=True,
    )
    return {"ok": True}


async def _notify_all(title: str) -> None:
    """In-app 'new announcement' ping to onboarded users (capped batch;
    push_notif applies marketing prefs + the 24h marketing cap per user)."""
    try:
        rows = await db.users.find(
            {"onboarded": True, "blocked": {"$ne": True}},
            {"_id": 0, "id": 1},
        ).limit(2000).to_list(2000)
        for u in rows:
            await push_notif(u["id"], "general", f"📣 {title}", link="/announcements", marketing=True)
    except Exception:
        log.warning("announcement fanout failed", exc_info=True)


@router.get("/admin/announcements")
async def admin_list_announcements(_: str = Depends(get_current_admin)):
    """Same feed as /announcements, but with a per-post unique-viewer count -
    'necha kishi ko'rdi', not raw impressions - so the admin can see whether
    a post actually reached anyone."""
    rows = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    if not rows:
        return rows
    ids = [r["id"] for r in rows]
    counts = await db.announcement_views.aggregate([
        {"$match": {"announcement_id": {"$in": ids}}},
        {"$group": {"_id": "$announcement_id", "n": {"$sum": 1}}},
    ]).to_list(len(ids))
    by_id = {c["_id"]: c["n"] for c in counts}
    for r in rows:
        r["view_count"] = by_id.get(r["id"], 0)
    return rows


@router.post("/admin/announcements")
async def create_announcement(req: AnnouncementCreate, _: str = Depends(get_current_admin)):
    title = (req.title or "").strip()
    if not title:
        raise HTTPException(400, "title required")
    doc = {
        "id": new_id(),
        "title": title,
        "text": (req.text or "").strip(),
        "image_url": req.image_url or None,
        "action_url": (req.action_url or "").strip() or None,
        "action_label": (req.action_label or "").strip() or None,
        "created_at": iso(now_utc()),
    }
    await db.announcements.insert_one(doc)
    doc.pop("_id", None)
    if req.notify:
        asyncio.create_task(_notify_all(title))
    return {"ok": True, "announcement": doc}


@router.patch("/admin/announcements/{aid}")
async def update_announcement(aid: str, req: AnnouncementUpdate, _: str = Depends(get_current_admin)):
    existing = await db.announcements.find_one({"id": aid}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Not found")

    update: dict = {}
    if req.title is not None:
        title = req.title.strip()
        if not title:
            raise HTTPException(400, "title required")
        update["title"] = title
    if req.text is not None:
        update["text"] = req.text.strip()
    if req.clear_image:
        update["image_url"] = None
    elif req.image_url is not None:
        update["image_url"] = req.image_url.strip() or None
    if req.clear_action:
        update["action_url"] = None
        update["action_label"] = None
    else:
        if req.action_url is not None:
            update["action_url"] = req.action_url.strip() or None
        if req.action_label is not None:
            update["action_label"] = req.action_label.strip() or None

    if update:
        await db.announcements.update_one({"id": aid}, {"$set": update})
    doc = await db.announcements.find_one({"id": aid}, {"_id": 0})
    return {"ok": True, "announcement": doc}


@router.delete("/admin/announcements/{aid}")
async def delete_announcement(aid: str, _: str = Depends(get_current_admin)):
    res = await db.announcements.delete_one({"id": aid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    await db.announcement_views.delete_many({"announcement_id": aid})
    return {"ok": True}
