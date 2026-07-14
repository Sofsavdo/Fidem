"""Payments (CLICK), verification, notifications, referral."""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from auth import get_current_user_id
from core import (
    PRICE_CHAT_UNLOCK,
    PRICE_PREMIUM,
    PRICE_STANDARD,
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
    rate_limit_payment,
    rate_limit_verification,
)
from models import CreatePaymentRequest, VerificationRequest, new_id
from services import CLICK_SECRET_KEY, click_pay_link, verify_click_sign

router = APIRouter(tags=["payments"])


# Referral tier system helpers
def get_tier_max_reward(monthly_count: int) -> int:
    """Get max reward based on monthly referral count."""
    if monthly_count >= 1001:
        return 49900  # Gold tier
    elif monthly_count >= 301:
        return 39900  # Silver tier
    else:
        return 29900  # Bronze tier


def get_tier_name(monthly_count: int) -> str:
    """Get tier name based on monthly referral count."""
    if monthly_count >= 1001:
        return "gold"
    elif monthly_count >= 301:
        return "silver"
    else:
        return "bronze"


async def get_monthly_referral_count(user_id: str) -> int:
    """Get current month's referral count for a user."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "monthly_referral_count": 1, "tier_reset_date": 1})
    
    # Reset monthly count if new month
    now = now_utc()
    reset_date = user.get("tier_reset_date")
    if reset_date:
        reset_dt = parse_dt(reset_date)
        # Reset if it's a new month
        if reset_dt.month != now.month or reset_dt.year != now.year:
            await db.users.update_one(
                {"id": user_id},
                {"$set": {"monthly_referral_count": 0, "tier_reset_date": iso(now)}}
            )
            return 0
    
    return user.get("monthly_referral_count", 0)


async def generate_payment_id() -> str:
    while True:
        pid = f"FD{datetime.now().strftime('%y%m%d')}{random.randint(1000, 9999)}"
        if not await db.payments.find_one({"id": pid}):
            return pid


async def apply_verification_decision(vid: str, approve: bool, reason: str = "", decided_by: str = "admin") -> bool:
    """Shared approve/reject side effects - used by both the admin panel and
    the AI auto-reviewer, so the two paths can never drift apart."""
    v = await db.verifications.find_one({"id": vid})
    if not v or v.get("status") != "pending":
        return False
    await db.verifications.update_one(
        {"id": vid},
        {"$set": {
            "status": "approved" if approve else "rejected",
            "decided_at": iso(now_utc()),
            "decided_by": decided_by,
            "rejection_reason": reason if not approve else None,
        }},
    )
    if approve:
        field = {"identity": "verified_identity", "selfie": "verified_selfie", "financial": "verified_financial"}.get(v.get("kind"))
        if field:
            await db.users.update_one({"id": v["user_id"]}, {"$set": {field: True}})
            if v.get("kind") == "financial":
                await db.users.update_one({"id": v["user_id"]}, {"$addToSet": {"badges": "b_financial"}})
        await push_notif(v["user_id"], "verified", f"✅ Tasdiqlash muvaffaqiyatli o'tdi: {v.get('kind')}")
    else:
        await push_notif(v["user_id"], "verified", f"❌ Tasdiqlash rad etildi: {reason or 'sabab ko`rsatilmagan'}")
    return True


async def _ai_review_verification(doc: dict) -> None:
    """Background AI review (Gemini, Claude fallback). Confident verdicts are
    applied automatically; anything uncertain stays pending for the admin,
    who sees the AI's verdict + reason next to the proof photo."""
    try:
        from ai_service import analyze_verification, _load_image_b64

        proof = (doc.get("proof_url") or "").strip()
        if not proof:
            return
        images: list = []
        has_profile = False
        if doc.get("kind") == "selfie":
            owner = await db.users.find_one({"id": doc["user_id"]}, {"_id": 0, "photo_url": 1})
            if owner and owner.get("photo_url"):
                try:
                    images.append(await _load_image_b64(owner["photo_url"], ""))
                    has_profile = True
                except Exception:
                    pass
        images.append(await _load_image_b64(proof, ""))

        res = await analyze_verification(doc.get("kind", ""), images, has_profile_photo=has_profile)
        await db.verifications.update_one(
            {"id": doc["id"]},
            {"$set": {
                "ai_verdict": res["verdict"],
                "ai_confidence": res["confidence"],
                "ai_reason": res["reason"],
            }},
        )
        if res["verdict"] == "approve" and res["confidence"] >= 80:
            await apply_verification_decision(doc["id"], True, decided_by="ai")
        elif res["verdict"] == "reject" and res["confidence"] >= 80:
            await apply_verification_decision(doc["id"], False, reason=res["reason"], decided_by="ai")
        # otherwise: stays pending, admin sees the AI hint
    except Exception:
        log.warning("ai verification review failed", exc_info=True)


