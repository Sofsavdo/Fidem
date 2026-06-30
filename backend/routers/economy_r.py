"""Economy system: Influence Score, Status Ladder, Donations, Lifetime Contribution (V3.2)."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_admin, get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt, push_notif
from models import new_id

router = APIRouter(tags=["economy"])

# Status thresholds (based on influence score)
STATUS_THRESHOLDS = {
    "bronze": 0,
    "silver": 1000,
    "gold": 5000,
    "platinum": 15000,
    "diamond": 50000,
    "legend": 150000,
}

# Donation bonus percentages
DONATION_BONUS_STANDARD = 0.10  # 10%
DONATION_BONUS_WEEKEND = 0.15   # 15%
DONATION_BONUS_EVENT = 0.25     # 25%
DONATION_BONUS_FOUNDER = 0.15   # 15% (prestige-only)
DONATION_BONUS_AMBASSADOR = 0.20  # 20%


def calculate_status_from_influence(influence_score: int) -> str:
    """Calculate status based on influence score."""
    if influence_score >= 150000:
        return "legend"
    elif influence_score >= 50000:
        return "diamond"
    elif influence_score >= 15000:
        return "platinum"
    elif influence_score >= 5000:
        return "gold"
    elif influence_score >= 1000:
        return "silver"
    else:
        return "bronze"


async def add_influence(
    user_id: str,
    amount: int,
    source: str,
    details: Optional[dict] = None
) -> None:
    """Add influence to a user and record in history."""
    influence_record = {
        "id": new_id(),
        "source": source,
        "amount": amount,
        "influence_gained": amount,
        "created_at": iso(now_utc()),
        "details": details or {}
    }
    
    # Update influence score and history
    await db.users.update_one(
        {"id": user_id},
        {
            "$inc": {"influence_score": amount},
            "$push": {"influence_history": influence_record}
        }
    )
    
    # Recalculate status
    user = await get_user(user_id)
    new_status = calculate_status_from_influence(user.get("influence_score", 0))
    
    # Update status if changed
    if user.get("status") != new_status:
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "status": new_status,
                    "status_since": iso(now_utc())
                },
                "$push": {
                    "status_history": {
                        "status": new_status,
                        "achieved_at": iso(now_utc()),
                        "influence_score_at_time": user.get("influence_score", 0)
                    }
                }
            }
        )


@router.get("/me/influence")
async def get_influence(uid: str = Depends(get_current_user_id)):
    """Get user's influence score and history."""
    user = await get_user(uid)
    return {
        "influence_score": user.get("influence_score", 0),
        "status": user.get("status", "bronze"),
        "status_since": user.get("status_since"),
        "badges": user.get("badges", []),
        "influence_history": user.get("influence_history", [])[-20:]  # Last 20 records
    }


@router.get("/me/status")
async def get_status(uid: str = Depends(get_current_user_id)):
    """Get user's current status and history."""
    user = await get_user(uid)
    return {
        "status": user.get("status", "bronze"),
        "status_since": user.get("status_since"),
        "badges": user.get("badges", []),
        "status_history": user.get("status_history", [])[-10:]  # Last 10 records
    }


@router.get("/me/badges")
async def get_badges(uid: str = Depends(get_current_user_id)):
    """Get user's badges."""
    user = await get_user(uid)
    return {
        "badges": user.get("badges", []),
        "is_founder": user.get("is_founder", False),
        "founder_type": user.get("founder_type"),
        "founder_achieved_at": user.get("founder_achieved_at")
    }


