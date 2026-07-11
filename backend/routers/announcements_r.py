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
    notify: bool = False


@router.get("/announcements")
async def list_announcements(uid: str = Depends(get_current_user_id)):
    rows = await db.announcements.find({}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return rows


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
        "created_at": iso(now_utc()),
    }
    await db.announcements.insert_one(doc)
    doc.pop("_id", None)
    if req.notify:
        asyncio.create_task(_notify_all(title))
    return {"ok": True, "announcement": doc}


@router.delete("/admin/announcements/{aid}")
async def delete_announcement(aid: str, _: str = Depends(get_current_admin)):
    res = await db.announcements.delete_one({"id": aid})
    if res.deleted_count == 0:
        raise HTTPException(404, "Not found")
    return {"ok": True}
