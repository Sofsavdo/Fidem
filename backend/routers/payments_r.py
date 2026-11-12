"""Payments (CLICK), verification, notifications, referral."""
from __future__ import annotations

import asyncio
import os
import random
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from auth import get_current_user_id
from core import (
    PLAN_PRICES,
    PREMIUM_PERIODS,
    PRICE_CHAT_UNLOCK,
    TELEGRAM_BOT_USERNAME,
    chat_id_for,
    db,
    get_user,
    women_free_active,
    iso,
    log,
    now_utc,
    parse_dt,
    push_notif,
    rate_limit_payment,
    rate_limit_verification,
)
from models import CreatePaymentRequest, VerificationRequest, new_id
from hamyon import (
    HAMYON_SHOP_ID,
    HamyonError,
    cancel_hamyon_payment,
    create_hamyon_payment,
    hamyon_enabled,
    hamyon_payment_status,
    verify_hamyon_sign,
)
from services import CLICK_SECRET_KEY, click_pay_link, verify_click_sign
from sofsavdo_integration import report_sofsavdo_conversion

router = APIRouter(tags=["payments"])

HAMYON_OPEN = ("pending", "prepared")
# A referral pays only when the inviter's account is at least this old.
REFERRAL_MIN_INVITER_AGE_DAYS = int(os.environ.get("REFERRAL_MIN_INVITER_AGE_DAYS", "3"))
# Last status Hamyon reported per payment, so the log shows changes only.
_HAMYON_LAST_STATUS: dict[str, str] = {}


def _hamyon_view(doc: dict) -> dict:
    """What the app needs to show the transfer screen and follow the result."""
    expire_at = int(doc.get("expire_at") or 0)
    return {
        "id": doc["id"],
        "method": "hamyon",
        "status": doc.get("status"),
        "purpose": doc.get("purpose"),
        "amount": doc.get("amount"),
        "balance_used": doc.get("balance_used", 0),
        "pay_amount": doc.get("hamyon_amount"),
        "card": doc.get("card"),
        "expire_at": expire_at,
        "expires_in": max(0, expire_at - int(time.time())) if expire_at else 0,
    }


async def start_hamyon_payment(doc: dict) -> dict:
    """Record the payment, then open it at Hamyon. doc carries id, user_id,
    purpose, amount, balance_used (already deducted) and click_amount (the
    part to pay by card). The record is saved first because Hamyon's prepare
    callback may arrive before its create answer does."""
    doc.update(method="hamyon", status="pending", created_at=iso(now_utc()))
    await db.payments.insert_one(doc)
    doc.pop("_id", None)
    since = iso(now_utc() - timedelta(minutes=7))
    open_rows = await db.payments.find(
        {"method": "hamyon", "status": {"$in": list(HAMYON_OPEN)}, "created_at": {"$gte": since},
         "hamyon_amount": {"$exists": True}},
        {"_id": 0, "hamyon_amount": 1},
    ).to_list(1000)
    busy = {int(r["hamyon_amount"]) for r in open_rows if r.get("hamyon_amount")}
    try:
        res = await create_hamyon_payment(doc["id"], int(doc["click_amount"]), busy)
    except HamyonError as e:
        log.error("Hamyon create failed for %s: %s", doc["id"], e)
        await db.payments.update_one({"id": doc["id"]}, {"$set": {"status": "failed", "error": str(e)[:200]}})
        if doc.get("balance_used", 0) > 0:
            await db.users.update_one({"id": doc["user_id"]}, {"$inc": {"balance": doc["balance_used"]}})
        raise HTTPException(502, "payment_provider_error")
    upd = {
        "hamyon_payment_id": str(res["payment_id"]),
        "hamyon_amount": int(res["amount"]),
        "card": str(res["card"]),
        "expire_at": int(res.get("expire_at") or (time.time() + int(res.get("expires_in") or 300))),
    }
    await db.payments.update_one({"id": doc["id"]}, {"$set": upd})
    doc.update(upd)
    # Hamyon's own id is what their support asks for when a transfer was not matched.
    log.info("Hamyon created: order=%s hamyon_id=%s amount=%s purpose=%s",
             doc["id"], upd["hamyon_payment_id"], upd["hamyon_amount"], doc.get("purpose"))
    return _hamyon_view(doc)


