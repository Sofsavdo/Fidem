"""Gift balance withdrawal (Bigo-style). Recipients accumulate withdrawable balance from received gifts.

Conversion: 50% of gift price is converted to withdrawable balance for recipient.
Min payout: 100,000 UZS. Admin approves manually via CLICK transfer.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_admin, get_current_user_id
from core import db, get_user, iso, log, now_utc, push_notif
from models import new_id

router = APIRouter(tags=["withdrawals"])

# Conversion: 50% of gift value goes to recipient's withdrawable balance
GIFT_CONVERSION_RATE = 0.5
MIN_WITHDRAW_UZS = 100_000


@router.get("/withdrawals/status")
async def withdraw_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    pending = await db.withdrawals.count_documents({"user_id": uid, "status": "pending"})
    return {
        "withdrawable_balance": int(me.get("withdrawable_balance", 0) or 0),
        "min_payout": MIN_WITHDRAW_UZS,
        "conversion_rate_pct": int(GIFT_CONVERSION_RATE * 100),
        "pending_count": pending,
        "gifts_received_total": int(me.get("gifts_received_total", 0) or 0),
    }


@router.post("/withdrawals/request")
async def request_withdrawal(
    amount: int = Body(..., embed=True),
    card_number: str = Body(..., embed=True),
    holder_name: str = Body("", embed=True),
    uid: str = Depends(get_current_user_id),
):
    if amount < MIN_WITHDRAW_UZS:
        raise HTTPException(400, f"Minimal yechib olish: {MIN_WITHDRAW_UZS:,} so'm")
    me = await get_user(uid)
    bal = int(me.get("withdrawable_balance", 0) or 0)
    if amount > bal:
        raise HTTPException(400, f"Yetarli mablag' yo'q. Mavjud: {bal:,} so'm")
    card_clean = "".join(ch for ch in card_number if ch.isdigit())
    if len(card_clean) < 16:
        raise HTTPException(400, "Karta raqami noto'g'ri")
    # Hold the amount
    res = await db.users.update_one(
        {"id": uid, "withdrawable_balance": {"$gte": amount}},
        {"$inc": {"withdrawable_balance": -amount, "withdrawals_pending": amount}},
    )
    if res.modified_count == 0:
        raise HTTPException(400, "Mablag' yetarli emas yoki bir vaqtda boshqa so'rov qilindi")
    wid = new_id()
    doc = {
        "id": wid,
        "user_id": uid,
        "amount": amount,
        "card_number": card_clean,
        "holder_name": holder_name or me.get("name", ""),
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    await db.withdrawals.insert_one(doc)
    doc.pop("_id", None)
    return {"ok": True, "id": wid, "amount": amount, "status": "pending"}


@router.get("/withdrawals/mine")
async def my_withdrawals(uid: str = Depends(get_current_user_id)):
    rows = await db.withdrawals.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


# ---------- Admin ----------
@router.get("/admin/withdrawals")
async def admin_list_withdrawals(status: str | None = None, _: str = Depends(get_current_admin)):
    q: dict = {}
    if status:
        q["status"] = status
    rows = await db.withdrawals.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    out = []
    for r in rows:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "name": 1, "email": 1, "phone": 1, "telegram_username": 1})
        r["user"] = u or {}
        out.append(r)
    return out


@router.post("/admin/withdrawals/{wid}/approve")
async def admin_approve_withdrawal(wid: str, _: str = Depends(get_current_admin)):
    w = await db.withdrawals.find_one({"id": wid})
    if not w:
        raise HTTPException(404, "Not found")
    if w["status"] != "pending":
        raise HTTPException(400, "Already processed")
    await db.withdrawals.update_one(
        {"id": wid},
        {"$set": {"status": "approved", "processed_at": iso(now_utc())}},
    )
    # Release hold
    await db.users.update_one(
        {"id": w["user_id"]}, {"$inc": {"withdrawals_pending": -w["amount"], "withdrawn_total": w["amount"]}}
    )
    await push_notif(
        w["user_id"],
        "withdraw",
        f"Sizning {w['amount']:,} so'm yechib olish so'rovingiz tasdiqlandi va kartaga o'tkazildi 💸",
    )
    return {"ok": True}


@router.post("/admin/withdrawals/{wid}/reject")
async def admin_reject_withdrawal(
    wid: str,
    reason: str = Body("", embed=True),
    _: str = Depends(get_current_admin),
):
    w = await db.withdrawals.find_one({"id": wid})
    if not w:
        raise HTTPException(404, "Not found")
    if w["status"] != "pending":
        raise HTTPException(400, "Already processed")
    # Return funds
    await db.users.update_one(
        {"id": w["user_id"]},
        {"$inc": {"withdrawable_balance": w["amount"], "withdrawals_pending": -w["amount"]}},
    )
    await db.withdrawals.update_one(
        {"id": wid},
        {"$set": {"status": "rejected", "rejection_reason": reason, "processed_at": iso(now_utc())}},
    )
    reason_text = reason or "ko'rsatilmagan"
    await push_notif(
        w["user_id"],
        "withdraw",
        f"Yechib olish so'rovingiz rad etildi. Sabab: {reason_text}. Mablag' qaytarildi.",
    )
    return {"ok": True}