@router.post("/donation/convert")
async def convert_to_influence(
    source: str = Body(..., embed=True),  # "balance" | "referral_earnings" | "bonus"
    amount: int = Body(..., embed=True),
    uid: str = Depends(get_current_user_id),
):
    """Convert balance, referral earnings, or bonuses to influence with bonus."""
    if amount <= 0:
        raise HTTPException(400, "Amount must be positive")
    
    user = await get_user(uid)
    
    # Determine bonus percentage
    bonus_pct = DONATION_BONUS_STANDARD
    
    # Weekend bonus
    if now_utc().weekday() >= 5:  # Saturday (5) or Sunday (6)
        bonus_pct = DONATION_BONUS_WEEKEND
    
    # Founder bonus (prestige-only)
    if user.get("is_founder"):
        bonus_pct = max(bonus_pct, DONATION_BONUS_FOUNDER)
    
    # Ambassador bonus
    if "ambassador" in user.get("badges", []):
        bonus_pct = max(bonus_pct, DONATION_BONUS_AMBASSADOR)
    
    # Validate source and check balance
    if source == "balance":
        min_conversion = 10000
        max_conversion = 500000
        if amount < min_conversion:
            raise HTTPException(400, f"Minimum conversion: {min_conversion:,} so'm")
        if amount > max_conversion:
            raise HTTPException(400, f"Maximum conversion per day: {max_conversion:,} so'm")
        
        balance = user.get("balance", 0)
        if balance < amount:
            raise HTTPException(400, f"Insufficient balance. Available: {balance:,} so'm")
        
        # Deduct balance
        await db.users.update_one(
            {"id": uid, "balance": {"$gte": amount}},
            {"$inc": {"balance": -amount}}
        )
        
    elif source == "referral_earnings":
        min_conversion = 10000
        max_conversion = 500000
        if amount < min_conversion:
            raise HTTPException(400, f"Minimum conversion: {min_conversion:,} so'm")
        if amount > max_conversion:
            raise HTTPException(400, f"Maximum conversion per day: {max_conversion:,} so'm")
        
        withdrawable = user.get("referral_earnings_withdrawable", 0)
        if withdrawable < amount:
            raise HTTPException(400, f"Insufficient referral earnings. Available: {withdrawable:,} so'm")
        
        # Deduct from withdrawable
        await db.users.update_one(
            {"id": uid, "referral_earnings_withdrawable": {"$gte": amount}},
            {"$inc": {"referral_earnings_withdrawable": -amount}}
        )
        
    elif source == "bonus":
        min_conversion = 1000
        max_conversion = 50000
        if amount < min_conversion:
            raise HTTPException(400, f"Minimum conversion: {min_conversion:,} so'm")
        if amount > max_conversion:
            raise HTTPException(400, f"Maximum conversion per day: {max_conversion:,} so'm")
        
        # Note: Bonus conversion would need a separate bonus balance field
        # For now, we'll allow it but track in history
        pass
    else:
        raise HTTPException(400, "Invalid source. Must be: balance, referral_earnings, or bonus")
    
    # Calculate influence with bonus
    influence_gained = int(amount * (1 + bonus_pct))
    
    # Record donation
    donation_record = {
        "id": new_id(),
        "source": source,
        "amount_converted": amount,
        "influence_gained": influence_gained,
        "bonus_percentage": int(bonus_pct * 100),
        "created_at": iso(now_utc())
    }
    
    await db.users.update_one(
        {"id": uid},
        {"$push": {"donations": donation_record}}
    )
    
    # Add influence
    await add_influence(uid, influence_gained, "donation", {
        "source": source,
        "amount_converted": amount,
        "bonus_percentage": int(bonus_pct * 100)
    })
    
    # Update lifetime contribution
    await db.users.update_one(
        {"id": uid},
        {
            "$inc": {
                "lifetime_contribution": amount,
                "lifetime_contribution_breakdown.donations_converted": amount
            }
        }
    )
    
    return {
        "ok": True,
        "amount_converted": amount,
        "influence_gained": influence_gained,
        "bonus_percentage": int(bonus_pct * 100)
    }


@router.get("/donation/history")
async def donation_history(uid: str = Depends(get_current_user_id)):
    """Get donation conversion history."""
    user = await get_user(uid)
    return {
        "donations": user.get("donations", [])[-50:]  # Last 50 records
    }


@router.get("/donation/rates")
async def donation_rates(uid: str = Depends(get_current_user_id)):
    """Get current donation conversion rates."""
    user = await get_user(uid)
    
    bonus_pct = DONATION_BONUS_STANDARD
    
    # Weekend bonus
    if now_utc().weekday() >= 5:
        bonus_pct = DONATION_BONUS_WEEKEND
    
    # Founder bonus
    if user.get("is_founder"):
        bonus_pct = max(bonus_pct, DONATION_BONUS_FOUNDER)
    
    # Ambassador bonus
    if "ambassador" in user.get("badges", []):
        bonus_pct = max(bonus_pct, DONATION_BONUS_AMBASSADOR)
    
    return {
        "standard_bonus": int(DONATION_BONUS_STANDARD * 100),
        "weekend_bonus": int(DONATION_BONUS_WEEKEND * 100),
        "event_bonus": int(DONATION_BONUS_EVENT * 100),
        "founder_bonus": int(DONATION_BONUS_FOUNDER * 100),
        "ambassador_bonus": int(DONATION_BONUS_AMBASSADOR * 100),
        "current_bonus": int(bonus_pct * 100),
        "is_weekend": now_utc().weekday() >= 5
    }