async def apply_hamyon_result(payment: dict, status: str, paid_amount: int | None = None,
                              reason: str = "", paid_at=None) -> None:
    """Single place that settles a Hamyon payment (callback, status check or
    the user's cancel). Safe to call many times: the purchase is delivered
    exactly once, and a cancel refunds the balance part exactly once."""
    pid = payment["id"]
    if status == "paid":
        expected = int(payment.get("hamyon_amount") or payment.get("click_amount") or 0)
        if paid_amount is not None and paid_amount != expected:
            log.error("Hamyon %s: paid amount %s differs from expected %s - not delivered", pid, paid_amount, expected)
            await db.payments.update_one({"id": pid}, {"$set": {"amount_mismatch": paid_amount}})
            return
        prev = await db.payments.find_one_and_update(
            {"id": pid, "status": {"$in": [*HAMYON_OPEN, "expired", "cancelled"]}},
            {"$set": {"status": "processing", "updated_at": iso(now_utc())}},
        )
        if not prev:
            return  # already delivered (Hamyon repeats the callback)
        # A top-up credits what was really transferred (it may be 1-2 so'm
        # above the asked sum because of the unique-amount rule).
        amount = expected if prev["purpose"] == "balance_topup" else prev["amount"]
        try:
            await process_completed_payment(
                prev["user_id"], prev["purpose"], amount, prev.get("balance_used", 0),
                prev.get("target_user_id"), prev.get("order_id"), prev.get("months", 1), payment_id=pid,
                days=prev.get("days"),
            )
        except Exception:
            await db.payments.update_one({"id": pid, "status": "processing"}, {"$set": {"status": prev["status"]}})
            raise
        upd = {"status": "success", "paid_at": iso(now_utc()), "hamyon_paid_at": paid_at}
        if prev.get("balance_refunded") and prev.get("balance_used", 0) > 0:
            # Cancelled/expired earlier and the balance part went back; the
            # money did arrive after all, so take that part again.
            await db.users.update_one({"id": prev["user_id"]}, {"$inc": {"balance": -prev["balance_used"]}})
            upd["balance_refunded"] = False
        await db.payments.update_one({"id": pid}, {"$set": upd})
        log.info("Hamyon %s paid: %s %s so'm", pid, prev["purpose"], expected)
        return

    prev = await db.payments.find_one_and_update(
        {"id": pid, "status": {"$in": list(HAMYON_OPEN)}},
        {"$set": {"status": "cancelled", "cancel_reason": reason or "", "updated_at": iso(now_utc())}},
    )
    if prev and prev.get("balance_used", 0) > 0:
        await db.users.update_one({"id": prev["user_id"]}, {"$inc": {"balance": prev["balance_used"]}})
        await db.payments.update_one({"id": pid}, {"$set": {"balance_refunded": True}})


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
    # One paid plan (Premium) is on sale. Standard/VIP stay valid for people who
    # already hold them (and admin grants) but can no longer be bought.
    if req.purpose in ("standard", "vip"):
        raise HTTPException(400, "plan_unavailable")
    if req.purpose in ("premium", "standard", "vip"):
        if req.purpose == "premium" and req.days:
            amount = PREMIUM_PERIODS[req.days]
        else:
            amount = PLAN_PRICES[req.purpose][req.months]
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
            "months": req.months,
            "days": req.days,
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
        await process_completed_payment(uid, req.purpose, amount, balance_used, req.target_user_id, req.order_id, req.months, payment_id=pid, days=req.days)
        return {"ok": True, "payment_id": pid, "status": "paid", "balance_used": balance_used, "click_amount": 0}

    # Hamyon (card transfer, confirmed automatically) is the main way to pay
    # whenever its keys are set; CLICK / manual P2P below are older fallbacks.
    if hamyon_enabled():
        if balance_used > 0:
            res = await db.users.update_one(
                {"id": uid, "balance": {"$gte": balance_used}},
                {"$inc": {"balance": -balance_used}},
            )
            if res.modified_count == 0:
                raise HTTPException(409, "Balance changed, please retry")
        doc = {
            "id": await generate_payment_id(),
            "user_id": uid,
            "amount": amount,
            "purpose": req.purpose,
            "months": req.months,
            "days": req.days,
            "target_user_id": req.target_user_id,
            "gift_kind": req.gift_kind,
            "order_id": req.order_id,
            "balance_used": balance_used,
            "click_amount": click_amount,
        }
        return await start_hamyon_payment(doc)

    # While P2P mode is on (CLICK temporarily disabled by the admin), nothing
    # may route to CLICK — users top the balance up via card transfer instead
    # and every purchase is balance-funded. Frontends map this code to a
    # "top up your balance first" hint instead of a dead CLICK redirect.
    cfg = await db.settings.find_one({"id": "topup_config"}) or {}
    if cfg.get("p2p_enabled"):
        raise HTTPException(400, "click_disabled")

    # CLICK not (fully) configured: the callback would be rejected, so sending
    # the user there ends in CLICK's "Xatolik ro'y berdi" page - and the
    # balance portion below would already be deducted. Refuse up front with the
    # same code the frontend already turns into a "pay another way" hint.
    from services import CLICK_MERCHANT_ID, CLICK_SERVICE_ID
    if not (CLICK_SECRET_KEY and CLICK_MERCHANT_ID and CLICK_SERVICE_ID):
        log.error("CLICK is not fully configured (merchant/service/secret) - refusing to create a CLICK payment")
        raise HTTPException(400, "click_disabled")

    pid = await generate_payment_id()

    doc = {
        "id": pid,
        "user_id": uid,
        "amount": amount,
        "purpose": req.purpose,
        "months": req.months,
        "days": req.days,
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

    # Diagnostic: CLICK always gets HTTP 200 (protocol requirement) even on
    # a rejected transaction - the actual pass/fail lives in the JSON body's
    # "error" field, which never showed up in Railway logs before this line.
    # Temporary while we track down the "xatolik ro'y berdi" report; safe to
    # trim once confirmed, no sign/card data included.
    log.info(
        "CLICK callback: action=%s pid=%s click_trans_id=%s amount=%s found=%s status=%s",
        action, pid, form.get("click_trans_id"), form.get("amount"),
        bool(payment), (payment or {}).get("status"),
    )
    if not CLICK_SECRET_KEY:
        # Fail closed: with no secret configured we cannot verify the caller
        # is actually CLICK, so no callback can be trusted (previously this
        # defaulted to accepting every unsigned request).
        log.error("CLICK_SECRET_KEY is not configured - rejecting payment callback")
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not verify_click_sign(form, action):
        log.warning("CLICK callback: SIGN CHECK FAILED for pid=%s action=%s", pid, action)
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not payment:
        log.warning("CLICK callback: order not found for merchant_trans_id=%s", pid)
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
            log.warning("CLICK callback: bad amount format %r for pid=%s", form.get("amount"), pid)
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})
        if prepare_amount != payment.get("click_amount", 0):
            log.warning(
                "CLICK callback: amount mismatch for pid=%s - click sent %s, expected %s",
                pid, prepare_amount, payment.get("click_amount", 0),
            )
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
            log.warning("CLICK callback: bad amount format %r for pid=%s (complete)", form.get("amount"), pid)
            return JSONResponse({"error": -2, "error_note": "Incorrect parameter amount"})
        if received_amount != expected_amount:
            log.warning(
                "CLICK callback: amount mismatch for pid=%s (complete) - click sent %s, expected %s",
                pid, received_amount, expected_amount,
            )
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
            payment.get("order_id"),
            payment.get("months", 1),
            payment_id=pid,
            days=payment.get("days"),
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


