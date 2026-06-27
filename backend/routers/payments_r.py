"""Payments (CLICK), verification, notifications, referral."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from auth import get_current_admin, get_current_user_id
from core import (
    PRICE_CHAT_UNLOCK,
    PRICE_PREMIUM,
    PRICE_STANDARD,
    PRICE_SUPER,
    PRICE_VIP,
    TELEGRAM_BOT_USERNAME,
    chat_id_for,
    db,
    get_user,
    iso,
    log,
    now_utc,
    push_notif,
)
from datetime import timedelta
from models import CreatePaymentRequest, VerificationRequest, new_id
from services import CLICK_SECRET_KEY, click_pay_link, verify_click_sign

router = APIRouter(tags=["payments"])


# ---------- Verification ----------
@router.post("/verification/request")
async def request_verification(req: VerificationRequest, uid: str = Depends(get_current_user_id)):
    doc = {
        "id": new_id(),
        "user_id": uid,
        "kind": req.kind,
        "note": req.note,
        "proof_url": req.proof_url,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    await db.verifications.insert_one(doc)
    return {"ok": True, "id": doc["id"]}


@router.get("/verification/mine")
async def my_verifications(uid: str = Depends(get_current_user_id)):
    rows = await db.verifications.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(50)
    me = await db.users.find_one({"id": uid}, {"_id": 0, "verified_identity": 1, "verified_selfie": 1, "verified_financial": 1})
    return {
        "items": rows,
        "verified_identity": bool((me or {}).get("verified_identity")),
        "verified_selfie": bool((me or {}).get("verified_selfie")),
        "verified_financial": bool((me or {}).get("verified_financial")),
    }


# ---------- Payments ----------
@router.post("/payments/create")
async def create_payment(req: CreatePaymentRequest, uid: str = Depends(get_current_user_id)):
    if req.purpose == "premium":
        amount = PRICE_PREMIUM
    elif req.purpose == "standard":
        amount = PRICE_STANDARD
    elif req.purpose == "vip":
        amount = PRICE_VIP
    elif req.purpose == "chat_unlock":
        amount = PRICE_CHAT_UNLOCK
        if not req.target_user_id:
            raise HTTPException(400, "target_user_id required for chat_unlock")
    elif req.purpose == "super_application":
        amount = PRICE_SUPER
    elif req.purpose == "balance_topup":
        amount = req.amount or 0
        if amount < 1000:
            raise HTTPException(400, "Minimum top-up is 1000")
    elif req.purpose == "gift":
        amount = req.amount or 0
        if amount < 50:
            raise HTTPException(400, "Minimum 50")
    else:
        raise HTTPException(400, "Unknown purpose")
    pid = new_id()
    doc = {
        "id": pid,
        "user_id": uid,
        "amount": amount,
        "purpose": req.purpose,
        "target_user_id": req.target_user_id,
        "gift_kind": req.gift_kind,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    link = click_pay_link(amount, pid)
    doc["payment_link"] = link
    await db.payments.insert_one(doc)
    return {"id": pid, "amount": amount, "payment_link": link, "status": "pending"}


@router.post("/payments/click/callback")
async def click_callback(request: Request):
    form_data = await request.form()
    form = dict(form_data)
    action = form.get("action", "0")
    pid = form.get("merchant_trans_id", "")
    payment = await db.payments.find_one({"id": pid})

    sign_ok = True
    if CLICK_SECRET_KEY:
        sign_ok = verify_click_sign(form, action)

    if not sign_ok:
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not payment:
        return JSONResponse({"error": -5, "error_note": "Order not found"})
    if payment["status"] == "success":
        return JSONResponse({"error": -4, "error_note": "Already paid"})
    if action == "0":
        await db.payments.update_one({"id": pid}, {"$set": {"status": "prepared", "click_trans_id": form.get("click_trans_id")}})
        return JSONResponse({
            "error": 0, "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid, "merchant_prepare_id": pid,
        })
    if action == "1":
        await apply_payment_success(payment)
        return JSONResponse({
            "error": 0, "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid, "merchant_confirm_id": pid,
        })
    return JSONResponse({"error": -3, "error_note": "Action not found"})


async def apply_payment_success(payment: dict) -> None:
    pid = payment["id"]
    await db.payments.update_one({"id": pid}, {"$set": {"status": "success", "paid_at": iso(now_utc())}})
    uid = payment["user_id"]
    purpose = payment["purpose"]
    amount = payment["amount"]
    expiry_iso = iso(now_utc() + timedelta(days=30))
    if purpose == "premium":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "premium", "plan_until": expiry_iso}})
        await push_notif(uid, "premium", "Premium tarif faollashtirildi 💎")
    elif purpose == "standard":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "standard", "plan_until": expiry_iso}})
        await push_notif(uid, "premium", "Standard tarif faollashtirildi ✅")
    elif purpose == "vip":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "vip", "plan_until": expiry_iso}})
        await push_notif(uid, "premium", "VIP tarif faollashtirildi 👑")
    elif purpose == "chat_unlock":
        target_id = payment.get("target_user_id")
        if target_id:
            cid = chat_id_for(uid, target_id)
            await db.chat_unlocks.update_one(
                {"user_id": uid, "target_id": target_id},
                {"$setOnInsert": {
                    "id": new_id(), "user_id": uid, "target_id": target_id,
                    "chat_id": cid, "source": "one_time",
                    "created_at": iso(now_utc()),
                    "guarantee_until": iso(now_utc() + timedelta(hours=48)),
                    "guarantee_refunded": False,
                }},
                upsert=True,
            )
            await push_notif(uid, "premium", "Suhbat ochildi — endi yozishingiz mumkin ✅", link=f"/chat/{target_id}")
    elif purpose == "balance_topup":
        await db.users.update_one({"id": uid}, {"$inc": {"balance": amount}})
        await push_notif(uid, "balance", f"Balansingiz {amount:,} so'mga to'ldirildi")
    elif purpose == "super_application":
        await db.users.update_one({"id": uid}, {"$inc": {"super_applications_available": 1}})
        await push_notif(uid, "balance", "Super murojaat sotib olindi")
    elif purpose == "gift":
        await db.users.update_one({"id": uid}, {"$inc": {"balance": amount}})
    elif purpose == "concierge":
        order_id = payment.get("order_id")
        if order_id:
            from datetime import timedelta as _td
            await db.concierge_orders.update_one(
                {"id": order_id},
                {"$set": {
                    "status": "in_progress",
                    "paid_at": iso(now_utc()),
                    "expires_at": iso(now_utc() + _td(days=30)),
                }},
            )
            await push_notif(uid, "concierge", "💎 Sovchi Concierge buyurtmangiz qabul qilindi. Admin sizga 5 ta mosni qo'lda topadi!")


@router.post("/payments/admin-confirm/{payment_id}")
async def admin_confirm_payment(payment_id: str, _: str = Depends(get_current_admin)):
    payment = await db.payments.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(404, "Not found")
    if payment["status"] == "success":
        return {"ok": True}
    await apply_payment_success(payment)
    return {"ok": True}


@router.get("/payments/mine")
async def my_payments(uid: str = Depends(get_current_user_id)):
    rows = await db.payments.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


# ---------- Notifications ----------
@router.get("/notifications")
async def list_notifications(uid: str = Depends(get_current_user_id)):
    rows = await db.notifications.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


@router.post("/notifications/read-all")
async def mark_all_read(uid: str = Depends(get_current_user_id)):
    await db.notifications.update_many({"user_id": uid, "read": False}, {"$set": {"read": True}})
    return {"ok": True}


# ---------- Referral ----------
@router.get("/referral/mine")
async def my_referral(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    code = me_doc.get("referral_code")
    if not code:
        code = uid[:8]
        await db.users.update_one({"id": uid}, {"$set": {"referral_code": code}})
    count = await db.users.count_documents({"referred_by": code})
    bonus_per_invite = 10000
    earned = count * bonus_per_invite
    link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={code}"
    return {
        "code": code,
        "link": link,
        "invited_count": count,
        "invites_count": count,  # alias
        "bonus_per_invite": bonus_per_invite,
        "earned": earned,
        "vip_bonus_threshold": 5,
    }
