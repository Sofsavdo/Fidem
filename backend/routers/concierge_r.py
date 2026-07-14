"""Sovchi Concierge — premium manual matchmaking service.
199,000 UZS / 1 month / 5 hand-picked matches by admin.
"""
from __future__ import annotations

from datetime import timedelta
from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_admin, get_current_user_id
from core import db, get_user, iso, log, now_utc, push_notif, user_public
from models import new_id
from services import click_pay_link

router = APIRouter(tags=["concierge"])

CONCIERGE_PRICE_UZS = 199_000
CONCIERGE_MAX_MATCHES = 5
CONCIERGE_DAYS = 30


@router.get("/concierge/info")
async def concierge_info(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    active = await db.concierge_orders.find_one(
        {"user_id": uid, "status": {"$in": ["active", "in_progress"]}}, {"_id": 0}
    )
    return {
        "price": CONCIERGE_PRICE_UZS,
        "max_matches": CONCIERGE_MAX_MATCHES,
        "days": CONCIERGE_DAYS,
        "active_order": active,
        "can_balance_pay": me.get("balance", 0) >= CONCIERGE_PRICE_UZS,
    }


@router.post("/concierge/order")
async def create_concierge_order(
    payment_method: str = Body("click", embed=True),
    uid: str = Depends(get_current_user_id),
):
    me = await get_user(uid)
    existing = await db.concierge_orders.find_one(
        {"user_id": uid, "status": {"$in": ["active", "in_progress"]}}
    )
    if existing:
        raise HTTPException(400, "Sizda allaqachon faol Sovchi Concierge buyurtmasi bor")

    order_id = new_id()

    if payment_method == "balance":
        res = await db.users.update_one(
            {"id": uid, "balance": {"$gte": CONCIERGE_PRICE_UZS}},
            {"$inc": {"balance": -CONCIERGE_PRICE_UZS}},
        )
        if res.modified_count == 0:
            raise HTTPException(402, "Balansda mablag' yetarli emas")
        order = {
            "id": order_id,
            "user_id": uid,
            "amount": CONCIERGE_PRICE_UZS,
            "status": "in_progress",
            "paid_at": iso(now_utc()),
            "expires_at": iso(now_utc() + timedelta(days=CONCIERGE_DAYS)),
            "matches": [],
            "created_at": iso(now_utc()),
            "payment_method": "balance",
        }
        await db.concierge_orders.insert_one(order)
        order.pop("_id", None)
        return {"order": order, "payment_link": None}

    # CLICK payment flow
    # P2P mode = CLICK is temporarily disabled by the admin; see payments_r.py
    cfg = await db.settings.find_one({"id": "topup_config"}) or {}
    if cfg.get("p2p_enabled"):
        raise HTTPException(400, "click_disabled")
    pid = new_id()
    payment = {
        "id": pid,
        "user_id": uid,
        "amount": CONCIERGE_PRICE_UZS,
        "purpose": "concierge",
        "order_id": order_id,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    link = click_pay_link(CONCIERGE_PRICE_UZS, pid)
    payment["payment_link"] = link
    await db.payments.insert_one(payment)

    order = {
        "id": order_id,
        "user_id": uid,
        "amount": CONCIERGE_PRICE_UZS,
        "status": "awaiting_payment",
        "matches": [],
        "payment_id": pid,
        "payment_method": "click",
        "created_at": iso(now_utc()),
    }
    await db.concierge_orders.insert_one(order)
    order.pop("_id", None)
    return {"order": order, "payment_link": link}


@router.get("/concierge/mine")
async def my_concierge(uid: str = Depends(get_current_user_id)):
    orders = await db.concierge_orders.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(20)
    # Enrich match user details
    match_ids = {mid for o in orders for mid in (o.get("matches") or [])}
    matched_users = await db.users.find(
        {"id": {"$in": list(match_ids)}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(match_ids))
    users_by_id = {u["id"]: u for u in matched_users}

    out = []
    for o in orders:
        o["match_users"] = [
            user_public(users_by_id[mid])
            for mid in (o.get("matches") or [])
            if mid in users_by_id
        ]
        out.append(o)
    return out


# ---------- Admin ----------
@router.get("/admin/concierge")
async def admin_list_concierge(status: str | None = None, _: str = Depends(get_current_admin)):
    q: dict = {}
    if status:
        q["status"] = status
    rows = await db.concierge_orders.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    user_ids = [r["user_id"] for r in rows]
    users = await db.users.find(
        {"id": {"$in": user_ids}}, {"_id": 0, "password_hash": 0}
    ).to_list(len(user_ids))
    users_by_id = {u["id"]: u for u in users}

    out = []
    for r in rows:
        u = users_by_id.get(r["user_id"])
        r["user"] = user_public(u, include_private=True) if u else None
        out.append(r)
    return out


@router.post("/admin/concierge/{order_id}/match")
async def admin_add_match(
    order_id: str,
    match_user_id: str = Body(..., embed=True),
    note: str = Body("", embed=True),
    _: str = Depends(get_current_admin),
):
    order = await db.concierge_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(404, "Order not found")
    if order["status"] not in ("in_progress", "active"):
        raise HTTPException(400, "Order not active")
    matches = order.get("matches") or []
    if match_user_id in matches:
        raise HTTPException(400, "Match already added")
    if len(matches) >= CONCIERGE_MAX_MATCHES:
        raise HTTPException(400, f"Maksimum {CONCIERGE_MAX_MATCHES} ta mos taqdim qilingan")
    matches.append(match_user_id)
    upd = {"matches": matches}
    notes = order.get("match_notes") or {}
    if note:
        notes[match_user_id] = note
        upd["match_notes"] = notes
    if len(matches) >= CONCIERGE_MAX_MATCHES:
        upd["status"] = "completed"
        upd["completed_at"] = iso(now_utc())
    await db.concierge_orders.update_one({"id": order_id}, {"$set": upd})
    await push_notif(
        order["user_id"],
        "concierge",
        f"🎯 Sizga yangi mos taqdim etildi ({len(matches)}/{CONCIERGE_MAX_MATCHES})",
        link="/concierge",
    )
    return {"ok": True, "matches_count": len(matches)}


@router.post("/admin/concierge/{order_id}/complete")
async def admin_complete_concierge(order_id: str, _: str = Depends(get_current_admin)):
    order = await db.concierge_orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(404, "Order not found")
    await db.concierge_orders.update_one(
        {"id": order_id},
        {"$set": {"status": "completed", "completed_at": iso(now_utc())}},
    )
    return {"ok": True}