# ---------- Hamyon callbacks (set these URLs in the Hamyon bot) ----------
#   prepare_url  = https://<backend>/api/payments/hamyon/prepare
#   complete_url = https://<backend>/api/payments/hamyon/complete
async def _hamyon_form(request: Request) -> dict:
    return {k: str(v) for k, v in dict(await request.form()).items()}


async def _find_hamyon_payment(form: dict) -> dict | None:
    """Our payment id travels as Hamyon's order_id; Hamyon's own id is kept too."""
    p = None
    if form.get("order_id"):
        p = await db.payments.find_one({"id": form["order_id"], "method": "hamyon"}, {"_id": 0})
    if not p and form.get("payment_id"):
        p = await db.payments.find_one({"hamyon_payment_id": form["payment_id"], "method": "hamyon"}, {"_id": 0})
    if p and p.get("hamyon_payment_id") and form.get("payment_id") and p["hamyon_payment_id"] != form["payment_id"]:
        log.warning("Hamyon callback: payment_id %s does not match order %s", form.get("payment_id"), p["id"])
        return None
    return p


@router.post("/payments/hamyon/prepare")
async def hamyon_prepare(request: Request):
    form = await _hamyon_form(request)
    if not verify_hamyon_sign(form):
        log.warning("Hamyon prepare: bad sign (order=%s)", form.get("order_id"))
        return JSONResponse({"error": "sign"}, status_code=403)
    p = await _find_hamyon_payment(form)
    if p:
        await db.payments.update_one(
            {"id": p["id"]},
            {"$set": {"hamyon_payment_id": form.get("payment_id"), "hamyon_prepared_at": iso(now_utc())}},
        )
    else:
        log.warning("Hamyon prepare: order %s not found", form.get("order_id"))
    return {"result": "ok"}