@router.get("/me/lifetime-contribution")
async def get_lifetime_contribution(uid: str = Depends(get_current_user_id)):
    """Get user's lifetime contribution."""
    user = await get_user(uid)
    return {
        "lifetime_contribution": user.get("lifetime_contribution", 0),
        "breakdown": user.get("lifetime_contribution_breakdown", {
            "balance_spent": 0,
            "referral_earnings_converted": 0,
            "donations_converted": 0,
            "subscription_payments": 0,
            "gifts_sent_value": 0
        })
    }


def calculate_activity_score(user: dict) -> int:
    """Calculate activity score (0-100) based on login frequency and engagement."""
    # Login frequency (past 30 days): 0-50 points
    last_active = parse_dt(user.get("last_active", now_utc()))
    days_since_active = (now_utc() - last_active).days
    
    login_score = 0
    if days_since_active <= 1:
        login_score = 50
    elif days_since_active <= 7:
        login_score = 40
    elif days_since_active <= 14:
        login_score = 30
    elif days_since_active <= 30:
        login_score = 20
    else:
        login_score = 0
    
    # Engagement actions (likes, messages, views): 0-50 points
    # For now, use a simple heuristic based on profile completeness and activity
    engagement_score = min(50, user.get("completeness", 0) // 2)
    
    return min(100, login_score + engagement_score)


def calculate_contribution_score(user: dict) -> int:
    """Calculate contribution score (0-100) based on lifetime contribution."""
    lifetime_contrib = user.get("lifetime_contribution", 0)
    
    # Normalize to 0-100 scale (assuming 1,000,000 so'm as max for now)
    max_contrib = 1000000
    contrib_score = min(100, int((lifetime_contrib / max_contrib) * 100))
    
    return contrib_score


def calculate_ranking_score(user: dict) -> int:
    """Calculate ranking score: Influence 70%, Activity 20%, Contribution 10%."""
    influence_score = user.get("influence_score", 0)
    activity_score = calculate_activity_score(user)
    contribution_score = calculate_contribution_score(user)
    
    # Normalize influence to 0-100 scale (assuming 500,000 as max for now)
    max_influence = 500000
    normalized_influence = min(100, int((influence_score / max_influence) * 100))
    
    # Weighted formula
    ranking_score = int(
        (normalized_influence * 0.70) +
        (activity_score * 0.20) +
        (contribution_score * 0.10)
    )
    
    return ranking_score


async def update_user_ranking_score(user_id: str) -> None:
    """Update user's activity score and ranking score."""
    user = await get_user(user_id)
    
    activity_score = calculate_activity_score(user)
    contribution_score = calculate_contribution_score(user)
    ranking_score = calculate_ranking_score(user)
    
    await db.users.update_one(
        {"id": user_id},
        {
            "$set": {
                "activity_score": activity_score,
                "ranking_score": ranking_score
            }
        }
    )


@router.get("/me/ranking-score")
async def get_ranking_score(uid: str = Depends(get_current_user_id)):
    """Get user's ranking score breakdown."""
    user = await get_user(uid)
    
    # Recalculate scores
    activity_score = calculate_activity_score(user)
    contribution_score = calculate_contribution_score(user)
    ranking_score = calculate_ranking_score(user)
    
    influence_score = user.get("influence_score", 0)
    max_influence = 500000
    normalized_influence = min(100, int((influence_score / max_influence) * 100))
    
    return {
        "ranking_score": ranking_score,
        "influence_score": influence_score,
        "normalized_influence": normalized_influence,
        "activity_score": activity_score,
        "contribution_score": contribution_score,
        "weights": {
            "influence": 0.70,
            "activity": 0.20,
            "contribution": 0.10
        }
    }


async def recalculate_titan_status() -> None:
    """Recalculate Titan status for top 100 active ranking users."""
    # Get active users (logged in within last 30 days)
    thirty_days_ago = now_utc() - timedelta(days=30)
    
    # Get top 100 users by ranking score
    top_users = await db.users.find(
        {
            "onboarded": True,
            "blocked": {"$ne": True},
            "last_active": {"$gte": iso(thirty_days_ago)}
        },
        {"id": 1, "ranking_score": 1, "badges": 1}
    ).sort("ranking_score", -1).limit(100).to_list(100)
    
    top_user_ids = {u["id"] for u in top_users}
    
    # Update Titan status
    # Remove Titan badge from users who are no longer in top 100
    # Recalculate their status based on actual influence score
    for user in await db.users.find({"badges": "titan", "id": {"$nin": list(top_user_ids)}}, {"id": 1, "influence_score": 1}).to_list(None):
        new_status = calculate_status_from_influence(user.get("influence_score", 0))
        await db.users.update_one(
            {"id": user["id"]},
            {
                "$pull": {"badges": "titan"},
                "$set": {"status": new_status}
            }
        )
    
    # Add Titan badge to top 100 users
    for user in top_users:
        current_badges = user.get("badges", [])
        if "titan" not in current_badges:
            await db.users.update_one(
                {"id": user["id"]},
                {
                    "$push": {"badges": "titan"},
                    "$set": {"status": "titan", "status_since": iso(now_utc())}
                }
            )


async def recalculate_ambassador_status() -> None:
    """Recalculate Ambassador status for strong referrers."""
    # Ambassador criteria:
    # - 50+ successful referrals
    # - 20+ paid referrals
    # - 25%+ conversion rate (paid / total)
    # - Active (logged in within last 30 days)
    
    thirty_days_ago = now_utc() - timedelta(days=30)
    
    # Get users with 50+ referrals
    users_with_refs = await db.users.find(
        {
            "onboarded": True,
            "blocked": {"$ne": True},
            "last_active": {"$gte": iso(thirty_days_ago)},
            "ref_count": {"$gte": 50}
        },
        {"id": 1, "ref_count": 1, "badges": 1}
    ).to_list(None)
    
    for user in users_with_refs:
        uid = user["id"]
        ref_count = user.get("ref_count", 0)
        
        # Count paid referrals (from referral_earnings with type "paid_subscription" and status "paid" or "withdrawable")
        paid_ref_count = 0
        earnings = user.get("referral_earnings", [])
        for earning in earnings:
            if earning.get("type") == "paid_subscription" and earning.get("status") in ("paid", "withdrawable"):
                paid_ref_count += 1
        
        # Calculate conversion rate
        conversion_rate = (paid_ref_count / ref_count * 100) if ref_count > 0 else 0
        
        # Check Ambassador criteria
        is_ambassador = (
            ref_count >= 50 and
            paid_ref_count >= 20 and
            conversion_rate >= 25
        )
        
        current_badges = user.get("badges", [])
        
        if is_ambassador and "ambassador" not in current_badges:
            # Add Ambassador badge
            await db.users.update_one(
                {"id": uid},
                {
                    "$push": {"badges": "ambassador"},
                    "$set": {"status": "ambassador", "status_since": iso(now_utc())}
                }
            )
        elif not is_ambassador and "ambassador" in current_badges:
            # Remove Ambassador badge
            # Recalculate status based on actual influence score
            user = await get_user(uid)
            new_status = calculate_status_from_influence(user.get("influence_score", 0))
            await db.users.update_one(
                {"id": uid},
                {
                    "$pull": {"badges": "ambassador"},
                    "$set": {"status": new_status}
                }
            )


@router.post("/admin/recalculate-statuses")
async def admin_recalculate_statuses(_: str = Depends(get_current_admin)):
    """Admin endpoint to recalculate Titan and Ambassador statuses."""
    await recalculate_titan_status()
    await recalculate_ambassador_status()
    return {"ok": True, "message": "Titan and Ambassador statuses recalculated"}


async def assign_founder_badges() -> None:
    """Assign Founder badge to first 5,000 registered users (one-time migration)."""
    # Get first 5,000 users by registration date
    first_5000 = await db.users.find(
        {"is_founder": {"$ne": True}},
        {"id": 1, "created_at": 1}
    ).sort("created_at", 1).limit(5000).to_list(5000)
    
    for user in first_5000:
        uid = user["id"]
        await db.users.update_one(
            {"id": uid},
            {
                "$set": {
                    "is_founder": True,
                    "founder_type": "early_adopter",
                    "founder_achieved_at": user.get("created_at")
                },
                "$push": {"badges": "founder"}
            }
        )


@router.post("/admin/assign-founder-badges")
async def admin_assign_founder_badges(_: str = Depends(get_current_admin)):
    """Admin endpoint to assign Founder badges to first 5,000 users (one-time)."""
    await assign_founder_badges()
    return {"ok": True, "message": "Founder badges assigned to first 5,000 users"}
