"""Guest mode: look around first, register to act.

A person who opened the Mini App through Telegram already has an account
(name, username and Telegram id come from Telegram), but until the profile
is filled in (`onboarded`) they are a guest:

- they can browse the candidates, profiles, Premium and the assistant;
- only the first GUEST_OPEN_PHOTOS profiles of their feed show photos. The
  rest come without photo URLs (`guest_locked`), so the photos can't be
  fetched at all, not just blurred on screen;
- likes, messages, unlock requests, payments and so on answer 403
  `onboarding_required`. The app shows "finish registration" and returns to
  the same place afterwards;
- their visits leave no trace (no "viewed you", no notification), and they
  never appear in anyone's feed (the feed only lists onboarded people).
"""
from __future__ import annotations

import time

from fastapi import Depends, HTTPException

import core
from auth import get_current_user_id

GUEST_OPEN_PHOTOS = 4


def is_guest(user: dict) -> bool:
    return not user.get("onboarded") and not user.get("is_admin")


def lock_photos(pub: dict) -> dict:
    pub["photo_url"] = None
    pub["photos"] = []
    pub["video_intro_url"] = None
    pub["guest_locked"] = True
    return pub


async def open_ids(me: dict, feed_ids: list[str]) -> set[str]:
    """The profiles whose photos this guest may see: the first ones of their
    first feed, fixed after that (so reloading or filtering doesn't open
    more)."""
    stored = list(me.get("guest_open_ids") or [])
    if len(stored) < GUEST_OPEN_PHOTOS:
        for fid in feed_ids:
            if len(stored) >= GUEST_OPEN_PHOTOS:
                break
            if fid not in stored:
                stored.append(fid)
        if stored != list(me.get("guest_open_ids") or []):
            await core.db.users.update_one({"id": me["id"]}, {"$set": {"guest_open_ids": stored}})
            forget(me["id"])
    return set(stored)


# ---- file access (serve_file): a guest may only fetch the open profiles' photos
_CACHE: dict[str, tuple[float, bool, frozenset]] = {}
_TTL = 15.0


def forget(uid: str) -> None:
    _CACHE.pop(uid, None)


async def guest_scope(uid: str) -> frozenset | None:
    """None for a registered user (no limit); for a guest, the profile ids
    whose photos they may fetch."""
    hit = _CACHE.get(uid)
    now = time.monotonic()
    if hit and hit[0] > now:
        return hit[2] if hit[1] else None
    u = await core.db.users.find_one(
        {"id": uid}, {"_id": 0, "onboarded": 1, "is_admin": 1, "guest_open_ids": 1},
    )
    if u is None:      # unknown account: the normal file rules decide
        return None
    guest = is_guest(u)
    scope = frozenset(u.get("guest_open_ids") or [])
    if len(_CACHE) > 5000:
        _CACHE.clear()
    _CACHE[uid] = (now + _TTL, guest, scope)
    return scope if guest else None


# ---- actions need a finished profile
async def require_onboarded(uid: str = Depends(get_current_user_id)) -> str:
    u = await core.db.users.find_one({"id": uid}, {"_id": 0, "onboarded": 1, "is_admin": 1}) or {}
    if is_guest(u):
        raise HTTPException(403, "onboarding_required")
    return uid