@router.post("/payments/hamyon/complete")
async def hamyon_complete(request: Request):
    form = await _hamyon_form(request)
    if not verify_hamyon_sign(form):
        log.warning("Hamyon complete: bad sign (order=%s)", form.get("order_id"))
        return JSONResponse({"error": "sign"}, status_code=403)
    p = await _find_hamyon_payment(form)
    log.info("Hamyon complete: order=%s status=%s amount=%s found=%s",
             form.get("order_id"), form.get("status"), form.get("amount"), bool(p))
    if not p:
        # Nothing to retry into; answer 200 so Hamyon stops repeating it.
        return {"result": "ok"}
    try:
        paid_amount = int(float(form.get("amount") or 0))
    except ValueError:
        paid_amount = -1
    try:
        await apply_hamyon_result(p, "paid" if form.get("status") == "paid" else "cancel",
                                  paid_amount, form.get("reason", ""), form.get("paid_at"))
    except Exception:
        log.exception("Hamyon complete: delivering %s failed", p["id"])
        # Non-2xx makes Hamyon retry (0s, 3s, 10s, 30s, 60s).
        return JSONResponse({"error": "retry"}, status_code=500)
    return {"result": "ok"}


async def _sync_with_hamyon(p: dict) -> str | None:
    """Ask Hamyon for the state of one open payment and settle it here if
    Hamyon already finished it. Returns Hamyon's status, None on error."""
    pid = p["id"]
    try:
        st = await hamyon_payment_status(p["hamyon_payment_id"])
        status = st.get("status")
        if _HAMYON_LAST_STATUS.get(pid) != status:
            _HAMYON_LAST_STATUS[pid] = status
            log.info("Hamyon status: order=%s hamyon=%s amount=%s", pid, status, st.get("amount"))
        if str(st.get("shop_id", HAMYON_SHOP_ID)) != HAMYON_SHOP_ID:
            return None
        if status == "paid":
            await apply_hamyon_result(p, "paid", int(st.get("amount") or 0))
        elif status == "cancel":
            await apply_hamyon_result(p, "cancel", reason="timeout")
        return status
    except HamyonError as e:
        log.info("Hamyon status check for %s failed: %s", pid, e)
    except Exception:
        log.exception("Hamyon status check for %s failed", pid)
    return None


async def reconcile_open_hamyon_payments() -> int:
    """Safety net for lost callbacks when nobody keeps the pay sheet open:
    every card payment still open 2 minutes to 2 hours after it was made is
    checked with Hamyon and settled. Returns how many were settled."""
    if not hamyon_enabled():
        return 0
    now = now_utc()
    rows = await db.payments.find(
        {"method": "hamyon", "status": {"$in": list(HAMYON_OPEN)}, "hamyon_payment_id": {"$exists": True},
         "created_at": {"$lte": iso(now - timedelta(minutes=2)), "$gte": iso(now - timedelta(hours=2))}},
        {"_id": 0},
    ).to_list(200)
    settled = 0
    for p in rows:
        if await _sync_with_hamyon(p) in ("paid", "cancel"):
            settled += 1
        await asyncio.sleep(0.2)
    return settled


