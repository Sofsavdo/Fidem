"""Admin endpoints."""
from __future__ import annotations

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
    total = await db.users.count_documents({})
    males = await db.users.count_documents({"gender": "male"})
    females = await db.users.count_documents({"gender": "female"})
    onboarded = await db.users.count_documents({"onboarded": True})
    premium = await db.users.count_documents({"plan": "premium"})
    vip = await db.users.count_documents({"plan": "vip"})
    today_iso = iso(datetime.now(timezone.utc) - timedelta(days=1))
    week_iso = iso(datetime.now(timezone.utc) - timedelta(days=7))
    month_iso = iso(datetime.now(timezone.utc) - timedelta(days=30))
    dau = await db.users.count_documents({"last_active": {"$gte": today_iso}})
    wau = await db.users.count_documents({"last_active": {"$gte": week_iso}})
    mau = await db.users.count_documents({"last_active": {"$gte": month_iso}})
    rev_agg = await db.payments.aggregate([
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    revenue = rev_agg[0]["total"] if rev_agg else 0
    
    # Revenue by period
    rev_today = await db.payments.aggregate([
        {"$match": {"status": "success", "created_at": {"$gte": today_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    rev_week = await db.payments.aggregate([
        {"$match": {"status": "success", "created_at": {"$gte": week_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    rev_month = await db.payments.aggregate([
        {"$match": {"status": "success", "created_at": {"$gte": month_iso}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    
    # Revenue by purpose
    rev_by_purpose = await db.payments.aggregate([
        {"$match": {"status": "success"}},
        {"$group": {"_id": "$purpose", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]).to_list(20)
    
    # Top regions
    top_regions = await db.users.aggregate([
        {"$match": {"onboarded": True, "region": {"$ne": None}}},
        {"$group": {"_id": "$region", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]).to_list(10)
    
    # Messages stats
    total_messages = await db.messages.count_documents({})
    messages_today = await db.messages.count_documents({"created_at": {"$gte": today_iso}})
    
    # Referral stats
    total_referrals = await db.users.count_documents({"referred_by": {"$ne": None}})
    
    # User quality metrics
    avg_completeness = await db.users.aggregate([
        {"$match": {"onboarded": True}},
        {"$group": {"_id": None, "avg": {"$avg": "$completeness"}}}
    ]).to_list(1)
    avg_completion = avg_completeness[0]["avg"] if avg_completeness else 0
    
    # Retention: users who onboarded in last 30 days and still active
    from core import parse_dt
    new_users = await db.users.find({"created_at": {"$gte": month_iso}}, {"_id": 0, "id": 1, "last_active": 1}).to_list(1000)
    retained = sum(1 for u in new_users if u.get("last_active") and parse_dt(u["last_active"]) >= datetime.fromisoformat(today_iso.replace('Z', '+00:00')))
    retention_rate = (retained / len(new_users) * 100) if new_users else 0

    # Usage: average messages per active user
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
        "pending_payments": await db.payments.count_documents({"status": "pending"}),
        "pending_verifications": await db.verifications.count_documents({"status": "pending"}),
        "open_reports": await db.reports.count_documents({"status": "open"}),
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
async def admin_list_users(q: str = "", page: int = 1, limit: int = 20, gender: str = "", region: str = "", age_min: int = None, age_max: int = None, marital_status: str = "", _: str = Depends(get_current_admin)):
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
        age_query = {}
        if age_min is not None:
            age_query["$gte"] = age_min
        if age_max is not None:
            age_query["$lte"] = age_max
        if age_query:
            query["age"] = age_query
    skip = (page - 1) * limit
    total = await db.users.count_documents(query)
    rows = await db.users.find(query, {"_id": 0, "password_hash": 0}).skip(skip).limit(limit).to_list(limit)
    return {"users": [user_public(u) for u in rows], "total": total, "page": page, "limit": limit}


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
    q: dict = {}
    if status:
        q["status"] = status
    skip = (page - 1) * limit
    total = await db.payments.count_documents(q)
    rows = await db.payments.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return {"payments": rows, "total": total, "page": page, "limit": limit}


@router.get("/verifications")
async def admin_verifications(status: str = "pending", page: int = 1, limit: int = 20, _: str = Depends(get_current_admin)):
    q = {} if status == "all" else {"status": status}
    skip = (page - 1) * limit
    total = await db.verifications.count_documents(q)
    rows = await db.verifications.find(q, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    out = []
    for r in rows:
        u = await db.users.find_one({"id": r["user_id"]}, {"_id": 0, "name": 1, "email": 1, "photo_url": 1, "id": 1, "verified_financial": 1, "verified_identity": 1, "verified_selfie": 1})
        r["user"] = u or {}
        out.append(r)
    return {"verifications": out, "total": total, "page": page, "limit": limit}


@router.post("/verifications/{vid}/decide")
async def admin_decide_verif(vid: str, approve: bool = Body(..., embed=True), reason: str = Body("", embed=True), _: str = Depends(get_current_admin)):
    v = await db.verifications.find_one({"id": vid})
    if not v:
        raise HTTPException(404, "Not found")
    await db.verifications.update_one(
        {"id": vid},
        {"$set": {
            "status": "approved" if approve else "rejected",
            "decided_at": iso(now_utc()),
            "rejection_reason": reason if not approve else None,
        }},
    )
    if approve:
        field = {"identity": "verified_identity", "selfie": "verified_selfie", "financial": "verified_financial"}.get(v.get("kind"), None)
        if field:
            await db.users.update_one({"id": v["user_id"]}, {"$set": {field: True}})
            # Auto-grant financial badge
            if v.get("kind") == "financial":
                await db.users.update_one(
                    {"id": v["user_id"]},
                    {"$addToSet": {"badges": "b_financial"}},
                )
        await push_notif(v["user_id"], "verified", f"✅ Verification tasdiqlandi: {v.get('kind')}")
    else:
        reason_txt = reason or "sabab ko'rsatilmagan"
        await push_notif(v["user_id"], "verified", f"❌ Verification rad etildi: {reason_txt}")
    return {"ok": True}


@router.get("/reports")
async def admin_reports(_: str = Depends(get_current_admin)):
    rows = await db.reports.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return rows


@router.post("/notification/broadcast")
async def admin_broadcast(text: str = Body(..., embed=True), dry_run: bool = Body(False, embed=True), _: str = Depends(get_current_admin)):
    users = await db.users.find({"onboarded": True, "blocked": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(10000)
    if dry_run:
        return {"would_send": len(users), "dry_run": True}
    sent, skipped = 0, 0
    for u in users:
        ok = await push_notif(u["id"], "marketing", text, marketing=True)
        if ok:
            sent += 1
        else:
            skipped += 1
    return {"sent": sent, "skipped_daily_cap": skipped}


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
    out = []
    for msg in rows:
        from_user = await db.users.find_one({"id": msg.get("from_user_id")}, {"_id": 0, "name": 1, "photo_url": 1})
        to_user = await db.users.find_one({"id": msg.get("to_user_id")}, {"_id": 0, "name": 1, "photo_url": 1})
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
    return {"users": [user_public(u) for u in rows], "total": total, "page": page, "limit": limit}


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
