"""Shared core: DB, helpers, connection manager, rate limiter."""
from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import bcrypt
import bleach
from fastapi import HTTPException, Request, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient

from models import new_id, now_utc
from services import (
    age_from_birth,
    compute_completeness,
    is_online,
    last_active_label,
    last_active_minutes,
    send_telegram_message,
)

log = logging.getLogger("fidem")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "Fidem_Appbot")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "fidem-tg")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@fidem.uz")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# Set default ADMIN_PASSWORD if not provided
if not ADMIN_PASSWORD:
    ADMIN_PASSWORD = "Admin@123"  # Default for development only
    log.warning(
        "ADMIN_PASSWORD is not set - falling back to a well-known default "
        "('Admin@123'). Set ADMIN_PASSWORD in the environment before exposing "
        "this deployment to real users; the default is public (audit docs, "
        "test fixtures) and grants full admin access."
    )
PRICE_PREMIUM = int(os.environ.get("PRICE_PREMIUM_UZS", "79000"))
PRICE_VIP = int(os.environ.get("PRICE_VIP_UZS", "199000"))
PRICE_STANDARD = int(os.environ.get("PRICE_STANDARD_UZS", "19900"))
PRICE_CHAT_UNLOCK = int(os.environ.get("PRICE_CHAT_UNLOCK_UZS", "9900"))
CHAT_UNLOCK_COINS = int(os.environ.get("CHAT_UNLOCK_COINS", "100"))
CHAT_GUARANTEE_HOURS = int(os.environ.get("CHAT_GUARANTEE_HOURS", "48"))
PAID_PLANS = ("standard", "premium", "vip")


def get_webapp_url() -> str:
    return os.environ.get(
        "WEBAPP_URL",
        "https://fidem-frontend-production.up.railway.app",
    ).rstrip("/")


def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def check_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def parse_dt(v: Any) -> datetime:
    if isinstance(v, datetime):
        return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            pass
    return now_utc()


def chat_id_for(a: str, b: str) -> str:
    return "_".join(sorted([a, b]))


def sanitize_text(text: str, allow_tags: bool = False) -> str:
    """Sanitize user-provided text to prevent XSS attacks."""
    if not text:
        return ""
    if allow_tags:
        # Allow some basic formatting tags
        allowed_tags = ["b", "i", "u", "em", "strong", "br", "p"]
        return bleach.clean(text, tags=allowed_tags, strip=True)
    return bleach.clean(text, tags=[], strip=True)