async def hamyon_reconcile_loop() -> None:
    while True:
        try:
            n = await reconcile_open_hamyon_payments()
            if n:
                log.info("Hamyon reconcile: settled %s open payments", n)
        except Exception as e:  # noqa: BLE001 - keep the loop alive
            log.warning(f"Hamyon reconcile loop error: {e}")
        await asyncio.sleep(90)


@router.get("/payments/status/{pid}")
async def payment_status(pid: str, uid: str = Depends(get_current_user_id)):
    """Polled by the transfer screen. For an open Hamyon payment it also asks
    Hamyon directly now and then, so a lost callback (or a wrong complete_url)
    still ends in a delivered purchase."""
    p = await db.payments.find_one({"id": pid, "user_id": uid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "not_found")
    if p.get("method") == "hamyon" and p.get("status") in HAMYON_OPEN and p.get("hamyon_payment_id"):
        now_ts = time.time()
        claimed = await db.payments.update_one(
            {"id": pid, "$or": [{"hamyon_checked_at": {"$exists": False}}, {"hamyon_checked_at": {"$lt": now_ts - 8}}]},
            {"$set": {"hamyon_checked_at": now_ts}},
        )
        if claimed.modified_count:
            await _sync_with_hamyon(p)
            p = await db.payments.find_one({"id": pid}, {"_id": 0}) or p
    if p.get("method") == "hamyon":
        return _hamyon_view(p)
    return {"id": p["id"], "status": p.get("status"), "purpose": p.get("purpose"), "method": p.get("method")}


@router.post("/payments/cancel/{pid}")
async def cancel_payment(pid: str, uid: str = Depends(get_current_user_id)):
    """The user gave up on a card transfer: close it at Hamyon (so the amount
    frees up) and refund any balance part right away."""
    p = await db.payments.find_one({"id": pid, "user_id": uid}, {"_id": 0})
    if not p:
        raise HTTPException(404, "not_found")
    if p.get("method") == "hamyon" and p.get("status") in HAMYON_OPEN:
        if p.get("hamyon_payment_id"):
            try:
                await cancel_hamyon_payment(p["hamyon_payment_id"])
            except HamyonError as e:
                log.info("Hamyon cancel for %s: %s", pid, e)
        await apply_hamyon_result(p, "cancel", reason="user")
        p = await db.payments.find_one({"id": pid}, {"_id": 0}) or p
    return {"ok": True, "status": p.get("status")}


async def process_completed_payment(uid: str, purpose: str, amount: int, balance_used: int, target_user_id: str = None, order_id: str = None, months: int = 1, payment_id: str = None, days: int | None = None) -> None:
    """Deliver a paid purchase (balance, card transfer or CLICK)."""
    duration_days = days or months * 30

    # First paid subscription referral reward
    # Only for first paid subscription, not recurring
    if purpose in ("premium", "standard", "vip"):
        user = await db.users.find_one({"id": uid}, {"_id": 0, "plan": 1, "plan_until": 1, "first_paid_at": 1, "referred_by": 1, "sofsavdo_click_token": 1})

        # Sofsavdo integration - independent of the internal Fidem referral logic
        # below (this user may have no `referred_by` at all, or a different
        # referrer than whoever's Sofsavdo Flow link brought them here). Only
        # ever fires on this user's first-ever paid subscription, same "free ->
        # paid" signal the internal referral reward below uses - a renewal or
        # upgrade must never re-trigger a creator commission. Never allowed to
        # affect this payment: report_sofsavdo_conversion swallows its own errors.
        #
        # The reward is Fidem's own real referral economics - 50% of the
        # payment, capped by tier - not a generic rate Sofsavdo's admin could
        # set arbitrarily. A Sofsavdo creator isn't a Fidem user and has no
        # monthly_referral_count of their own, so they're always priced at the
        # base (bronze) tier cap, same as a brand-new Fidem-internal referrer.
        if user and user.get("plan") == "free" and not user.get("first_paid_at") and user.get("sofsavdo_click_token"):
            sofsavdo_reward = min(int(amount * 0.5), get_tier_max_reward(0))
            if sofsavdo_reward > 0:
                await report_sofsavdo_conversion(user["sofsavdo_click_token"], payment_id or order_id or new_id(), amount, sofsavdo_reward, purpose)
        # Renewing the same tier (or better) before it expires extends from
        # the remaining time instead of overwriting it - buying a fresh
        # 3-month plan with 10 days of the current one left should leave 3
        # months + 10 days, not just 3 months.
        from routers.chat_r import PLAN_RANK
        stored_until = (user or {}).get("plan_until")
        current_plan = (user or {}).get("plan")
        is_active = bool(stored_until and parse_dt(stored_until) > now_utc())
        if is_active and current_plan in PLAN_RANK and PLAN_RANK.get(current_plan, -1) >= PLAN_RANK.get(purpose, -1):
            expiry_iso = iso(parse_dt(stored_until) + timedelta(days=duration_days))
        else:
            expiry_iso = iso(now_utc() + timedelta(days=duration_days))
        
        # Check if this is the first paid subscription
        if user and user.get("plan") == "free" and not user.get("first_paid_at"):
            # Process referral reward
            referred_by = user.get("referred_by")
            if referred_by:
                inviter = await db.users.find_one({"referral_id": referred_by})
                if not inviter:
                    inviter = await db.users.find_one({"referral_username_lower": referred_by.lower()})
                
                if inviter and inviter.get("id") != uid and not inviter.get("blocked"):
                    # Fraud guard: a brand-new inviter account earns nothing.
                    # 30 days meant NOBODY could earn in a newly launched app;
                    # the 14-day hold below still protects against refunds.
                    inviter_age = now_utc() - parse_dt(inviter.get("created_at", now_utc()))
                    if inviter_age >= timedelta(days=REFERRAL_MIN_INVITER_AGE_DAYS):
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
                                
                                
                                # Notify inviter
                                await push_notif(
                                    inviter["id"],
                                    "referral",
                                    f"Tabriklaymiz! Sizning taklifingiz birinchi obunani faollashtirdi. {reward:,} so'm mukofot 14 kundan keyin o'tkaziladi 🎉"
                                )

        # The first paid subscription is a one-time event: mark it whatever
        # happened above (no inviter, young inviter...). It used to be set only
        # when a referral reward was created, so a later renewal could still
        # pay a referral reward and re-report a Sofsavdo conversion.
        if user and not user.get("first_paid_at"):
            await db.users.update_one({"id": uid, "first_paid_at": {"$exists": False}}, {"$set": {"first_paid_at": iso(now_utc())}})

    duration_label = (
        {1: "1 kun", 15: "15 kun", 30: "1 oy"}.get(days, f"{days} kun") if days
        else {1: "1 oy", 3: "3 oy", 12: "1 yil"}.get(months, f"{months} oy")
    )
    if purpose == "premium":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "premium", "plan_until": expiry_iso}})
        # Boost stays active exactly as long as the plan does, not a flat 30
        # days regardless of the term bought.
        # (not while hidden mode is on - a boost would only pay for invisibility)
        await db.users.update_one({"id": uid, "hidden_profile": {"$ne": True}}, {"$set": {"boost_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", f"Premium tarif faollashtirildi ({duration_label}). Boost ham shuncha muddat aktiv 💎")
    elif purpose == "standard":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "standard", "plan_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", f"Standard tarif faollashtirildi ({duration_label}) ✅")
    elif purpose == "vip":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "vip", "plan_until": expiry_iso}})
        # Boost stays active exactly as long as the plan does, not a flat 30
        # days regardless of the term bought.
        # (not while hidden mode is on - a boost would only pay for invisibility)
        await db.users.update_one({"id": uid, "hidden_profile": {"$ne": True}}, {"$set": {"boost_until": expiry_iso}})
        # Add to lifetime contribution
        await db.users.update_one(
            {"id": uid},
            {"$inc": {"lifetime_contribution": amount, "lifetime_contribution_breakdown.subscription_payments": amount}}
        )
        await push_notif(uid, "premium", f"VIP tarif faollashtirildi ({duration_label}). Boost ham shuncha muddat aktiv 👑")
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
            await push_notif(uid, "concierge", "💎 Shaxsiy sovchi buyurtmangiz qabul qilindi. Admin sizga 5 ta mosni qo'lda topadi!")


