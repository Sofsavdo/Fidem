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
from fastapi import HTTPException, Request, WebSocket
from motor.motor_asyncio import AsyncIOMotorClient

from models import new_id, now_utc
from services import (
    age_from_birth,
    compute_completeness,
    is_online,
    last_active_label,
    send_telegram_message,
)

log = logging.getLogger("fidem")

# ---------- Env / DB ----------
client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "Fidem_Appbot")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "fidem-tg")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@fidem.uz")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")
PRICE_PREMIUM = int(os.environ.get("PRICE_PREMIUM_UZS", "79000"))
PRICE_VIP = int(os.environ.get("PRICE_VIP_UZS", "199000"))
PRICE_SUPER = int(os.environ.get("PRICE_SUPER_APPLICATION_UZS", "15000"))


# ---------- Helpers ----------
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


async def get_user(uid: str) -> dict:
    user = await db.users.find_one({"id": uid}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    plan_until = user.get("plan_until")
    if plan_until and user.get("plan") in ("premium", "vip"):
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


def user_public(u: dict) -> dict:
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
        "children_count": u.get("children_count", 0),
        "height_cm": u.get("height_cm", 170),
        "weight_kg": u.get("weight_kg", 70),
        "education": u.get("education", ""),
        "profession": u.get("profession", ""),
        "religion": u.get("religion", ""),
        "bio": u.get("bio", ""),
        "photo_url": u.get("photo_url"),
        "verified_identity": u.get("verified_identity", False),
        "verified_selfie": u.get("verified_selfie", False),
        "verified_financial": u.get("verified_financial", False),
        "last_active": la,
        "last_active_label": last_active_label(la),
        "online": is_online(la),
        "completeness": u.get("completeness", compute_completeness(u)),
        "avg_response_min": u.get("avg_response_min"),
        "plan": u.get("plan", "free"),
        "balance": u.get("balance", 0),
        "withdrawable_balance": int(u.get("withdrawable_balance", 0) or 0),
        "blocked": u.get("blocked", False),
        "prompts": u.get("prompts") or [],
        "big5_scores": u.get("big5_scores") or {},
    }


async def notify_telegram(uid: str, text: str, link: Optional[str] = None) -> None:
    user = await db.users.find_one({"id": uid}, {"telegram_id": 1, "_id": 0})
    if user and user.get("telegram_id"):
        try:
            reply_markup = None
            if link:
                base = os.environ.get("CLICK_RETURN_URL", "").split("/payment/return")[0] or ""
                full = link if link.startswith("http") else f"{base}{link}" if base else None
                if full:
                    reply_markup = {"inline_keyboard": [[{"text": "🔗 Ochish", "url": full}]]}
            await send_telegram_message(int(user["telegram_id"]), text, reply_markup=reply_markup)
        except Exception as e:
            log.warning(f"telegram notify failed: {e}")


async def push_notif(uid: str, kind: str, text: str, link: Optional[str] = None,
                     marketing: bool = False, payload: Optional[dict] = None) -> bool:
    """Persist + Telegram-DM a notification + push via WebSocket. Returns False if marketing cap hit."""
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
    # WebSocket push (best-effort)
    asyncio.create_task(manager.send_to_user(uid, {"type": "notification", "data": notif, "payload": payload or {}}))
    return True


# ---------- WebSocket Connection Manager ----------
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
                # Best-effort; drop dead connections
                async with self._lock:
                    self.connections[uid].discard(ws)

    async def broadcast_chat(self, uids: list[str], message: dict) -> None:
        for uid in uids:
            await self.send_to_user(uid, message)


manager = ConnectionManager()


# ---------- Rate Limiter ----------
class RateLimiter:
    """Sliding-window in-memory limiter. Not for multi-instance prod but fine for MVP."""
    def __init__(self, max_attempts: int = 10, window_sec: int = 300) -> None:
        self.max = max_attempts
        self.window = window_sec
        self.hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self.hits[key]
        # Drop old hits
        cutoff = now - self.window
        self.hits[key] = [t for t in bucket if t > cutoff]
        if len(self.hits[key]) >= self.max:
            raise HTTPException(429, "Too many attempts. Try again later.")
        self.hits[key].append(now)


auth_limiter = RateLimiter(max_attempts=10, window_sec=300)


def rate_limit_auth(request: Request) -> None:
    """Apply rate limit per client IP for auth endpoints."""
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    auth_limiter.check(f"auth:{ip}")
