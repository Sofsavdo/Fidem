"""Payments (CLICK), verification, notifications, referral."""
from __future__ import annotations

import random
from datetime import datetime, timedelta

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
    parse_dt,
    push_notif,
)
from models import CreatePaymentRequest, VerificationRequest, new_id
from services import CLICK_SECRET_KEY, click_pay_link, verify_click_sign

router = APIRouter(tags=["payments"])


async def generate_payment_id() -> str:
    while True:
        pid = f"FD{datetime.now().strftime('%y%m%d')}{random.randint(1000, 9999)}"
        if not await db.payments.find_one({"id": pid}):
            return pid


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
    me = await db.users.find_one(
        {"id": uid},
        {"_id": 0, "verified_identity": 1, "verified_selfie": 1, "verified_financial": 1},
    )
    return {
        "items": rows,
        "verified_identity": bool((me or {}).get("verified_identity")),
        "verified_selfie": bool((me or {}).get("verified_selfie")),
        "verified_financial": bool((me or {}).get("verified_financial")),
    }


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

    # Smart payment: use balance first, then Click for remainder
    me = await get_user(uid)
    balance = me.get("balance", 0) or 0
    balance_used = min(balance, amount)
    click_amount = amount - balance_used

    # If balance covers full amount, no Click payment needed
    if click_amount <= 0:
        # Deduct from balance directly
        await db.users.update_one({"id": uid}, {"$inc": {"balance": -balance_used}})
        # Record payment as completed via balance
        pid = await generate_payment_id()
        doc = {
            "id": pid,
            "user_id": uid,
            "purpose": req.purpose,
            "amount": amount,
            "balance_used": balance_used,
            "click_amount": 0,
            "status": "paid",
            "method": "balance",
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc()),
        }
        if req.target_user_id:
            doc["target_user_id"] = req.target_user_id
        if req.order_id:
            doc["order_id"] = req.order_id
        await db.payments.insert_one(doc)
        # Process the purchase immediately
        await process_completed_payment(uid, req.purpose, amount, balance_used, req.target_user_id, req.order_id)
        return {"ok": True, "payment_id": pid, "status": "paid", "balance_used": balance_used, "click_amount": 0}

    pid = await generate_payment_id()

    doc = {
        "id": pid,
        "user_id": uid,
        "amount": amount,
        "purpose": req.purpose,
        "target_user_id": req.target_user_id,
        "gift_kind": req.gift_kind,
        "order_id": req.order_id,
        "balance_used": balance_used,
        "click_amount": click_amount,
        "status": "pending",
        "created_at": iso(now_utc()),
    }

    # Deduct balance portion immediately
    if balance_used > 0:
        await db.users.update_one({"id": uid}, {"$inc": {"balance": -balance_used}})

    link = click_pay_link(click_amount, pid)
    doc["payment_link"] = link
    await db.payments.insert_one(doc)

    return {"id": pid, "amount": amount, "balance_used": balance_used, "click_amount": click_amount, "payment_link": link, "status": "pending"}


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
        await db.payments.update_one(
            {"id": pid},
            {"$set": {"status": "prepared", "click_trans_id": form.get("click_trans_id")}},
        )
        return JSONResponse({
            "error": 0,
            "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid,
            "merchant_prepare_id": pid,
        })

    if action == "1":
        await process_completed_payment(
            payment["user_id"],
            payment["purpose"],
            payment["amount"],
            payment.get("balance_used", 0),
            payment.get("target_user_id"),
            payment.get("order_id")
        )
        return JSONResponse({
            "error": 0,
            "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid,
            "merchant_confirm_id": pid,
        })

    return JSONResponse({"error": -3, "error_note": "Action not found"})