@router.post("/verification/request")
async def request_verification(req: VerificationRequest, request: Request, uid: str = Depends(get_current_user_id)):
    rate_limit_verification(request)
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
    # AI reviews in the background - the user gets an instant answer when the
    # model is confident, and the admin queue only holds the unclear cases.
    asyncio.create_task(_ai_review_verification(doc))
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
async def create_payment(req: CreatePaymentRequest, request: Request, uid: str = Depends(get_current_user_id)):
    rate_limit_payment(request)
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
    elif req.purpose == "balance_topup":
        amount = req.amount or 0
        if amount < 1000:
            raise HTTPException(400, "Minimum top-up is 1000")
    elif req.purpose == "gift":
        amount = req.amount or 0
        if amount < 50:
            raise HTTPException(400, "Minimum 50")
    elif req.purpose == "rank_boost":
        # Direct real-money contribution to the leaderboard total (Rankings
        # page) - same ledger the gift-sending leaderboard reads from, just
        # without needing to pick a recipient. Min is 1 so'm on purpose: even
        # a 200-so'm streak bonus can be contributed from the balance, which
        # builds trust before real money ever enters. (Tiny CLICK remainders
        # are rejected below - the 1-so'm path is balance-only in practice.)
        amount = req.amount or 0
        if amount < 1:
            raise HTTPException(400, "Minimum 1")
    elif req.purpose == "boost":
        # 24h profile boost. Routed through the smart-payment flow so the
        # balance covers what it can and CLICK picks up the remainder -
        # previously the "pay with CLICK" path only topped up the balance
        # and never actually activated the boost.
        from routers.growth_r import BOOST_PRICE
        amount = BOOST_PRICE
    else:
        raise HTTPException(400, "Unknown purpose")

    # Smart payment: use balance first, then Click for remainder
    me = await get_user(uid)
    if req.purpose == "boost" and me.get("hidden_profile"):
        # Same rule as /boost/activate: boost sells visibility, a hidden
        # profile has none — don't take the money.
        raise HTTPException(400, "boost_hidden")
    balance = me.get("balance", 0) or 0

    # CLICK cannot process sub-1000-so'm charges. If the amount is 1000+,
    # we can use balance to reduce the Click charge. If the amount is <1000,
    # we must use balance only (can't send partial amounts to Click).
    if req.purpose == "balance_topup":
        # A top-up must bring NEW money in — paying it from the balance is a
        # no-op (deduct N, credit N back) that reported "success" without ever
        # opening CLICK. Top-ups therefore always go 100% through CLICK.
        balance_used = 0
        click_amount = amount
    elif amount < 1000:
        # Full amount must come from balance (Click doesn't support <1000)
        balance_used = amount
        click_amount = 0
    else:
        # Amount >= 1000: use balance first, Click pays remainder
        balance_used = min(balance, amount)
        click_amount = amount - balance_used
        # If Click remainder is still sub-1000, reduce balance_used so the
        # full amount goes to Click (which can handle >= 1000)
        if 0 < click_amount < 1000:
            # Adjust: use more balance to make Click amount exactly 0,
            # or use no balance and send full amount to Click if possible
            if balance >= amount:
                # We have enough balance for full amount
                balance_used = amount
                click_amount = 0
            else:
                # Balance insufficient for full amount, but Click minimum blocks it
                # Send full amount via Click instead
                balance_used = 0
                click_amount = amount
                if click_amount < 1000:
                    raise HTTPException(400, "click_min_1000")

    # If balance covers full amount, no Click payment needed
    if click_amount <= 0:
        # Deduct from balance directly (atomic - balance may have changed
        # since it was read above, e.g. a concurrent request)
        res = await db.users.update_one(
            {"id": uid, "balance": {"$gte": balance_used}},
            {"$inc": {"balance": -balance_used}},
        )
        if res.modified_count == 0:
            raise HTTPException(409, "Balance changed, please retry")
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

    # Deduct balance portion immediately (atomic - see full-balance branch above)
    if balance_used > 0:
        res = await db.users.update_one(
            {"id": uid, "balance": {"$gte": balance_used}},
            {"$inc": {"balance": -balance_used}},
        )
        if res.modified_count == 0:
            raise HTTPException(409, "Balance changed, please retry")

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

    if not CLICK_SECRET_KEY:
        # Fail closed: with no secret configured we cannot verify the caller
        # is actually CLICK, so no callback can be trusted (previously this
        # defaulted to accepting every unsigned request).
        log.error("CLICK_SECRET_KEY is not configured - rejecting payment callback")
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not verify_click_sign(form, action):
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not payment:
        return JSONResponse({"error": -5, "error_note": "Order not found"})
    if payment["status"] == "success":
        return JSONResponse({"error": -4, "error_note": "Already paid"})

    # Check if payment is blocked by admin
    if payment.get("blocked_by_admin"):
        return JSONResponse({"error": -6, "error_note": "Payment blocked by admin"})

    if action == "0":
        # CLICK expects the merchant to validate the amount at prepare time
        # (error -2 on mismatch). Amount arrives as a decimal string.
        try:
            prepare_amount = int(float(form.get("amount", "0") or 0))
        except (TypeError, ValueError):
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})
        if prepare_amount != payment.get("click_amount", 0):
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})
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
        # Verify payment amount matches expected amount. CLICK sends the
        # amount as a decimal string ("1000.00") — int() on that raises
        # ValueError, which 500'd the callback and made CLICK treat every
        # completion as failed.
        expected_amount = payment.get("click_amount", 0)
        try:
            received_amount = int(float(form.get("amount", "0") or 0))
        except (TypeError, ValueError):
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})
        if received_amount != expected_amount:
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})

        # Late completion: if this payment already expired, the balance
        # portion was refunded to the user (see /payments/mine). CLICK still
        # completed, so deliver the purchase - but take the refunded balance
        # part back first, otherwise the user gets it twice.
        if payment.get("status") == "expired" and payment.get("balance_used", 0) > 0:
            await db.users.update_one(
                {"id": payment["user_id"]},
                {"$inc": {"balance": -payment["balance_used"]}},
            )

        await process_completed_payment(
            payment["user_id"],
            payment["purpose"],
            payment["amount"],
            payment.get("balance_used", 0),
            payment.get("target_user_id"),
            payment.get("order_id")
        )
        await db.payments.update_one(
            {"id": pid},
            {"$set": {"status": "success", "click_trans_id": form.get("click_trans_id")}},
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

    # First paid subscription referral reward
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
                            # Calculate tier-based max reward
                            monthly_count = await get_monthly_referral_count(inviter["id"])
                            reward_cap = get_tier_max_reward(monthly_count)
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
                                    "tier_at_time": get_tier_name(monthly_count),
                                    "subscription_plan": purpose,
                                    "subscription_amount": amount,
                                }
                                
                                # Update inviter's referral earnings and monthly count (atomic)
                                await db.users.update_one(
                                    {"id": inviter["id"]},
                                    {
                                        "$inc": {
                                            "referral_earnings_pending": reward,
                                            "ref_count": 1,
                                            "monthly_referral_count": 1
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
        # Auto-activate Boost for 30 days with Premium
        boost_until = iso(now_utc() + timedelta(days=30))
        await db.users.update_one({"id": uid}, {"$set": {"boost_until": boost_until}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", "Premium tarif faollashtirildi. Boost 30 kun aktiv 💎")
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
        # Auto-activate Boost for 30 days with VIP
        boost_until = iso(now_utc() + timedelta(days=30))
        await db.users.update_one({"id": uid}, {"$set": {"boost_until": boost_until}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", "VIP tarif faollashtirildi. Boost 30 kun aktiv 👑")
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
    elif purpose == "boost":
        await db.users.update_one(
            {"id": uid},
            {"$set": {
                "boost_until": iso(now_utc() + timedelta(hours=24)),
                "boost_metrics.started_at": iso(now_utc()),
                "boost_metrics.impressions": 0,
                "boost_metrics.views": 0,
                "boost_metrics.likes": 0,
                "boost_metrics.messages": 0,
            }},
        )
        await push_notif(uid, "boost", "Profile Boost faollashtirildi — 24 soat 5x ko'proq ko'rinish 🚀")
    elif purpose == "rank_boost":
        await db.gifts.insert_one({
            "id": new_id(),
            "from_user_id": uid,
            "to_user_id": uid,
            "kind": "rank_boost",
            "price": amount,
            "is_free": False,
            "created_at": iso(now_utc()),
        })
        await push_notif(uid, "rank_boost", f"Reytingga {amount:,} so'm qo'shildi 🏆")
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


# NOTE: there is deliberately no admin "confirm payment" endpoint. CLICK
# payments and balance top-ups are confirmed automatically by the CLICK
# callback (see click_callback / process_completed_payment); balance-funded
# purchases complete instantly at create time. The only money the admin ever
# approves/rejects is a referral-earnings WITHDRAWAL request (see
# routers/withdrawals_r.py: /admin/withdrawals/{id}/approve|reject).


@router.get("/payments/mine")
async def my_payments(uid: str = Depends(get_current_user_id)):
    rows = await db.payments.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Expire pending payments older than 10 minutes
    ten_minutes_ago = now_utc() - timedelta(minutes=10)
    for row in rows:
        if row.get("status") == "pending" and parse_dt(row.get("created_at", now_utc())) < ten_minutes_ago:
            row["status"] = "expired"
            res = await db.payments.update_one(
                {"id": row["id"], "status": "pending"},
                {"$set": {"status": "expired", "updated_at": iso(now_utc())}}
            )
            # The balance portion was deducted up-front at create time; if the
            # CLICK half never completed, that money would silently vanish.
            # Refund it exactly once - the modified_count guard means only the
            # request that actually flipped pending->expired pays it back.
            if res.modified_count == 1 and row.get("balance_used", 0) > 0:
                await db.users.update_one({"id": uid}, {"$inc": {"balance": row["balance_used"]}})

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
    link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={code}"

    # Count paid referrals (users who have made at least one successful payment)
    paid_referrals = await db.users.count_documents({
        "referred_by": code,
        "plan": {"$ne": "free"}
    })

    # Tier standing - drives "how much can I earn" on the Referral page (a
    # referral pays 50% of the friend's first subscription, capped by tier).
    monthly_count = await get_monthly_referral_count(uid)
    tier = get_tier_name(monthly_count)
    tier_cap = get_tier_max_reward(monthly_count)
    next_tier_threshold = 301 if monthly_count < 301 else (1001 if monthly_count < 1001 else None)

    return {
        "code": code,
        "link": link,
        "invited_count": count,
        "invites_count": count,
        "invited": count,
        "paid_referrals": paid_referrals,
        "referral_earnings_pending": me_doc.get("referral_earnings_pending", 0),
        "referral_earnings_approved": me_doc.get("referral_earnings_approved", 0),
        "referral_earnings_withdrawable": me_doc.get("referral_earnings_withdrawable", 0),
        "referral_earnings_paid_out": me_doc.get("referral_earnings_paid_out", 0),
        "monthly_count": monthly_count,
        "monthly_tier": tier,
        "tier_cap": tier_cap,
        "next_tier_threshold": next_tier_threshold,
    }
