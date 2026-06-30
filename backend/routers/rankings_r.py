"""Rankings & Leaderboards (V3.2)."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt
from services import age_from_birth

router = APIRouter(tags=["rankings"])


def format_ranking_user(user: dict, rank: int) -> dict:
    """Format user data for ranking display."""
    name = user.get("name", "")
    # Display first name + last initial
    name_parts = name.split()
    if len(name_parts) >= 2:
        display_name = f"{name_parts[0]} {name_parts[1][0]}."
    else:
        display_name = name
    
    # Only include photo if not locked
    photo_url = None
    if not user.get("photo_locked", False):
        photo_url = user.get("photo_url")
    
    return {
        "user_id": user["id"],
        "rank": rank,
        "name": display_name,
        "age": age_from_birth(user.get("birth_date", "2000-01-01")),
        "city": user.get("city", user.get("region", "")),
        "status": user.get("status", "bronze"),
        "badges": user.get("badges", []),
        "influence_score": user.get("influence_score", 0),
        "activity_score": user.get("activity_score", 0),
        "contribution_score": 0,  # Will be calculated
        "ranking_score": user.get("ranking_score", 0),
        "photo_url": photo_url,
    }


async def get_ranking_users(
    ranking_type: str,
    filter_value: Optional[str] = None,
    limit: int = 100
) -> list:
    """Get users for a specific ranking type."""
    query = {
        "onboarded": True,
        "blocked": {"$ne": True},
        "show_in_rankings": True
    }
    
    # Apply filters based on ranking type
    if ranking_type == "country" and filter_value:
        query["country"] = filter_value
    elif ranking_type == "region" and filter_value:
        query["region"] = filter_value
    elif ranking_type == "city" and filter_value:
        query["city"] = filter_value
    elif ranking_type == "age_group":
        # Filter by age group
        if filter_value == "18-25":
            query["birth_date"] = {"$gte": "2001-01-01"}
        elif filter_value == "26-35":
            query["birth_date"] = {"$lte": "2000-12-31", "$gte": "1990-01-01"}
        elif filter_value == "36-45":
            query["birth_date"] = {"$lte": "1989-12-31", "$gte": "1980-01-01"}
        elif filter_value == "46+":
            query["birth_date"] = {"$lte": "1979-12-31"}
    elif ranking_type == "men":
        query["gender"] = "male"
    elif ranking_type == "women":
        query["gender"] = "female"
    elif ranking_type == "ambassadors":
        query["badges"] = "ambassador"
    
    # Get users sorted by ranking score
    users = await db.users.find(
        query,
        {
            "id": 1, "name": 1, "birth_date": 1, "city": 1, "region": 1,
            "status": 1, "badges": 1, "influence_score": 1,
            "activity_score": 1, "ranking_score": 1, "photo_url": 1
        }
    ).sort("ranking_score", -1).limit(limit).to_list(limit)
    
    # Format with ranks
    ranked_users = []
    for idx, user in enumerate(users, 1):
        ranked_users.append(format_ranking_user(user, idx))
    
    return ranked_users


@router.get("/rankings/global")
async def global_ranking(limit: int = Query(100, ge=1, le=500)):
    """Global ranking."""
    users = await get_ranking_users("global", limit=limit)
    return {"ranking_type": "global", "rankings": users}


@router.get("/rankings/country/{country_code}")
async def country_ranking(country_code: str, limit: int = Query(100, ge=1, le=500)):
    """Country ranking."""
    users = await get_ranking_users("country", filter_value=country_code.upper(), limit=limit)
    return {"ranking_type": "country", "filter_value": country_code.upper(), "rankings": users}


@router.get("/rankings/region/{region_name}")
async def region_ranking(region_name: str, limit: int = Query(100, ge=1, le=500)):
    """Region ranking."""
    users = await get_ranking_users("region", filter_value=region_name, limit=limit)
    return {"ranking_type": "region", "filter_value": region_name, "rankings": users}


@router.get("/rankings/city/{city_name}")
async def city_ranking(city_name: str, limit: int = Query(100, ge=1, le=500)):
    """City ranking."""
    users = await get_ranking_users("city", filter_value=city_name, limit=limit)
    return {"ranking_type": "city", "filter_value": city_name, "rankings": users}


@router.get("/rankings/age_group/{group}")
async def age_group_ranking(group: str, limit: int = Query(100, ge=1, le=500)):
    """Age group ranking."""
    valid_groups = ["18-25", "26-35", "36-45", "46+"]
    if group not in valid_groups:
        raise HTTPException(400, f"Invalid age group. Must be one of: {', '.join(valid_groups)}")
    
    users = await get_ranking_users("age_group", filter_value=group, limit=limit)
    return {"ranking_type": "age_group", "filter_value": group, "rankings": users}


@router.get("/rankings/men")
async def men_ranking(limit: int = Query(100, ge=1, le=500)):
    """Men ranking."""
    users = await get_ranking_users("men", limit=limit)
    return {"ranking_type": "men", "rankings": users}


@router.get("/rankings/women")
async def women_ranking(limit: int = Query(100, ge=1, le=500)):
    """Women ranking."""
    users = await get_ranking_users("women", limit=limit)
    return {"ranking_type": "women", "rankings": users}


@router.get("/rankings/ambassadors")
async def ambassadors_ranking(limit: int = Query(100, ge=1, le=500)):
    """Ambassadors ranking."""
    users = await get_ranking_users("ambassadors", limit=limit)
    return {"ranking_type": "ambassadors", "rankings": users}


@router.get("/rankings/me")
async def my_rankings(uid: str = Depends(get_current_user_id)):
    """Get user's rank in all categories."""
    user = await get_user(uid)
    
    if not user.get("show_in_rankings", True):
        return {"message": "You have opted out of rankings"}
    
    # Get ranking score
    my_ranking_score = user.get("ranking_score", 0)
    
    # Count users with higher ranking score in each category
    categories = {
        "global": {},
        "men": {"gender": "male"},
        "women": {"gender": "female"},
        "ambassadors": {"badges": "ambassador"}
    }
    
    results = {}
    for category, filters in categories.items():
        query = {
            "onboarded": True,
            "blocked": {"$ne": True},
            "show_in_rankings": True,
            "ranking_score": {"$gt": my_ranking_score}
        }
        query.update(filters)
        
        higher_count = await db.users.count_documents(query)
        results[category] = {
            "rank": higher_count + 1,
            "ranking_score": my_ranking_score
        }
    
    return {"my_rankings": results}


@router.put("/me/settings/rankings")
async def toggle_rankings_visibility(
    show: bool = Body(..., embed=True),
    uid: str = Depends(get_current_user_id)
):
    """Toggle visibility in rankings."""
    await db.users.update_one(
        {"id": uid},
        {"$set": {"show_in_rankings": show}}
    )
    return {"ok": True, "show_in_rankings": show}
