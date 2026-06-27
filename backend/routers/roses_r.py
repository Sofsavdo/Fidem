"""Roses — Hinge-style premium attention currency.

- Every user gets 1 free rose per week (auto-reset on Monday UTC)
- Sending a rose puts your message at the top of recipient's inbox + special highlight
- Extra roses can be purchased: 1 = 5,000 UZS, 5 = 20,000, 12 = 45,000
- Premium subscribers get 3 free roses per week
- VIP subscribers get 7 free roses per week
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import chat_id_for, db, get_user, iso, manager, now_utc, push_notif
from models import new_id

router = APIRouter(tags=["roses"])

ROSE_BUNDLES = {
    "1":  {"count": 1,  "price": 5000},
    "5":  {"count": 5,  "price": 20000},
    "12": {"count": 12, "price": 45000},
}

WEEKLY_FREE_BY_PLAN = {"free": 1, "premium": 3, "vip": 7}


def _monday_iso() -> str:
    n = now_utc()
    monday = (n - timedelta(days=n.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return iso(monday)


async def _ensure_weekly_refill(uid: str, me: dict) -> dict:
    """Make sure user has their plan's weekly free roses (additive on top of paid ones)."""
    monday = _monday_iso()
    last_refill = me.get("roses_last_refill")
    plan = me.get("plan", "free")
    free_per_week = WEEKLY_FREE_BY_PLAN.get(plan, 1)
    if last_refill == monday:
        return me
    # Set paid roses untouched; raise free up to plan's amount
    current_free = me.get("roses_free", 0)
    new_free = max(current_free, free_per_week)
    await db.users.update_one(
        {"id": uid},
        {"$set": {"roses_last_refill": monday, "roses_free": new_free}},
    )
    me["roses_free"] = new_free
    me["roses_last_refill"] = monday
    return me


@router.get("/roses/status")
async def roses_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    me = await _ensure_weekly_refill(uid, me)
    plan = me.get("plan", "free")
    return {
        "free": me.get("roses_free", 0),
        "paid": me.get("roses_paid", 0),
        "total": me.get("roses_free", 0) + me.get("roses_paid", 0),
        "weekly_quota": WEEKLY_FREE_BY_PLAN.get(plan, 1),
        "plan": plan,
        "bundles": ROSE_BUNDLES,
    }


@router.post("/roses/send")
async def send_rose(
    to_user_id: str = Body(..., embed=True),
    note: str = Body("", embed=True),
    uid: str = Depends(get_current_user_id),
):
    """Spend 1 rose to send a highlighted message. Counts as priority application."""
    if to_user_id == uid:
        raise HTTPException(400, "O'zingizga gul yubora olmaysiz")
    me = await get_user(uid)
    me = await _ensure_weekly_refill(uid, me)
    free = me.get("roses_free", 0)
    paid = me.get("roses_paid", 0)
    if free + paid <= 0:
        raise HTTPException(402, "Atirgullar tugagan. Yangisini sotib oling yoki keyingi hafta kuting.")
    # Prefer using free first
    inc = {"roses_free": -1} if free > 0 else {"roses_paid": -1}
    inc["roses_sent_total"] = 1
    inc["xp"] = 10
    await db.users.update_one({"id": uid}, {"$inc": inc})

    target = await get_user(to_user_id)
    cid = chat_id_for(uid, to_user_id)
    msg_text = note or "🌹 Sizga alohida e'tibor bilan murojaat qildim — sovchi-app orqali."

    msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": to_user_id,
        "text": msg_text,
        "kind": "rose",
        "meta": {"highlighted": True},
        "created_at": iso(now_utc()),
        "read": False,
        "status": "application",
    }
    await db.messages.insert_one(msg)
    msg.pop("_id", None)

    # Mark as roses-sent record
    await db.roses.insert_one({
        "id": new_id(),
        "from_user_id": uid,
        "to_user_id": to_user_id,
        "note": note,
        "used_free": free > 0,
        "created_at": iso(now_utc()),
    })
    await db.applications.update_one(
        {"from_user_id": uid, "to_user_id": to_user_id},
        {"$set": {
            "id": new_id(), "from_user_id": uid, "to_user_id": to_user_id,
            "is_rose": True, "status": "pending",
            "created_at": iso(now_utc()), "text": msg_text,
        }},
        upsert=True,
    )
    await manager.broadcast_chat([uid, to_user_id], {"type": "message", "data": msg})
    await push_notif(to_user_id, "rose", f"🌹 {me.get('name','Birov')} sizga atirgul yubordi")
    return {"ok": True, "remaining_free": max(0, free - 1), "remaining_paid": paid - (0 if free > 0 else 1)}


@router.post("/roses/purchase")
async def roses_purchase(bundle: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    """Purchase a rose bundle. Returns CLICK payment link."""
    if bundle not in ROSE_BUNDLES:
        raise HTTPException(400, "Noma'lum to'plam")
    b = ROSE_BUNDLES[bundle]
    pid = new_id()
    from services import click_pay_link
    link = click_pay_link(b["price"], pid)
    await db.payments.insert_one({
        "id": pid,
        "user_id": uid,
        "amount": b["price"],
        "purpose": "roses",
        "meta": {"bundle": bundle, "count": b["count"]},
        "status": "pending",
        "payment_link": link,
        "created_at": iso(now_utc()),
    })
    return {"id": pid, "amount": b["price"], "payment_link": link, "count": b["count"]}


@router.post("/roses/purchase-balance")
async def roses_purchase_from_balance(bundle: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    """Buy roses paying from in-app balance (no external payment)."""
    if bundle not in ROSE_BUNDLES:
        raise HTTPException(400, "Noma'lum to'plam")
    b = ROSE_BUNDLES[bundle]
    me = await get_user(uid)
    if me.get("balance", 0) < b["price"]:
        raise HTTPException(402, f"Balansda {b['price']:,} so'm kerak")
    await db.users.update_one({"id": uid}, {"$inc": {"balance": -b["price"], "roses_paid": b["count"]}})
    return {"ok": True, "added": b["count"], "balance_after": me.get("balance", 0) - b["price"]}
