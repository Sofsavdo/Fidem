"""Wali / Chaperone — read-only family observer in chats.

Flow:
1) User generates an invite code (POST /chaperone/invite)
2) Shares code with parent/sibling/wali (Telegram link)
3) Wali accepts (POST /chaperone/accept) — must have FIDEM account
4) Wali can see user's matches & chats in read-only mode
5) Either party can remove the relationship
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import TELEGRAM_BOT_USERNAME, db, get_user, iso, now_utc, push_notif, user_public
from models import new_id

router = APIRouter(tags=["chaperone"])


# ---------- Generate & share invite ----------
@router.post("/chaperone/invite")
async def chaperone_invite(relation: str = Body("parent", embed=True), uid: str = Depends(get_current_user_id)):
    """Create an invite code that a wali (family observer) can redeem."""
    code = new_id().split("-")[0].upper()
    doc = {
        "id": new_id(),
        "code": code,
        "owner_id": uid,
        "relation": relation,   # parent / sibling / friend / wali
        "status": "open",
        "created_at": iso(now_utc()),
    }
    await db.chaperone_invites.insert_one(doc)
    link_app = f"/chaperone/accept?code={code}"
    link_tg = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start=chaperone_{code}" if TELEGRAM_BOT_USERNAME else None
    return {"code": code, "link_app": link_app, "link_tg": link_tg, "relation": relation}


@router.post("/chaperone/accept")
async def chaperone_accept(code: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    """Wali accepts to become an observer."""
    invite = await db.chaperone_invites.find_one({"code": code, "status": "open"})
    if not invite:
        raise HTTPException(404, "Taklif topilmadi yoki tugagan")
    owner_id = invite["owner_id"]
    if owner_id == uid:
        raise HTTPException(400, "O'zingiz uchun sovchi bo'la olmaysiz")
    # already linked?
    existing = await db.chaperones.find_one({"owner_id": owner_id, "wali_id": uid})
    if existing:
        return {"ok": True, "already": True}

    await db.chaperones.insert_one({
        "id": new_id(),
        "owner_id": owner_id,
        "wali_id": uid,
        "relation": invite.get("relation", "parent"),
        "status": "active",
        "created_at": iso(now_utc()),
    })
    await db.chaperone_invites.update_one({"id": invite["id"]}, {"$set": {"status": "accepted", "accepted_by": uid}})
    wali = await get_user(uid)
    await push_notif(owner_id, "chaperone", f"{wali.get('name','Sovchi')} sizning sovchingiz sifatida qo'shildi 👨‍👩‍👧")
    return {"ok": True}


# ---------- My chaperones (people who watch over me) ----------
@router.get("/chaperone/mine")
async def my_chaperones(uid: str = Depends(get_current_user_id)):
    rows = await db.chaperones.find({"owner_id": uid, "status": "active"}, {"_id": 0}).to_list(50)
    out = []
    for r in rows:
        wali = await db.users.find_one({"id": r["wali_id"]}, {"_id": 0, "password_hash": 0})
        if wali:
            out.append({"relation": r.get("relation"), "since": r.get("created_at"), "id": r.get("id"), "wali": user_public(wali)})
    return out


# ---------- People I observe (those I am wali for) ----------
@router.get("/chaperone/wards")
async def my_wards(uid: str = Depends(get_current_user_id)):
    rows = await db.chaperones.find({"wali_id": uid, "status": "active"}, {"_id": 0}).to_list(50)
    out = []
    for r in rows:
        owner = await db.users.find_one({"id": r["owner_id"]}, {"_id": 0, "password_hash": 0})
        if owner:
            out.append({"relation": r.get("relation"), "since": r.get("created_at"), "id": r.get("id"), "ward": user_public(owner)})
    return out


# ---------- Remove ----------
@router.delete("/chaperone/{link_id}")
async def remove_chaperone(link_id: str, uid: str = Depends(get_current_user_id)):
    row = await db.chaperones.find_one({"id": link_id})
    if not row or (row["owner_id"] != uid and row["wali_id"] != uid):
        raise HTTPException(404, "Aloqa topilmadi")
    await db.chaperones.update_one({"id": link_id}, {"$set": {"status": "removed", "removed_at": iso(now_utc()), "removed_by": uid}})
    return {"ok": True}


# ---------- View ward's chat (read-only) ----------
@router.get("/chaperone/ward/{ward_id}/chats")
async def ward_chats(ward_id: str, uid: str = Depends(get_current_user_id)):
    link = await db.chaperones.find_one({"wali_id": uid, "owner_id": ward_id, "status": "active"})
    if not link:
        raise HTTPException(403, "Sovchi sifatida ulanmagansiz")
    # Aggregate chats for ward, like list_chats in chat_r
    pipeline = [
        {"$match": {"$or": [{"from_user_id": ward_id}, {"to_user_id": ward_id}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$chat_id", "last": {"$first": "$$ROOT"}}},
        {"$sort": {"last.created_at": -1}},
    ]
    items = []
    async for row in db.messages.aggregate(pipeline):
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == ward_id else last["from_user_id"]
        u = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
        if not u:
            continue
        items.append({
            "chat_id": row["_id"],
            "other": user_public(u),
            "last_text": last.get("text", "")[:100],
            "last_kind": last.get("kind", "text"),
            "last_at": last.get("created_at"),
        })
    return items


@router.get("/chaperone/ward/{ward_id}/messages/{chat_id}")
async def ward_messages(ward_id: str, chat_id: str, uid: str = Depends(get_current_user_id)):
    link = await db.chaperones.find_one({"wali_id": uid, "owner_id": ward_id, "status": "active"})
    if not link:
        raise HTTPException(403, "Sovchi sifatida ulanmagansiz")
    if ward_id not in chat_id.split("_"):
        raise HTTPException(403, "Bu chat ward'ga tegishli emas")
    rows = await db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    # Strip private content (e.g. only show first 500)
    return rows