# NOTE: there is deliberately no admin "confirm payment" endpoint. CLICK
# payments and balance top-ups are confirmed automatically by the CLICK
# callback (see click_callback / process_completed_payment); balance-funded
# purchases complete instantly at create time. The only money the admin ever
# approves/rejects is a referral-earnings WITHDRAWAL request (see
# routers/withdrawals_r.py: /admin/withdrawals/{id}/approve|reject).


# --- Manual (P2P card transfer) top-up — temporary fallback while CLICK is
# --- being sorted out. Admin sets a card number and toggles p2p_enabled; the
# --- user transfers money card-to-card, attaches a receipt screenshot, and an
# --- admin credits the balance after checking the actual card statement.

@router.get("/payments/topup-config")
async def topup_config(uid: str = Depends(get_current_user_id)):
    cfg = await db.settings.find_one({"id": "topup_config"}, {"_id": 0}) or {}
    enabled = bool(cfg.get("p2p_enabled"))
    from services import CLICK_MERCHANT_ID, CLICK_SERVICE_ID
    click_enabled = bool(CLICK_SECRET_KEY and CLICK_MERCHANT_ID and CLICK_SERVICE_ID)
    # payments_available lets the app show a clear "coming soon" state instead
    # of sending users into a payment flow that cannot complete.
    hamyon_on = hamyon_enabled()
    out = {
        "p2p_enabled": enabled and not hamyon_on,
        "click_enabled": click_enabled,
        "hamyon_enabled": hamyon_on,
        "payments_available": enabled or click_enabled or hamyon_on,
        # Prices the Premium page shows (days -> so'm) and the launch promo.
        "premium_periods": {str(k): v for k, v in PREMIUM_PERIODS.items()},
        "women_free": await women_free_active(),
    }
    if out["p2p_enabled"]:
        out["card_number"] = cfg.get("card_number", "")
        out["card_holder"] = cfg.get("card_holder", "")
    return out


