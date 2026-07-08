"""Geo helpers for Map M1 — location verification + coarse distance.

Design constraints (see the Map View analysis):
- Raw GPS coordinates are NEVER returned to any client. They live in the
  separate `user_locations` collection and are only ever read server-side
  to compute a coarse, bucketed distance.
- Distance is exposed only as a rounded bucket ("~5 km", "50+ km"), never
  a precise value — precise distance enables trilateration of a user's home.
- Verification is offline: we match a GPS point to the nearest Uzbek region
  centroid and compare it to the region the user claimed. No external
  geocoding API (no cost, no third-party sharing of coordinates).
"""
from __future__ import annotations

import math
from typing import Optional

# Approximate centroids of Uzbekistan regions. Keys must match the region
# strings stored on the user doc (see frontend/src/lib/locations.js UZ list).
REGION_CENTROIDS = {
    "Toshkent shahri": (41.311, 69.280),
    "Toshkent viloyati": (41.000, 69.350),
    "Samarqand": (39.654, 66.960),
    "Buxoro": (39.767, 64.421),
    "Andijon": (40.783, 72.344),
    "Farg'ona": (40.389, 71.783),
    "Namangan": (40.998, 71.672),
    "Qashqadaryo": (38.861, 65.789),
    "Surxondaryo": (37.224, 67.278),
    "Sirdaryo": (40.489, 68.786),
    "Jizzax": (40.116, 67.842),
    "Navoiy": (40.104, 65.379),
    "Xorazm": (41.550, 60.631),
    "Qoraqalpog'iston": (42.460, 59.617),
}


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def region_from_coords(lat: float, lon: float) -> Optional[str]:
    """Nearest Uzbek region centroid to the given point, or None if the point
    is implausibly far from any region (outside the country)."""
    best_region = None
    best_dist = float("inf")
    for region, (rlat, rlon) in REGION_CENTROIDS.items():
        d = haversine_km(lat, lon, rlat, rlon)
        if d < best_dist:
            best_dist = d
            best_region = region
    # Region centroids are up to ~200km apart; a point more than 350km from
    # the nearest centroid is almost certainly outside Uzbekistan.
    if best_dist > 350:
        return None
    return best_region


def coords_match_region(lat: float, lon: float, claimed_region: str) -> bool:
    """True if the GPS point resolves to the region the user claimed."""
    if not claimed_region:
        return False
    detected = region_from_coords(lat, lon)
    return detected is not None and detected == claimed_region


def distance_bucket(km: float, lang: str = "uz") -> str:
    """Coarsen a precise distance into a privacy-safe display bucket.

    Rounds to the nearest 5 km up to 50, then a single "50+ km" bucket.
    Never returns a precise figure — precise distance across multiple reads
    enables trilateration of the target's location.
    """
    unit = {"uz": "km", "ru": "км", "en": "km"}.get(lang, "km")
    if km < 1:
        return {"uz": "1 km dan yaqin", "ru": "менее 1 км", "en": "under 1 km"}.get(lang, "under 1 km")
    if km >= 50:
        return f"50+ {unit}"
    nearest = max(5, int(round(km / 5.0) * 5))
    return f"~{nearest} {unit}"


def valid_coords(lat, lon) -> bool:
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return False
    return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
