"""Admin endpoints."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_admin
from core import db, iso, now_utc, push_notif, user_public
from models import AdminUpdateUserRequest
from routers.payments_r import process_completed_payment

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/stats")
async def admin_stats(_: str = Depends(get_current_admin)):
    """Dashboard metrics. Everything runs CONCURRENTLY via asyncio.gather -
    this endpoint used to fire ~22 sequential DB roundtrips, which made the
    whole admin panel feel frozen on every open."""
    today_iso = iso(datetime.now(timezone.utc) - timedelta(days=1))
    week_iso = iso(datetime.now(timezone.utc) - timedelta(days=7))
    month_iso = iso(datetime.now(timezone.utc) - timedelta(days=30))

    def _rev(match):
        return db.payments.aggregate([
            {"$match": match},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]).to_list(1)

    (
        total, males, females, onboarded, premium, vip,
        dau, wau, mau,
        rev_agg, rev_today, rev_week, rev_month, rev_by_purpose,
        top_regions, total_messages, messages_today, total_referrals,
        avg_completeness, new_users,
        pending_payments, pending_verifications, open_reports,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"gender": "male"}),
        db.users.count_documents({"gender": "female"}),
        db.users.count_documents({"onboarded": True}),
        db.users.count_documents({"plan": "premium"}),
        db.users.count_documents({"plan": "vip"}),
        db.users.count_documents({"last_active": {"$gte": today_iso}}),
        db.users.count_documents({"last_active": {"$gte": week_iso}}),
        db.users.count_documents({"last_active": {"$gte": month_iso}}),
        _rev({"status": "success"}),
        _rev({"status": "success", "created_at": {"$gte": today_iso}}),
        _rev({"status": "success", "created_at": {"$gte": week_iso}}),
        _rev({"status": "success", "created_at": {"$gte": month_iso}}),
        db.payments.aggregate([
            {"$match": {"status": "success"}},
            {"$group": {"_id": "$purpose", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
            {"$sort": {"total": -1}},
        ]).to_list(20),
        db.users.aggregate([
            {"$match": {"onboarded": True, "region": {"$ne": None}}},
            {"$group": {"_id": "$region", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10},
        ]).to_list(10),
        db.messages.count_documents({}),
        db.messages.count_documents({"created_at": {"$gte": today_iso}}),
        db.users.count_documents({"referred_by": {"$ne": None}}),
        db.users.aggregate([
            {"$match": {"onboarded": True}},
            {"$group": {"_id": None, "avg": {"$avg": "$completeness"}}},
        ]).to_list(1),
        db.users.find({"created_at": {"$gte": month_iso}}, {"_id": 0, "id": 1, "last_active": 1}).to_list(1000),
        db.payments.count_documents({"status": "pending"}),
        db.verifications.count_documents({"status": "pending"}),
        db.reports.count_documents({"status": "open"}),
    )

    revenue = rev_agg[0]["total"] if rev_agg else 0
    avg_completion = avg_completeness[0]["avg"] if avg_completeness else 0

    from core import parse_dt
    retained = sum(1 for u in new_users if u.get("last_active") and parse_dt(u["last_active"]) >= datetime.fromisoformat(today_iso.replace('Z', '+00:00')))
    retention_rate = (retained / len(new_users) * 100) if new_users else 0
    avg_messages_per_user = messages_today / dau if dau > 0 else 0

    return {
        "total_users": total, "males": males, "females": females,
        "onboarded": onboarded, "premium": premium, "vip": vip,
        "dau": dau, "wau": wau, "mau": mau,
        "revenue": {
            "total": revenue,
            "today": rev_today[0]["total"] if rev_today else 0,
            "week": rev_week[0]["total"] if rev_week else 0,
            "month": rev_month[0]["total"] if rev_month else 0,
            "by_purpose": rev_by_purpose,
        },
        "conversion_premium": round((premium + vip) / total * 100, 2) if total else 0,
        "pending_payments": pending_payments,
        "pending_verifications": pending_verifications,
        "open_reports": open_reports,
        "top_regions": top_regions,
        "messages": {
            "total": total_messages,
            "today": messages_today,
        },
        "referrals": {
            "total": total_referrals,
        },
        "quality": {
            "avg_completion": round(avg_completion, 1),
            "retention_rate": round(retention_rate, 1),
            "avg_messages_per_user": round(avg_messages_per_user, 1),
        },
    }


@router.get("/users")
async def admin_list_users(
    q: str = "",
    page: int = 1,
    limit: int = 20,
    gender: str = "",
    region: str = "",
    age_min: int = None,
    age_max: int = None,
    marital_status: str = "",
    plan: str = "",
    joined_within_days: int = None,
    active_within_days: int = None,
    sort: str = "",
    _: str = Depends(get_current_admin),
):
    query = {}
    if q:
        query["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"telegram_username": {"$regex": q, "$options": "i"}},
        ]
    if gender:
        query["gender"] = gender
    if region:
        query["region"] = {"$regex": region, "$options": "i"}
    if marital_status:
        query["marital_status"] = marital_status
    if age_min is not None or age_max is not None:
        # users.age is not a stored field (age is derived from birth_date at
        # read time, see services.age_from_birth) - translate the bounds into
        # a birth_date range instead of filtering on a field that never exists.
        today = now_utc().date()
        bd_query = {}
        if age_min is not None:
            bd_query["$lte"] = today.replace(year=today.year - age_min).isoformat()
        if age_max is not None:
            bd_query["$gt"] = today.replace(year=today.year - age_max - 1).isoformat()
        if bd_query:
            query["birth_date"] = bd_query
    if plan:
        query["plan"] = {"$in": ["standard", "premium", "vip"]} if plan == "paid" else plan
    if joined_within_days is not None:
        query["created_at"] = {"$gte": iso(now_utc() - timedelta(days=joined_within_days))}
    if active_within_days is not None:
        query["last_active"] = {"$gte": iso(now_utc() - timedelta(days=active_within_days))}

    # "new" = signup date, "active" = most recently seen. Default keeps the
    # old behavior (insertion order) so existing screens don't reshuffle.
    sort_spec = {"new": [("created_at", -1)], "active": [("last_active", -1)]}.get(sort)

    skip = (page - 1) * limit
    total = await db.users.count_documents(query)
    cursor = db.users.find(query, {"_id": 0, "password_hash": 0})
    if sort_spec:
        cursor = cursor.sort(sort_spec)
    rows = await cursor.skip(skip).limit(limit).to_list(limit)

    out = []
    for u in rows:
        pub = user_public(u, include_private=True)
        # How long they've been on the platform - the "necha kundan beri
        # ilovada" column the admin asked for.
        try:
            from core import parse_dt
            created = parse_dt(u.get("created_at"))
            pub["days_in_app"] = max(0, (now_utc() - created).days) if created else None
        except Exception:
            pub["days_in_app"] = None
        out.append(pub)
    return {"users": out, "total": total, "page": page, "limit": limit}


@router.patch("/users/{target_id}")
async def admin_update_user(target_id: str, req: AdminUpdateUserRequest, _: str = Depends(get_current_admin)):
    update = {k: v for k, v in req.model_dump().items() if v is not None and k != "add_balance"}
    ops: dict = {}
    if update:
        ops["$set"] = update
    if req.add_balance:
        ops["$inc"] = {"balance": req.add_balance}
    if not ops:
        return {"ok": True}
    await db.users.update_one({"id": target_id}, ops)
    return {"ok": True}


@router.get("/payments")
async def admin_payments(status: Optional[str] = None, page: int = 1, limit: int = 20, _: str = Depends(get_current_admin)):
    """Payments feed for the admin panel.

    status: "successful" (paid via balance + success via CLICK - the default
    view), "other" (pending/expired/failed, collapsed by default in the UI),
    a literal status, or empty for everything. Every row carries the paying
    user's name so the admin can tell WHO paid at a glance.
    """
    q: dict = {}
    if status == "successful":
        q["status"] = {"$in": ["success", "paid"]}
    elif status == "other":
        q["status"] = {"$nin": ["success", "paid"]}
    elif status:
        q["status"] = status
    skip = (page - 1) * limit
    total = await db.payments.count_documents(q)
    rows = await db.payments.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)

    user_ids = list({r.get("user_id") for r in rows if r.get("user_id")})
    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "id": 1, "name": 1, "telegram_username": 1, "plan": 1},
    ).to_list(len(user_ids)) if user_ids else []
    by_id = {u["id"]: u for u in users}
    for r in rows:
        u = by_id.get(r.get("user_id"), {})
        r["user_name"] = u.get("name", "")
        r["user_telegram"] = u.get("telegram_username", "")
        r["user_plan"] = u.get("plan", "")
    return {"payments": rows, "total": total, "page": page, "limit": limit}


# ---------- Referral tracking ----------
@router.get("/referrers")
async def admin_referrers(limit: int = 100, _: str = Depends(get_current_admin)):
    """Who is actually distributing referral links: every user that at least
    one other user signed up under, with invited/paid counts."""
    pipeline = [
        {"$match": {"referred_by": {"$nin": [None, ""]}}},
        {"$group": {
            "_id": "$referred_by",
            "invited": {"$sum": 1},
            "paid": {"$sum": {"$cond": [{"$in": ["$plan", ["standard", "premium", "vip"]]}, 1, 0]}},
            "last_signup": {"$max": "$created_at"},
        }},
        {"$sort": {"invited": -1}},
        {"$limit": max(1, min(limit, 500))},
    ]
    groups = await db.users.aggregate(pipeline).to_list(500)

    # referred_by stores either the inviter's referral_id or their referral
    # username - resolve both in one query.
    codes = [g["_id"] for g in groups]
    lowers = [str(c).lower() for c in codes]
    refs = await db.users.find(
        {"$or": [{"referral_id": {"$in": codes}}, {"referral_username_lower": {"$in": lowers}}]},
        {"_id": 0, "id": 1, "name": 1, "telegram_username": 1, "plan": 1, "referral_id": 1,
         "referral_username_lower": 1, "referral_earnings_withdrawable": 1, "referral_earnings_pending": 1},
    ).to_list(1000)
    by_code: dict = {}
    for u in refs:
        if u.get("referral_id"):
            by_code[u["referral_id"]] = u
        if u.get("referral_username_lower"):
            by_code[u["referral_username_lower"]] = u

    out = []
    for g in groups:
        u = by_code.get(g["_id"]) or by_code.get(str(g["_id"]).lower())
        out.append({
            "code": g["_id"],
            "invited": g["invited"],
            "paid": g["paid"],
            "last_signup": g.get("last_signup"),
            "referrer": {
                "id": u.get("id") if u else None,
                "name": (u or {}).get("name", "(topilmadi)"),
                "telegram_username": (u or {}).get("telegram_username", ""),
                "plan": (u or {}).get("plan", ""),
                "earnings_withdrawable": (u or {}).get("referral_earnings_withdrawable", 0),
                "earnings_pending": (u or {}).get("referral_earnings_pending", 0),
            },
        })
    return out


@router.get("/referrers/{user_id}")
async def admin_referrer_detail(user_id: str, _: str = Depends(get_current_admin)):
    """One referrer's full picture: exactly who they invited, when, and
    whether each invitee has paid (upgraded off free) or not."""
    ref = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not ref:
        raise HTTPException(404, "User not found")
    codes = [c for c in [ref.get("referral_id"), ref.get("referral_username_lower"), ref.get("referral_username")] if c]
    invited = await db.users.find(
        {"referred_by": {"$in": codes}},
        {"_id": 0, "id": 1, "name": 1, "gender": 1, "region": 1, "plan": 1,
         "created_at": 1, "last_active": 1, "onboarded": 1, "completeness": 1},
    ).sort("created_at", -1).to_list(1000)
    for u in invited:
        u["is_paid"] = u.get("plan", "free") in ("standard", "premium", "vip")
    return {
        "referrer": user_public(ref, include_private=True),
        "earnings_withdrawable": ref.get("referral_earnings_withdrawable", 0),
        "earnings_pending": ref.get("referral_earnings_pending", 0),
        "invited_total": len(invited),
        "invited_paid": sum(1 for u in invited if u["is_paid"]),
        "invited": invited,
    }


@router.get("/verifications")
async def admin_verifications(status: str = "pending", page: int = 1, limit: int = 20, _: str = Depends(get_current_admin)):
    q = {} if status == "all" else {"status": status}
    skip = (page - 1) * limit
    total = await db.verifications.count_documents(q)
    rows = await db.verifications.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    # One batched lookup instead of a query per row.
    user_ids = list({r["user_id"] for r in rows})
    users = await db.users.find(
        {"id": {"$in": user_ids}},
        {"_id": 0, "name": 1, "email": 1, "photo_url": 1, "id": 1, "verified_financial": 1, "verified_identity": 1, "verified_selfie": 1},
    ).to_list(len(user_ids)) if user_ids else []
    by_id = {u["id"]: u for u in users}
    for r in rows:
        r["user"] = by_id.get(r["user_id"], {})
    return {"verifications": rows, "total": total, "page": page, "limit": limit}


@router.post("/verifications/{vid}/decide")
async def admin_decide_verif(vid: str, approve: bool = Body(..., embed=True), reason: str = Body("", embed=True), _: str = Depends(get_current_admin)):
    # Same side-effects as the AI auto-reviewer (single shared helper).
    from routers.payments_r import apply_verification_decision
    v = await db.verifications.find_one({"id": vid})
    if not v:
        raise HTTPException(404, "Not found")
    ok = await apply_verification_decision(vid, approve, reason=reason, decided_by="admin")
    if not ok:
        raise HTTPException(409, "Already decided")
    return {"ok": True}


@router.get("/reports")
async def admin_reports(_: str = Depends(get_current_admin)):
    rows = await db.reports.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return rows


async def _run_broadcast(user_ids: list[str], text: str) -> None:
    sent, skipped = 0, 0
    for uid in user_ids:
        ok = await push_notif(uid, "marketing", text, marketing=True)
        if ok:
            sent += 1
        else:
            skipped += 1
    log.info(f"broadcast finished: sent={sent} skipped_daily_cap={skipped} total={len(user_ids)}")


@router.post("/notification/broadcast")
async def admin_broadcast(text: str = Body(..., embed=True), dry_run: bool = Body(False, embed=True), _: str = Depends(get_current_admin)):
    users = await db.users.find({"onboarded": True, "blocked": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(200000)
    if dry_run:
        return {"would_send": len(users), "dry_run": True}
    # One push_notif per user is a real DB round trip each - at 10K-1M users
    # that loop can run for minutes. Running it inline would hold the admin's
    # HTTP request open (and the connection pool slot) until every send
    # finishes, freezing the admin panel exactly like the /admin/stats
    # sequential-query issue this audit already fixed. Fire it in the
    # background and let the admin keep working.
    asyncio.create_task(_run_broadcast([u["id"] for u in users], text))
    return {"queued": len(users), "dry_run": False}


@router.get("/referrals")
async def admin_referrals(type: Optional[str] = None, limit: int = 200, _: str = Depends(get_current_admin)):
    """Get all referral earnings with optional type filter."""
    q = {}
    if type:
        q["type"] = type
    rows = await db.users.aggregate([
        {"$unwind": "$referral_earnings"},
        {"$match": q if q else {}},
        {"$sort": {"referral_earnings.created_at": -1}},
        {"$limit": limit},
        {"$project": {
            "_id": 0,
            "id": "$referral_earnings.id",
            "user_id": "$id",
            "referred_user_id": "$referral_earnings.referred_user_id",
            "type": "$referral_earnings.type",
            "amount": "$referral_earnings.amount",
            "status": "$referral_earnings.status",
            "created_at": "$referral_earnings.created_at",
            "level": "$referral_earnings.level",
        }}
    ]).to_list(limit)
    return rows


@router.get("/messages")
async def admin_messages(q: str = "", user_id: str = "", page: int = 1, limit: int = 20, _: str = Depends(get_current_admin)):
    """Get all messages with optional search, user filter, and pagination."""
    query = {}
    if q:
        query["text"] = {"$regex": q, "$options": "i"}
    if user_id:
        query["$or"] = [
            {"from_user_id": user_id},
            {"to_user_id": user_id}
        ]
    skip = (page - 1) * limit
    total = await db.messages.count_documents(query)
    rows = await db.messages.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    
    # Add user info to each message
    user_ids = {msg.get("from_user_id") for msg in rows} | {msg.get("to_user_id") for msg in rows}
    user_ids.discard(None)
    users = await db.users.find(
        {"id": {"$in": list(user_ids)}}, {"_id": 0, "name": 1, "photo_url": 1, "id": 1}
    ).to_list(len(user_ids))
    users_by_id = {u["id"]: u for u in users}

    out = []
    for msg in rows:
        from_user = users_by_id.get(msg.get("from_user_id"))
        to_user = users_by_id.get(msg.get("to_user_id"))
        msg["from_user_name"] = from_user.get("name") if from_user else "Unknown"
        msg["from_user_photo"] = from_user.get("photo_url") if from_user else None
        msg["to_user_name"] = to_user.get("name") if to_user else "Unknown"
        msg["to_user_photo"] = to_user.get("photo_url") if to_user else None
        out.append(msg)

    return {"messages": out, "total": total, "page": page, "limit": limit}


@router.delete("/messages/{mid}")
async def admin_delete_message(mid: str, _: str = Depends(get_current_admin)):
    """Delete a message by ID."""
    result = await db.messages.delete_one({"id": mid})
    if result.deleted_count == 0:
        raise HTTPException(404, "Message not found")
    return {"ok": True}


@router.post("/payments/{pid}/block")
async def admin_block_payment(pid: str, _: str = Depends(get_current_admin)):
    """Block a payment from being processed."""
    result = await db.payments.update_one({"id": pid}, {"$set": {"blocked_by_admin": True}})
    if result.modified_count == 0:
        raise HTTPException(404, "Payment not found")
    return {"ok": True}


@router.post("/payments/{pid}/unblock")
async def admin_unblock_payment(pid: str, _: str = Depends(get_current_admin)):
    """Unblock a payment."""
    result = await db.payments.update_one({"id": pid}, {"$set": {"blocked_by_admin": False}})
    if result.modified_count == 0:
        raise HTTPException(404, "Payment not found")
    return {"ok": True}


@router.get("/fraud")
async def admin_fraud_detection(min_score: int = 50, page: int = 1, limit: int = 50, _: str = Depends(get_current_admin)):
    """Get users with high fraud scores."""
    skip = (page - 1) * limit
    total = await db.users.count_documents({"fraud_score": {"$gte": min_score}})
    rows = await db.users.find(
        {"fraud_score": {"$gte": min_score}},
        {"_id": 0, "password_hash": 0}
    ).sort("fraud_score", -1).skip(skip).limit(limit).to_list(limit)
    return {"users": [user_public(u, include_private=True) for u in rows], "total": total, "page": page, "limit": limit}


@router.post("/users/{uid}/mark-safe")
async def admin_mark_user_safe(uid: str, _: str = Depends(get_current_admin)):
    """Mark a user as safe (reset fraud score)."""
    result = await db.users.update_one(
        {"id": uid},
        {"$set": {"fraud_score": 0, "fraud_reasons": [], "flagged_as_bot": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(404, "User not found")
    return {"ok": True}


@router.get("/regions")
async def admin_regions(_: str = Depends(get_current_admin)):
    """Get list of all regions for filtering."""
    regions = await db.users.distinct("region", {"region": {"$ne": "", "$ne": None}})
    return {"regions": sorted(regions)}