@router.post("/payments/manual-topup")
async def manual_topup(
    request: Request,
    amount: int = Body(..., embed=True),
    proof_url: str = Body(..., embed=True),
    uid: str = Depends(get_current_user_id),
):
    rate_limit_payment(request)
    cfg = await db.settings.find_one({"id": "topup_config"}) or {}
    if not cfg.get("p2p_enabled"):
        raise HTTPException(400, "p2p_disabled")
    if amount < 1000:
        raise HTTPException(400, "Minimum top-up is 1000")
    if not (proof_url or "").strip():
        raise HTTPException(400, "proof_required")
    # Cap open requests so a user can't flood the admin queue
    pending = await db.manual_topups.count_documents({"user_id": uid, "status": "pending"})
    if pending >= 3:
        raise HTTPException(429, "too_many_pending")
    doc = {
        "id": new_id(),
        "user_id": uid,
        "amount": amount,
        "proof_url": proof_url.strip(),
        "status": "pending",
        "created_at": iso(now_utc()),
        "decided_at": None,
        "rejection_reason": None,
    }
    await db.manual_topups.insert_one(doc)
    # Real-time admin review card in Telegram (receipt photo + inline
    # approve/reject) — the admin decides from the phone without opening
    # the panel, so the user isn't left waiting.
    from admin_bot import notify_admins_manual_topup
    asyncio.create_task(notify_admins_manual_topup({k: v for k, v in doc.items() if k != "_id"}))
    return {"ok": True, "id": doc["id"]}


@router.get("/payments/manual-topup/mine")
async def my_manual_topups(uid: str = Depends(get_current_user_id)):
    rows = await db.manual_topups.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(20)
    return rows


