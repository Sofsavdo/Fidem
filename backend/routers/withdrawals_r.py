"""Referral earnings withdrawal (V3.2 economy system). Users withdraw from referral earnings only.

Gifts are NOT withdrawable. Only referral earnings can be withdrawn.
Min payout: 100,000 UZS. 12% tax withholding. Admin approves manually via CLICK transfer.
"""
from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_admin, get_current_user_id
from core import db, get_user, iso, log, now_utc, parse_dt, push_notif
from models import new_id

router = APIRouter(tags=["withdrawals"])

MIN_WITHDRAW_UZS = 100_000
TAX_RATE = 0.12  # 12% tax withholding


@router.get("/withdrawals/status")
async def withdraw_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    pending = await db.withdrawals.count_documents({"user_id": uid, "status": "pending"})
    
    # Calculate account age in days
    account_age = now_utc() - parse_dt(me.get("created_at", now_utc()))
    account_age_days = int(account_age.total_seconds() / 86400)
    
    # Count paid referrals
    earnings = me.get("referral_earnings", [])
    paid_referrals_count = 0
    for earning in earnings:
        if earning.get("type") == "paid_subscription" and earning.get("status") in ("approved", "withdrawable", "paid"):
            paid_referrals_count += 1
    
    return {
        "referral_earnings_withdrawable": int(me.get("referral_earnings_withdrawable", 0) or 0),
        "referral_earnings_pending": int(me.get("referral_earnings_pending", 0) or 0),
        "referral_earnings_paid_out": int(me.get("referral_earnings_paid_out", 0) or 0),
        "min_payout": MIN_WITHDRAW_UZS,
        "tax_rate_pct": int(TAX_RATE * 100),
        "pending_count": pending,
        "paid_referrals_count": paid_referrals_count,
        "account_age_days": account_age_days,
        "verified_identity": me.get("verified_identity", False),
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
    
    # Check account age >= 30 days
    account_age = now_utc() - parse_dt(me.get("created_at", now_utc()))
    if account_age < timedelta(days=30):
        days_left = 30 - int(account_age.total_seconds() / 86400)
        raise HTTPException(400, f"Hisobingiz {days_left} kundan keyin pul yechib olishi mumkin")
    
    # Check verification requirements
    if not me.get("verified_identity"):
        raise HTTPException(400, "Shaxsni tasdiqlash talab qilinadi (Identity verification)")
    if not me.get("verified_selfie"):
        raise HTTPException(400, "Selfie tasdiqlash talab qilinadi (Selfie verification)")
    
    # Check minimum 3 paid referrals requirement
    earnings = me.get("referral_earnings", [])
    paid_ref_count = 0
    for earning in earnings:
        if earning.get("type") == "paid_subscription" and earning.get("status") in ("approved", "withdrawable", "paid"):
            paid_ref_count += 1
    
    if paid_ref_count < 3:
        raise HTTPException(400, f"Yechib olish uchun kamida 3 ta to'langan tavsiya talab qilinadi. Hozir: {paid_ref_count}")
    
    # Check referral earnings balance
    bal = int(me.get("referral_earnings_withdrawable", 0) or 0)
    if amount > bal:
        raise HTTPException(400, f"Yetarli mablag' yo'q. Mavjud: {bal:,} so'm")
    
    card_clean = "".join(ch for ch in card_number if ch.isdigit())
    if len(card_clean) < 16:
        raise HTTPException(400, "Karta raqami noto'g'ri")
    
    # Hold the amount from referral earnings
    res = await db.users.update_one(
        {"id": uid, "referral_earnings_withdrawable": {"$gte": amount}},
        {"$inc": {"referral_earnings_withdrawable": -amount, "withdrawals_pending": amount}},
    )
    if res.modified_count == 0:
        raise HTTPException(400, "Mablag' yetarli emas yoki bir vaqtda boshqa so'rov qilindi")
    
    wid = new_id()
    doc = {
        "id": wid,
        "user_id": uid,
        "amount": amount,  # Gross amount
        "tax_amount": 0,   # Will be set on approval
        "net_amount": 0,   # Will be set on approval
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
    
    # Calculate tax (12%)
    gross_amount = w["amount"]
    tax_amount = int(gross_amount * TAX_RATE)
    net_amount = gross_amount - tax_amount
    
    # Release hold and update referral earnings FIRST (idempotency)
    res = await db.users.update_one(
        {"id": w["user_id"], "withdrawals_pending": {"$gte": gross_amount}},
        {"$inc": {
            "withdrawals_pending": -gross_amount,
            "referral_earnings_paid_out": net_amount,
            "referral_earnings_tax_withheld": tax_amount,
            "withdrawn_total": net_amount,
            "tax_paid_total": tax_amount
        }}
    )
    
    if res.modified_count == 0:
        raise HTTPException(400, "Failed to update user balance - may have been already processed")
    
    # Mark withdrawal as paid AFTER user balance is updated
    await db.withdrawals.update_one(
        {"id": wid},
        {"$set": {
            "status": "paid",
            "processed_at": iso(now_utc()),
            "tax_amount": tax_amount,
            "net_amount": net_amount
        }},
    )
    
    await push_notif(
        w["user_id"],
        "withdraw",
        f"Sizning {gross_amount:,} so'm yechib olish so'rovingiz tasdiqlandi. Soliq: {tax_amount:,} so'm, Net: {net_amount:,} so'm 💸",
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
    # Return funds to referral earnings
    await db.users.update_one(
        {"id": w["user_id"]},
        {"$inc": {"referral_earnings_withdrawable": w["amount"], "withdrawals_pending": -w["amount"]}},
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
