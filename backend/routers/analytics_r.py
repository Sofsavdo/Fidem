"""Product/business analytics for the admin panel: CEO Dashboard, growth
funnel, match/chat/premium engagement KPIs, and the revenue dashboard.

Every number here answers a specific question a dating-app operator asks
daily (acquisition, activation, engagement, revenue, retention) — the older
/admin/stats endpoint (still used by the Boshqaruv tab) mixed in numbers
that don't drive decisions (M/F ratio, top regions) with ones that do. This
module is additive; nothing here replaces /admin/stats.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends

from auth import get_current_admin
from core import db, iso, now_utc, parse_dt

router = APIRouter(prefix="/admin", tags=["admin-analytics"])


def _period_bounds():
    now = now_utc()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return {
        "now": now,
        "today": iso(today_start),
        "yesterday": iso(today_start - timedelta(days=1)),
        "week": iso(now - timedelta(days=7)),
        "month": iso(now - timedelta(days=30)),
        "month_start": iso(today_start.replace(day=1)),
    }


# ---------- Matches: a "match" is a save that COMPLETES a mutual pair. The
# saved collection has one row per (owner, target) with a single "at"
# (last-saved) timestamp, so a match is detected by the row whose reciprocal
# already existed at or before it — that row's "at" IS the match's formation
# time, and there is exactly one such row per matched pair (no double count).
# Computed in Python over the full collection (same style as
# candidates_r.saved_summary's latest_at dict) rather than an aggregation
# self-join — simpler to reason about and fine at this scale (bounded by
# total likes, not messages).
async def _matched_rows(since_iso: Optional[str] = None, user_id: Optional[str] = None) -> list:
    q: dict = {}
    if user_id:
        q["$or"] = [{"owner_id": user_id}, {"target_id": user_id}]
    rows = await db.saved.find(q, {"_id": 0, "owner_id": 1, "target_id": 1, "at": 1}).to_list(200000)
    by_pair = {(r["owner_id"], r["target_id"]): r["at"] for r in rows}
    completed = []
    for r in rows:
        recip_at = by_pair.get((r["target_id"], r["owner_id"]))
        if recip_at is not None and recip_at <= r["at"]:
            if since_iso is None or r["at"] >= since_iso:
                completed.append(r)
    return completed


async def _count_matches(since_iso: Optional[str] = None) -> int:
    return len(await _matched_rows(since_iso))


async def _matched_user_ids() -> set:
    """Every user who is on at least one side of at least one match."""
    ids = set()
    for r in await _matched_rows(None):
        ids.add(r["owner_id"])
        ids.add(r["target_id"])
    return ids


# ---------- Real cash in: CLICK success (click_amount, not the full order —
# the balance-funded portion of a hybrid order was already counted when that
# balance was topped up) plus approved manual P2P transfers. A balance-only
# purchase moves already-counted money between "wallet" and "spent on X" and
# must NOT be counted again here, or every feature's "revenue" would double
# real cash in.
async def _real_revenue(since_iso: Optional[str] = None) -> int:
    match: dict = {"status": "success"}
    match_p2p: dict = {"status": "paid", "method": "manual_p2p"}
    if since_iso:
        match["created_at"] = {"$gte": since_iso}
        match_p2p["created_at"] = {"$gte": since_iso}
    click_agg, p2p_agg = await asyncio.gather(
        db.payments.aggregate([{"$match": match}, {"$group": {"_id": None, "t": {"$sum": "$click_amount"}}}]).to_list(1),
        db.payments.aggregate([{"$match": match_p2p}, {"$group": {"_id": None, "t": {"$sum": "$amount"}}}]).to_list(1),
    )
    return (click_agg[0]["t"] if click_agg else 0) + (p2p_agg[0]["t"] if p2p_agg else 0)


@router.get("/ceo")
async def ceo_dashboard(_: str = Depends(get_current_admin)):
    """The 4-question dashboard: how many people came, how many matched, how
    many chatted, how much money came in — today, at a glance."""
    p = _period_bounds()

    (
        total_users, new_today, new_week, new_month,
        dau, wau, mau,
        rev_today, rev_week, rev_month, rev_total,
        matches_today, matches_week, matches_month,
        new_chats_today, messages_today,
        paying_users, active_plan_counts,
        cohort_yesterday,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"created_at": {"$gte": p["today"]}}),
        db.users.count_documents({"created_at": {"$gte": p["week"]}}),
        db.users.count_documents({"created_at": {"$gte": p["month"]}}),
        db.users.count_documents({"last_active": {"$gte": p["today"]}}),
        db.users.count_documents({"last_active": {"$gte": p["week"]}}),
        db.users.count_documents({"last_active": {"$gte": p["month"]}}),
        _real_revenue(p["today"]),
        _real_revenue(p["week"]),
        _real_revenue(p["month"]),
        _real_revenue(None),
        _count_matches(p["today"]),
        _count_matches(p["week"]),
        _count_matches(p["month"]),
        db.messages.aggregate([
            {"$group": {"_id": "$chat_id", "first_at": {"$min": "$created_at"}}},
            {"$match": {"first_at": {"$gte": p["today"]}}},
            {"$count": "n"},
        ]).to_list(1),
        db.messages.count_documents({"created_at": {"$gte": p["today"]}}),
        db.users.count_documents({"lifetime_contribution": {"$gt": 0}}),
        db.users.aggregate([
            {"$match": {"plan": {"$in": ["standard", "premium", "vip"]}, "plan_until": {"$gt": iso(p["now"])}}},
            {"$group": {"_id": "$plan", "n": {"$sum": 1}}},
        ]).to_list(10),
        # D1 retention: users who signed up "yesterday" (24-48h ago) and were
        # active again after their signup day — the earliest meaningful
        # retention signal at low volume (D7/D30 need more history to be
        # anything but noise with ~100 users).
        db.users.find(
            {"created_at": {"$gte": iso(p["now"] - timedelta(days=2)), "$lt": p["yesterday"]}},
            {"_id": 0, "id": 1, "created_at": 1, "last_active": 1},
        ).to_list(2000),
    )

    plan_price = {"standard": 34900, "premium": 79000, "vip": 199000}
    mrr = sum(plan_price.get(r["_id"], 0) * r["n"] for r in active_plan_counts)

    d1_eligible = len(cohort_yesterday)
    d1_retained = 0
    for u in cohort_yesterday:
        try:
            if u.get("last_active") and parse_dt(u["last_active"]) > parse_dt(u["created_at"]) + timedelta(hours=20):
                d1_retained += 1
        except Exception:
            pass
    d1_retention_pct = round(d1_retained / d1_eligible * 100, 1) if d1_eligible else None

    new_chats = new_chats_today[0]["n"] if new_chats_today else 0
    match_rate_today = round(matches_today / new_today * 100, 1) if new_today else None
    chat_rate_today = round(new_chats / matches_today * 100, 1) if matches_today else None
    premium_conversion = round(paying_users / total_users * 100, 2) if total_users else 0
    arpu = round(rev_total / total_users) if total_users else 0
    arppu = round(rev_total / paying_users) if paying_users else 0

    return {
        "revenue": {"today": rev_today, "week": rev_week, "month": rev_month, "total": rev_total},
        "users": {"total": total_users, "new_today": new_today, "new_week": new_week, "new_month": new_month},
        "active": {"dau": dau, "wau": wau, "mau": mau},
        "matches": {"today": matches_today, "week": matches_week, "month": matches_month, "match_rate_today_pct": match_rate_today},
        "chats": {"new_today": new_chats, "chat_rate_today_pct": chat_rate_today, "messages_today": messages_today},
        "monetization": {
            "premium_conversion_pct": premium_conversion,
            "paying_users": paying_users,
            "arpu": arpu,
            "arppu": arppu,
            "mrr": mrr,
        },
        "retention": {
            "d1_pct": d1_retention_pct,
            "d1_cohort_size": d1_eligible,
            "note": "D7/D30 saqlanish 100+ foydalanuvchida shovqinli — kohorta kattalashgach qo'shiladi",
        },
    }


@router.get("/growth/funnel")
async def growth_funnel(_: str = Depends(get_current_admin)):
    """Telegram start -> registered -> onboarded -> first like -> first
    match -> first chat -> paying. Every step counted against the step
    before it, so the drop-off percentage is directly visible."""
    (
        bot_starts,
        registered,
        onboarded,
        first_like_ids,
        first_chat_agg,
        paying,
        matched_ids,
    ) = await asyncio.gather(
        db.bot_starts.count_documents({}),
        db.users.count_documents({}),
        db.users.count_documents({"onboarded": True}),
        db.saved.distinct("owner_id"),
        db.messages.distinct("from_user_id"),
        db.users.count_documents({"lifetime_contribution": {"$gt": 0}}),
        _matched_user_ids(),
    )

    steps = [
        {"key": "bot_start", "label": "Telegram /start", "count": bot_starts},
        {"key": "registered", "label": "Ro'yxatdan o'tish", "count": registered},
        {"key": "onboarded", "label": "Anketa to'ldirildi", "count": onboarded},
        {"key": "first_like", "label": "Birinchi like", "count": len(first_like_ids)},
        {"key": "first_match", "label": "Birinchi match", "count": len(matched_ids)},
        {"key": "first_chat", "label": "Birinchi xabar", "count": len(first_chat_agg)},
        {"key": "paying", "label": "To'lov qildi", "count": paying},
    ]
    prev = None
    for s in steps:
        s["pct_of_previous"] = round(s["count"] / prev * 100, 1) if prev else 100.0
        s["pct_of_top"] = round(s["count"] / steps[0]["count"] * 100, 1) if steps[0]["count"] else 0.0
        prev = s["count"] or None
    return {"steps": steps}


@router.get("/growth/engagement")
async def growth_engagement(_: str = Depends(get_current_admin)):
    """Like / match / chat / premium-funnel KPI cards."""
    p = _period_bounds()

    (
        likes_today, likes_week, likes_month, likes_total,
        matches_today, matches_week, matches_month,
        new_chats_today_agg, active_chats_week_agg, msgs_today, msgs_week,
        reply_rate_agg,
        total_matched_users,
        total_onboarded,
    ) = await asyncio.gather(
        db.saved.count_documents({"at": {"$gte": p["today"]}}),
        db.saved.count_documents({"at": {"$gte": p["week"]}}),
        db.saved.count_documents({"at": {"$gte": p["month"]}}),
        db.saved.count_documents({}),
        _count_matches(p["today"]),
        _count_matches(p["week"]),
        _count_matches(p["month"]),
        db.messages.aggregate([
            {"$group": {"_id": "$chat_id", "first_at": {"$min": "$created_at"}}},
            {"$match": {"first_at": {"$gte": p["today"]}}},
            {"$count": "n"},
        ]).to_list(1),
        db.messages.aggregate([
            {"$match": {"created_at": {"$gte": p["week"]}}},
            {"$group": {"_id": "$chat_id"}},
            {"$count": "n"},
        ]).to_list(1),
        db.messages.count_documents({"created_at": {"$gte": p["today"]}}),
        db.messages.count_documents({"created_at": {"$gte": p["week"]}}),
        db.messages.aggregate([
            {"$group": {"_id": "$chat_id", "senders": {"$addToSet": "$from_user_id"}, "n": {"$sum": 1}}},
            {"$group": {
                "_id": None,
                "chats": {"$sum": 1},
                "replied": {"$sum": {"$cond": [{"$gte": [{"$size": "$senders"}, 2]}, 1, 0]}},
                "total_msgs": {"$sum": "$n"},
            }},
        ]).to_list(1),
        _matched_user_ids(),
        db.users.count_documents({"onboarded": True}),
    )

    r = reply_rate_agg[0] if reply_rate_agg else {"chats": 0, "replied": 0, "total_msgs": 0}
    reply_rate_pct = round(r["replied"] / r["chats"] * 100, 1) if r["chats"] else None
    avg_msgs_per_chat = round(r["total_msgs"] / r["chats"], 1) if r["chats"] else 0
    avg_match_per_user = round(len(total_matched_users) / total_onboarded, 2) if total_onboarded else 0
    mutual_likes = matches_week  # a "mutual like" IS a match by definition

    return {
        "likes": {"today": likes_today, "week": likes_week, "month": likes_month, "total": likes_total, "mutual_this_week": mutual_likes},
        "matches": {"today": matches_today, "week": matches_week, "month": matches_month, "avg_per_user": avg_match_per_user},
        "chats": {
            "new_today": new_chats_today_agg[0]["n"] if new_chats_today_agg else 0,
            "active_this_week": active_chats_week_agg[0]["n"] if active_chats_week_agg else 0,
            "messages_today": msgs_today,
            "messages_week": msgs_week,
            "reply_rate_pct": reply_rate_pct,
            "avg_messages_per_chat": avg_msgs_per_chat,
        },
    }


@router.get("/revenue")
async def revenue_dashboard(_: str = Depends(get_current_admin)):
    """Real cash in (today/week/month/total + 30-day trend) plus a spend
    breakdown by feature — clearly two different questions, kept visually
    separate so the two are never confused."""
    p = _period_bounds()

    real_today, real_week, real_month, real_total, total_users, paying_users = await asyncio.gather(
        _real_revenue(p["today"]),
        _real_revenue(p["week"]),
        _real_revenue(p["month"]),
        _real_revenue(None),
        db.users.count_documents({}),
        db.users.count_documents({"lifetime_contribution": {"$gt": 0}}),
    )

    # Spend by feature: how balance actually gets used, whatever its source
    # (CLICK, P2P, or a prior top-up). Distinct from "real cash in" above.
    spend_by_purpose = await db.payments.aggregate([
        {"$match": {"status": {"$in": ["paid", "success"]}}},
        {"$group": {"_id": "$purpose", "total": {"$sum": "$amount"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
    ]).to_list(20)

    # 30-day daily trend of real cash in, for a sparkline.
    trend_rows = await db.payments.aggregate([
        {"$match": {"$or": [
            {"status": "success", "created_at": {"$gte": p["month"]}},
            {"status": "paid", "method": "manual_p2p", "created_at": {"$gte": p["month"]}},
        ]}},
        {"$project": {
            "day": {"$substrBytes": ["$created_at", 0, 10]},
            "cash": {"$cond": [{"$eq": ["$method", "manual_p2p"]}, "$amount", "$click_amount"]},
        }},
        {"$group": {"_id": "$day", "total": {"$sum": "$cash"}}},
        {"$sort": {"_id": 1}},
    ]).to_list(31)

    active_plan_counts = await db.users.aggregate([
        {"$match": {"plan": {"$in": ["standard", "premium", "vip"]}, "plan_until": {"$gt": iso(p["now"])}}},
        {"$group": {"_id": "$plan", "n": {"$sum": 1}}},
    ]).to_list(10)
    plan_price = {"standard": 34900, "premium": 79000, "vip": 199000}
    mrr = sum(plan_price.get(r["_id"], 0) * r["n"] for r in active_plan_counts)

    return {
        "real_revenue": {"today": real_today, "week": real_week, "month": real_month, "total": real_total},
        "trend_30d": [{"date": r["_id"], "total": r["total"]} for r in trend_rows],
        "spend_by_feature": spend_by_purpose,
        "kpi": {
            "arpu": round(real_total / total_users) if total_users else 0,
            "arppu": round(real_total / paying_users) if paying_users else 0,
            "mrr": mrr,
            "paying_users": paying_users,
            "total_users": total_users,
            "premium_conversion_pct": round(paying_users / total_users * 100, 2) if total_users else 0,
        },
        "ltv_note": "LTV ishonchli hisoblash uchun uzoqroq muddat (kohorta chayqovi) kerak — hozircha ARPPU'ni proksi sifatida ishlating.",
    }


@router.get("/concierge/analytics")
async def concierge_analytics(_: str = Depends(get_current_admin)):
    rows = await db.concierge_orders.aggregate([
        {"$group": {"_id": "$status", "n": {"$sum": 1}, "amount": {"$sum": "$amount"}}},
    ]).to_list(20)
    by_status = {r["_id"]: {"count": r["n"], "amount": r["amount"]} for r in rows}
    total_orders = sum(v["count"] for v in by_status.values())
    revenue = sum(v["amount"] for k, v in by_status.items() if k in ("in_progress", "active", "completed"))
    total_users = await db.users.count_documents({})
    return {
        "applications": total_orders,
        "awaiting_payment": by_status.get("awaiting_payment", {}).get("count", 0),
        "in_progress": by_status.get("in_progress", {}).get("count", 0) + by_status.get("active", {}).get("count", 0),
        "completed": by_status.get("completed", {}).get("count", 0),
        "expired": by_status.get("expired", {}).get("count", 0),
        "revenue_generated": revenue,
        "conversion_pct": round(total_orders / total_users * 100, 2) if total_users else 0,
    }


@router.get("/chat-moderation/analytics")
async def chat_moderation_analytics(_: str = Depends(get_current_admin)):
    p = _period_bounds()
    (most_active, most_reported, blocked_count, reports_open, reports_total) = await asyncio.gather(
        db.messages.aggregate([
            {"$match": {"created_at": {"$gte": p["week"]}}},
            {"$group": {"_id": "$from_user_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": 10},
        ]).to_list(10),
        db.reports.aggregate([
            {"$group": {"_id": "$target_id", "n": {"$sum": 1}}},
            {"$sort": {"n": -1}},
            {"$limit": 10},
        ]).to_list(10),
        db.blocks.count_documents({}),
        db.reports.count_documents({"status": "open"}),
        db.reports.count_documents({}),
    )
    ids = list({r["_id"] for r in most_active} | {r["_id"] for r in most_reported})
    users = await db.users.find({"id": {"$in": ids}}, {"_id": 0, "id": 1, "name": 1, "telegram_username": 1}).to_list(len(ids)) if ids else []
    umap = {u["id"]: u for u in users}
    for r in most_active:
        r["user"] = umap.get(r["_id"], {})
    for r in most_reported:
        r["user"] = umap.get(r["_id"], {})
    return {
        "most_active_users": most_active,
        "most_reported_users": most_reported,
        "blocked_relationships": blocked_count,
        "reports_open": reports_open,
        "reports_total": reports_total,
    }


@router.get("/audit-log")
async def audit_log(page: int = 1, limit: int = 50, admin_id: Optional[str] = None, action: Optional[str] = None, _: str = Depends(get_current_admin)):
    q: dict = {}
    if admin_id:
        q["admin_id"] = admin_id
    if action:
        q["action"] = action
    skip = (page - 1) * limit
    total = await db.admin_audit_log.count_documents(q)
    rows = await db.admin_audit_log.find(q, {"_id": 0}).sort("at", -1).skip(skip).limit(limit).to_list(limit)
    admin_ids = list({r["admin_id"] for r in rows if r.get("admin_id")})
    target_ids = list({r["target_id"] for r in rows if r.get("target_id")})
    admins = await db.users.find({"id": {"$in": admin_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(admin_ids)) if admin_ids else []
    targets = await db.users.find({"id": {"$in": target_ids}}, {"_id": 0, "id": 1, "name": 1}).to_list(len(target_ids)) if target_ids else []
    admin_map = {a["id"]: a["name"] for a in admins}
    target_map = {t["id"]: t["name"] for t in targets}
    for r in rows:
        r["admin_name"] = admin_map.get(r.get("admin_id"), r.get("admin_id"))
        r["target_name"] = target_map.get(r.get("target_id"), r.get("target_id"))
    return {"items": rows, "total": total, "page": page, "limit": limit}