async def decide_manual_topup(tid: str, approve: bool, reason: str = "", decided_by: str = "admin"):
    """Shared approve/reject for a P2P top-up — used by both the admin panel
    endpoint and the admin's Telegram inline buttons, so the two paths can
    never drift. Returns the request doc, or None if it was already decided
    (the atomic pending->decided flip makes double-taps harmless)."""
    res = await db.manual_topups.find_one_and_update(
        {"id": tid, "status": "pending"},
        {"$set": {
            "status": "approved" if approve else "rejected",
            "decided_at": iso(now_utc()),
            "decided_by": decided_by,
            "rejection_reason": (reason or "").strip() if not approve else None,
        }},
    )
    if not res:
        return None
    if approve:
        await db.users.update_one({"id": res["user_id"]}, {"$inc": {"balance": res["amount"]}})
        await db.payments.insert_one({
            "id": new_id(),
            "user_id": res["user_id"],
            "purpose": "balance_topup",
            "amount": res["amount"],
            "balance_used": 0,
            "click_amount": 0,
            "status": "paid",
            "method": "manual_p2p",
            "manual_topup_id": tid,
            "created_at": iso(now_utc()),
            "updated_at": iso(now_utc()),
        })
        await push_notif(res["user_id"], "balance", f"✅ To'lovingiz tasdiqlandi — balansingizga {res['amount']:,} so'm tushdi")
    else:
        await push_notif(res["user_id"], "balance", f"❌ Balans to'ldirish rad etildi: {(reason or 'sabab ko`rsatilmagan')}")
    return res


@router.get("/payments/mine")
async def my_payments(uid: str = Depends(get_current_user_id)):
    rows = await db.payments.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    
    # Expire pending payments older than 10 minutes. Hamyon closes its own
    # payments after 5 minutes and tells us (complete callback), so its rows
    # get a much later safety net here.
    ten_minutes_ago = now_utc() - timedelta(minutes=10)
    hamyon_cutoff = now_utc() - timedelta(minutes=30)
    for row in rows:
        is_hamyon = row.get("method") == "hamyon"
        cutoff = hamyon_cutoff if is_hamyon else ten_minutes_ago
        open_statuses = list(HAMYON_OPEN) if is_hamyon else ["pending"]
        if row.get("status") in open_statuses and parse_dt(row.get("created_at", now_utc())) < cutoff:
            row["status"] = "expired"
            res = await db.payments.update_one(
                {"id": row["id"], "status": {"$in": open_statuses}},
                {"$set": {"status": "expired", "updated_at": iso(now_utc()), "balance_refunded": row.get("balance_used", 0) > 0}}
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
    # BUG FIX: this read "referral_code" - a field that never exists in the
    # schema (it's only ever an incoming request field name elsewhere, never
    # persisted). The real field is "referral_id" (set at signup), with
    # "referral_username" as the vanity override a user can set via
    # /referral/username/set. Reading the wrong field meant this endpoint
    # silently ignored any custom username the user had set and rewrote a
    # separate, unused "referral_code" field on every single call.
    referral_id = me_doc.get("referral_id")
    if not referral_id:
        referral_id = uid[:8]
        await db.users.update_one({"id": uid}, {"$set": {"referral_id": referral_id}})
    code = me_doc.get("referral_username") or referral_id
    link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={code}"

    # A referred user's `referred_by` can hold either the inviter's raw
    # referral_id or their vanity username depending on which attribution
    # path recorded it (deep-link start vs. manual "who invited you" entry
    # during onboarding) - match both so a vanity username doesn't silently
    # undercount referrals made before it was set.
    match_codes = list({c for c in (referral_id, me_doc.get("referral_username")) if c})
    count = await db.users.count_documents({"referred_by": {"$in": match_codes}})

    # Count paid referrals (users who have made at least one successful payment)
    # Friends who have paid at least once (the current plan alone undercounts:
    # an expired plan reads "free" again).
    paid_referrals = await db.users.count_documents({
        "referred_by": {"$in": match_codes},
        "first_paid_at": {"$exists": True},
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
        "referral_earnings_withdrawable": me_doc.get("referral_earnings_withdrawable", 0),
        "referral_earnings_paid_out": me_doc.get("referral_earnings_paid_out", 0),
        # Sum of "credited" signup_free bonuses - a separate, non-withdrawable
        # internal-balance reward for free-tier referrals (see auth_r.py's
        # /profile/onboard), previously invisible: it was silently folded
        # into referral_earnings_pending with no distinct label anywhere.
        "signup_bonus_total": sum(
            int(e.get("amount") or 0)
            for e in me_doc.get("referral_earnings", [])
            if e.get("type") == "signup_free" and e.get("status") == "credited"
        ),
        "monthly_count": monthly_count,
        "monthly_tier": tier,
        "tier_cap": tier_cap,
        "next_tier_threshold": next_tier_threshold,
    }
