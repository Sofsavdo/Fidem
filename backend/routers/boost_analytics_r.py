"""Boost & Spotlight analytics + Leaderboard.
Lightweight tracking: counters on user doc per boost session.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt, user_public

router = APIRouter(prefix="/boost", tags=["boost-analytics"])


@router.get("/analytics")
async def boost_analytics(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    boost_until = me.get("boost_until")
    spotlight_until = me.get("spotlight_until")
    now = now_utc()
    boost_active = bool(boost_until and parse_dt(boost_until) > now)
    spotlight_active = bool(spotlight_until and parse_dt(spotlight_until) > now)

    metrics = me.get("boost_metrics") or {}
    return {
        "boost": {
            "active": boost_active,
            "until": boost_until,
            "impressions": int(metrics.get("impressions", 0) or 0),
            "views": int(metrics.get("views", 0) or 0),
            "likes": int(metrics.get("likes", 0) or 0),
            "messages": int(metrics.get("messages", 0) or 0),
            "roses": int(metrics.get("roses", 0) or 0),
            "started_at": metrics.get("started_at"),
        },
        "spotlight": {
            "active": spotlight_active,
            "until": spotlight_until,
            "impressions": int(metrics.get("sp_impressions", 0) or 0),
            "views": int(metrics.get("sp_views", 0) or 0),
            "started_at": metrics.get("sp_started_at"),
        },
        "lifetime": {
            "total_impressions": int(me.get("impressions_total", 0) or 0),
            "total_views": int(me.get("views_total", 0) or 0),
            "total_likes": int(me.get("likes_received_total", 0) or 0),
            "gifts_received": int(me.get("gifts_received_total", 0) or 0),
        },
    }


@router.get("/leaderboard")
async def boost_leaderboard(_uid: str = Depends(get_current_user_id)):
    """Top 10 users by current-session boost impressions (active boost only)."""
    now_iso = iso(now_utc())
    pipeline = [
        {"$match": {"boost_until": {"$gt": now_iso}, "onboarded": True, "blocked": {"$ne": True}}},
        {"$addFields": {"impressions_now": {"$ifNull": ["$boost_metrics.impressions", 0]}}},
        {"$sort": {"impressions_now": -1}},
        {"$limit": 10},
    ]
    docs = await db.users.aggregate(pipeline).to_list(10)
    out = []
    for d in docs:
        pub = user_public(d)
        pub["boost_impressions"] = int((d.get("boost_metrics") or {}).get("impressions", 0) or 0)
        pub["boost_until"] = d.get("boost_until")
        out.append(pub)
    return out