async def process_completed_payment(uid: str, purpose: str, amount: int, balance_used: int, target_user_id: str = None, order_id: str = None) -> None:
    """Process a payment completed via balance (no Click needed)."""
    expiry_iso = iso(now_utc() + timedelta(days=30))

    # Phase 1.5: First paid subscription referral reward (V3.2 economy system)
    # Only for first paid subscription, not recurring
    if purpose in ("premium", "standard", "vip"):
        user = await db.users.find_one({"id": uid}, {"_id": 0, "plan": 1, "first_paid_at": 1, "referred_by": 1})
        
        # Check if this is the first paid subscription
        if user and user.get("plan") == "free" and not user.get("first_paid_at"):
            # Process referral reward
            referred_by = user.get("referred_by")
            if referred_by:
                inviter = await db.users.find_one({"referral_id": referred_by})
                if not inviter:
                    inviter = await db.users.find_one({"referral_username_lower": referred_by.lower()})
                
                if inviter:
                    # Check inviter account age >= 30 days
                    inviter_age = now_utc() - parse_dt(inviter.get("created_at", now_utc()))
                    if inviter_age >= timedelta(days=30):
                        # Check for duplicate earning (idempotency)
                        existing_earning = await db.users.find_one(
                            {
                                "id": inviter["id"],
                                "referral_earnings.referred_user_id": uid,
                                "referral_earnings.type": "paid_subscription"
                            }
                        )
                        
                        if not existing_earning:
                            # Calculate reward: 50% of amount, capped at 29,900 (39,900 for Ambassadors)
                            reward_cap = 39900 if "ambassador" in inviter.get("badges", []) else 29900
                            reward = min(int(amount * 0.5), reward_cap)
                            
                            if reward > 0:
                                hold_until = now_utc() + timedelta(days=14)
                                
                                # Create pending referral earning
                                earning_record = {
                                    "id": new_id(),
                                    "user_id": inviter["id"],
                                    "referred_user_id": uid,
                                    "type": "paid_subscription",
                                    "amount": reward,
                                    "status": "pending",
                                    "created_at": iso(now_utc()),
                                    "hold_until": iso(hold_until),
                                    "approved_at": None,
                                    "paid_at": None,
                                    "rejected_at": None,
                                    "rejection_reason": None,
                                    "gross_amount": reward,
                                    "tax_amount": 0,
                                    "net_amount": reward,
                                    "level": 1,
                                    "subscription_plan": purpose,
                                    "subscription_amount": amount,
                                }
                                
                                # Update inviter's referral earnings (atomic)
                                await db.users.update_one(
                                    {"id": inviter["id"]},
                                    {
                                        "$inc": {
                                            "referral_earnings_pending": reward,
                                            "ref_count": 1
                                        },
                                        "$push": {"referral_earnings": earning_record}
                                    }
                                )
                                
                                # Mark as first paid ONLY after earning is successfully created
                                await db.users.update_one({"id": uid}, {"$set": {"first_paid_at": iso(now_utc())}})
                                
                                # Notify inviter
                                await push_notif(
                                    inviter["id"],
                                    "referral",
                                    f"Tabriklaymiz! Sizning taklifingiz birinchi obunani faollashtirdi. {reward:,} so'm mukofot 14 kundan keyin o'tkaziladi 🎉"
                                )

    if purpose == "premium":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "premium", "plan_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", "Premium tarif faollashtirildi 💎")
    elif purpose == "standard":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "standard", "plan_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", "Standard tarif faollashtirildi ✅")
    elif purpose == "vip":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "vip", "plan_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", "VIP tarif faollashtirildi 👑")
    elif purpose == "chat_unlock":
        target_id = target_user_id
        if target_id:
            cid = chat_id_for(uid, target_id)
            await db.chat_unlocks.update_one(
                {"user_id": uid, "target_id": target_id},
                {"$setOnInsert": {
                    "id": new_id(),
                    "user_id": uid,
                    "target_id": target_id,
                    "chat_id": cid,
                    "source": "one_time",
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
        # Track balance spent for lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.balance_spent": amount}}
        )
    elif purpose == "gift":
        # Send gift to target user and increase influence for sender
        if target_user_id:
            # Add gift to target's gifts received
            await db.users.update_one(
                {"id": target_user_id},
                {"$inc": {"gifts_received_count": 1, "gifts_received_value": amount}}
            )
            # Increase sender's influence score (10% of gift value)
            influence_gain = int(amount * 0.1)
            await db.users.update_one(
                {"id": uid},
                {"$inc": {"influence_score": influence_gain}}
            )
            await push_notif(uid, "gift", f"Sovg'a yuborildi. Ta'sir +{influence_gain}")
            await push_notif(target_user_id, "gift", "Sizga sovg'a yuborildi! 🎁")
    elif purpose == "concierge":
        if order_id:
            await db.concierge_orders.update_one(
                {"id": order_id},
                {"$set": {
                    "status": "in_progress",
                    "paid_at": iso(now_utc()),
                    "expires_at": iso(now_utc() + timedelta(days=30)),
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
    await process_completed_payment(
        payment["user_id"],
        payment["purpose"],
        payment["amount"],
        payment.get("balance_used", 0),
        payment.get("target_user_id"),
        payment.get("order_id")
    )
    return {"ok": True}


@router.get("/payments/mine")
async def my_payments(uid: str = Depends(get_current_user_id)):
    rows = await db.payments.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Expire pending payments older than 10 minutes
    ten_minutes_ago = now_utc() - timedelta(minutes=10)
    for row in rows:
        if row.get("status") == "pending" and parse_dt(row.get("created_at", now_utc())) < ten_minutes_ago:
            row["status"] = "expired"
            # Update DB status to expired (idempotent)
            await db.payments.update_one(
                {"id": row["id"], "status": "pending"},
                {"$set": {"status": "expired", "updated_at": iso(now_utc())}}
            )
    
    return rows


@router.get("/notifications")
async def list_notifications(uid: str = Depends(get_current_user_id)):
    rows = await db.notifications.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


@router.post("/notifications/read-all")
async def mark_all_read(uid: str = Depends(get_current_user_id)):
    await db.notifications.update_many({"user_id": uid, "read": False}, {"$set": {"read": True}})
    return {"ok": True}


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

    redeemed = me_doc.get("invite_premium_redeemed", 0)
    eligible_redemptions = count // 3
    available_weeks = max(0, eligible_redemptions - redeemed)
    next_milestone = 3 - (count % 3) if count % 3 != 0 else 3

    # Count paid referrals (users who have made at least one successful payment)
    paid_referrals = await db.users.count_documents({
        "referred_by": code,
        "plan": {"$ne": "free"}
    })

    return {
        "code": code,
        "link": link,
        "invited_count": count,
        "invites_count": count,
        "invited": count,
        "bonus_per_invite": bonus_per_invite,
        "earned": earned,
        "vip_bonus_threshold": 5,
        "redeemed_weeks": redeemed,
        "available_weeks": available_weeks,
        "paid_referrals": paid_referrals,
        "referral_earnings_pending": me_doc.get("referral_earnings_pending", 0),
        "referral_earnings_approved": me_doc.get("referral_earnings_approved", 0),
        "referral_earnings_withdrawable": me_doc.get("referral_earnings_withdrawable", 0),
        "referral_earnings_paid_out": me_doc.get("referral_earnings_paid_out", 0),
        "next_milestone": next_milestone,
        "premium_per_milestone_days": 7,
    }