async def get_user(uid: str) -> dict:
    user = await db.users.find_one({"id": uid}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    plan_until = user.get("plan_until")
    if plan_until and user.get("plan") in ("standard", "premium", "vip"):
        try:
            until_dt = parse_dt(plan_until)
            if until_dt < now_utc():
                await db.users.update_one(
                    {"id": uid},
                    {"$set": {"plan": "free", "plan_expired_at": iso(now_utc())}},
                )
                user["plan"] = "free"
                user["plan_until"] = None
        except Exception:
            pass
    return user


async def touch_active(uid: str) -> None:
    await db.users.update_one({"id": uid}, {"$set": {"last_active": iso(now_utc())}})


def strip_locked_photo(pub: dict) -> dict:
    """Remove photo_url from API payloads when the viewer has not unlocked the photo."""
    if pub.get("photo_unlocked"):
        return pub
    out = dict(pub)
    out["photo_url"] = None
    out["photo_unlocked"] = False
    return out


def user_public(u: dict, include_private: bool = False) -> dict:
    """Public-safe view of a user document.

    include_private=True must only be passed for the account's own owner
    (e.g. /auth/me) or an admin - it adds contact info, device/IP data and
    fraud-review fields that must never be visible to other end users.
    """
    age = age_from_birth(u.get("birth_date", "2000-01-01"))
    la = parse_dt(u.get("last_active"))
    out = {
        "id": u["id"],
        "name": u.get("name", ""),
        "gender": u.get("gender", "male"),
        "age": age,
        "region": u.get("region", ""),
        "district": u.get("district", ""),
        "marital_status": u.get("marital_status", "single"),
        "has_children": u.get("has_children", False),
        "children_count": u.get("children_count", 0),
        "height_cm": u.get("height_cm", 170),
        "weight_kg": u.get("weight_kg", 70),
        "education": u.get("education", ""),
        "profession": u.get("profession", ""),
        "religion": u.get("religion", ""),
        "smoking": u.get("smoking", "no"),
        "alcohol": u.get("alcohol", "no"),
        "relocation": bool(u.get("relocation", False)),
        "bio": u.get("bio", ""),
        "photo_url": u.get("photo_url"),
        "photo_verified": bool(u.get("photo_verified", False)),
        "verified_identity": u.get("verified_identity", False),
        "verified_selfie": u.get("verified_selfie", False),
        "verified_financial": u.get("verified_financial", False),
        "last_active": la,
        "last_active_label": last_active_label(la),
        "last_active_minutes": last_active_minutes(la),
        "online": is_online(la),
        "completeness": u.get("completeness", compute_completeness(u)),
        "avg_response_min": u.get("avg_response_min"),
        "plan": u.get("plan", "free"),
        "blocked": u.get("blocked", False),
        "prompts": u.get("prompts") or [],
        "big5_scores": u.get("big5_scores") or {},
        "balance": u.get("balance", 0),
    }
    if include_private:
        # Contact info, device/IP data and fraud-review fields - only for the
        # account owner (self) or an admin, never for other end users.
        out.update({
            "email": u.get("email", ""),
            "phone": u.get("phone", ""),
            "telegram_id": u.get("telegram_id", ""),
            "telegram_username": u.get("telegram_username", ""),
            "ip_address": u.get("ip_address", ""),
            "user_agent": u.get("user_agent", ""),
            "created_at": u.get("created_at", ""),
            "fraud_score": u.get("fraud_score", 0),
            "fraud_reasons": u.get("fraud_reasons", []),
            "flagged_as_bot": u.get("flagged_as_bot", False),
        })
    return out


def user_public_minimal(u: dict) -> dict:
    """Lean version for candidate lists - removes heavy fields."""
    age = age_from_birth(u.get("birth_date", "2000-01-01"))
    la = parse_dt(u.get("last_active"))
    return {
        "id": u["id"],
        "name": u.get("name", ""),
        "gender": u.get("gender", "male"),
        "age": age,
        "region": u.get("region", ""),
        "district": u.get("district", ""),
        "marital_status": u.get("marital_status", "single"),
        "has_children": u.get("has_children", False),
        "height_cm": u.get("height_cm", 170),
        "education": u.get("education", ""),
        "profession": u.get("profession", ""),
        "bio": u.get("bio", ""),
        "photo_url": u.get("photo_url"),
        "verified_selfie": u.get("verified_selfie", False),
        "verified_financial": u.get("verified_financial", False),
        "last_active": la,
        "last_active_label": last_active_label(la),
        "online": is_online(la),
        "plan": u.get("plan", "free"),
        "blocked": u.get("blocked", False),
    }


async def notify_telegram(uid: str, text: str, link: Optional[str] = None, kind: str = "general") -> None:
    """Send Telegram notification with user preference check and rate limiting."""
    user = await db.users.find_one({"id": uid}, {"telegram_id": 1, "notification_prefs": 1, "_id": 0})
    if not user or not user.get("telegram_id"):
        return
    
    # Check user notification preferences
    prefs = user.get("notification_prefs", {})
    if prefs.get(f"disable_{kind}", False):
        log.debug(f"User {uid} has disabled {kind} notifications")
        return
    
    # Rate limiting: check last notification time for this kind
    last_notif_key = f"last_notif_{kind}"
    last_notif = user.get(last_notif_key)
    if last_notif:
        try:
            last_time = parse_dt(last_notif)
            # Don't send more than 3 notifications of same kind per hour
            if (now_utc() - last_time).total_seconds() < 1200:  # 20 minutes
                log.debug(f"Rate limited {kind} notification for user {uid}")
                return
        except Exception:
            pass
    
    try:
        base = get_webapp_url()
        full = base

        if link:
            full = link if link.startswith("http") else f"{base}{link}"

        reply_markup = {
            "inline_keyboard": [
                [
                    {
                        "text": "💖 FIDEM'ni ochish",
                        "web_app": {"url": full},
                    }
                ]
            ]
        }

        await send_telegram_message(
            int(user["telegram_id"]),
            text,
            reply_markup=reply_markup,
        )
        
        # Update last notification time
        await db.users.update_one(
            {"id": uid},
            {"$set": {last_notif_key: iso(now_utc())}}
        )
    except Exception as e:
        log.warning(f"telegram notify failed: {e}")


async def notify_telegram_batch(uids: list[str], text: str, link: Optional[str] = None, kind: str = "general") -> int:
    """Send batch notifications with rate limiting and preference checks."""
    sent_count = 0
    for uid in uids:
        await notify_telegram(uid, text, link, kind)
        sent_count += 1
        # Small delay to avoid hitting Telegram API rate limits
        await asyncio.sleep(0.1)
    return sent_count


async def push_notif(
    uid: str,
    kind: str,
    text: str,
    link: Optional[str] = None,
    marketing: bool = False,
    payload: Optional[dict] = None,
) -> bool:
    if marketing:
        cutoff = iso(now_utc() - timedelta(hours=24))
        today_count = await db.notifications.count_documents(
            {"user_id": uid, "marketing": True, "created_at": {"$gte": cutoff}}
        )
        if today_count >= 2:
            return False

    notif = {
        "id": new_id(),
        "user_id": uid,
        "kind": kind,
        "text": text,
        "link": link,
        "marketing": marketing,
        "created_at": iso(now_utc()),
        "read": False,
    }

    await db.notifications.insert_one(notif)
    notif.pop("_id", None)

    asyncio.create_task(notify_telegram(uid, text, link))
    asyncio.create_task(manager.send_to_user(uid, {"type": "notification", "data": notif, "payload": payload or {}}))

    return True


class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, uid: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.connections[uid].add(ws)

    async def disconnect(self, uid: str, ws: WebSocket) -> None:
        async with self._lock:
            self.connections[uid].discard(ws)
            if not self.connections[uid]:
                self.connections.pop(uid, None)

    async def send_to_user(self, uid: str, message: dict) -> None:
        conns = list(self.connections.get(uid, ()))
        for ws in conns:
            try:
                await ws.send_json(message)
            except Exception:
                async with self._lock:
                    self.connections[uid].discard(ws)

    async def broadcast_chat(self, uids: list[str], message: dict) -> None:
        for uid in uids:
            await self.send_to_user(uid, message)


manager = ConnectionManager()


class RateLimiter:
    def __init__(self, max_attempts: int = 10, window_sec: int = 300) -> None:
        self.max = max_attempts
        self.window = window_sec
        self.hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self.hits[key]
        cutoff = now - self.window
        self.hits[key] = [t for t in bucket if t > cutoff]
        if len(self.hits[key]) >= self.max:
            raise HTTPException(429, "Too many attempts. Try again later.")
        self.hits[key].append(now)


auth_limiter = RateLimiter(max_attempts=10, window_sec=300)
payment_limiter = RateLimiter(max_attempts=5, window_sec=60)


def rate_limit_auth(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    auth_limiter.check(f"auth:{ip}")


def rate_limit_payment(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    payment_limiter.check(f"payment:{ip}")
