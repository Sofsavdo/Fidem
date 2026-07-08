"""Location verification (Map M1).

Client sends its GPS point once; we resolve it to the nearest Uzbek region
and compare against the region the user claimed during onboarding. The raw
coordinate is stored in the isolated `user_locations` collection (never
returned to any client); only the boolean `location_verified` badge and a
coarse bucketed distance are ever exposed.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc
from geo import coords_match_region, region_from_coords, valid_coords

router = APIRouter(tags=["location"])


@router.post("/location/verify")
async def verify_location(
    lat: float = Body(..., embed=True),
    lng: float = Body(..., embed=True),
    uid: str = Depends(get_current_user_id),
):
    if not valid_coords(lat, lng):
        raise HTTPException(400, "Noto'g'ri koordinatalar")

    me = await get_user(uid)
    claimed_region = me.get("region", "")
    detected_region = region_from_coords(lat, lng)
    verified = coords_match_region(lat, lng, claimed_region)

    # Raw point isolated in its own collection — never surfaced via user_public
    # or any candidate payload. Only read server-side for coarse distance.
    await db.user_locations.update_one(
        {"user_id": uid},
        {"$set": {
            "user_id": uid,
            "geo_point": [float(lng), float(lat)],  # GeoJSON order: [lng, lat]
            "updated_at": iso(now_utc()),
        }},
        upsert=True,
    )

    await db.users.update_one(
        {"id": uid},
        {"$set": {
            "location_verified": bool(verified),
            "location_verified_at": iso(now_utc()) if verified else None,
            "location_consent": True,
        }},
    )

    return {
        "verified": bool(verified),
        "claimed_region": claimed_region,
        "detected_region": detected_region,
        # true only when a real region was detected but it differs from the
        # claimed one — lets the UI say "you seem to be in X, not Y"
        "mismatch": bool(detected_region and detected_region != claimed_region),
    }
