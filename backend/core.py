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
    ADMIN_BOT_TOKEN,  # noqa: F401 - re-exported for `from core import ADMIN_BOT_TOKEN` callers
    TELEGRAM_BOT_TOKEN,  # noqa: F401 - re-exported for `from core import TELEGRAM_BOT_TOKEN` callers
    age_from_birth,
    compute_completeness,
    is_online,
    last_active_label,
    last_active_minutes,
    send_telegram_message,  # noqa: F401 - kept importable from core for existing callers
    send_telegram_message_status,
)

log = logging.getLogger("fidem")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "Fidem_Appbot")
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "fidem-tg")
ADMIN_BOT_WEBHOOK_SECRET = os.environ.get("ADMIN_BOT_WEBHOOK_SECRET", "fidem-admin-tg")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@fidem.uz")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# In production the admin password MUST come from the environment — the dev
# default below is public (audit docs, test fixtures) and grants full admin
# access. Mirrors the JWT_SECRET check in auth.py; accepts both ENV and
# ENVIRONMENT since deploy docs have historically disagreed on the var name.
_is_production = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "")).lower() == "production"
if not ADMIN_PASSWORD:
    if _is_production:
        raise ValueError(
            "ADMIN_PASSWORD must be set in production environment "
            "(the built-in default is publicly known and grants full admin access)"
        )
    ADMIN_PASSWORD = "Admin@123"  # Default for development only
    log.warning(
        "ADMIN_PASSWORD is not set - falling back to a well-known default "
        "('Admin@123'). Set ADMIN_PASSWORD in the environment before exposing "
        "this deployment to real users; the default is public (audit docs, "
        "test fixtures) and grants full admin access."
    )
PRICE_PREMIUM = int(os.environ.get("PRICE_PREMIUM_UZS", "79000"))
PRICE_VIP = int(os.environ.get("PRICE_VIP_UZS", "199000"))
PRICE_STANDARD = int(os.environ.get("PRICE_STANDARD_UZS", "34900"))
# 3-month prices match the existing "gift a subscription" 3-month prices in
# models.PLAN_GIFTS exactly (~15-16% off the 1-month rate) - a direct
# purchase and a self-gift must show the same number for the same plan.
# 12-month prices are new (~29-32% off) - the deeper discount standard SaaS
# annual plans use to reward commitment and lower churn. Both are fixed
# absolute prices, not derived from PRICE_*_UZS, so an env override of the
# monthly price does not silently double-discount the longer terms.
PLAN_PRICES = {
    "standard": {1: PRICE_STANDARD, 3: 89_000, 12: 299_000},
    "premium": {1: PRICE_PREMIUM, 3: 199_000, 12: 649_000},
    "vip": {1: PRICE_VIP, 3: 499_000, 12: 1_699_000},
}
# Premium sold by the day count: a cheap 1-day try, 15 days and a month.
PREMIUM_PERIODS = {
    1: int(os.environ.get("PRICE_PREMIUM_1D_UZS", "9900")),
    15: int(os.environ.get("PRICE_PREMIUM_15D_UZS", "49900")),
    30: int(os.environ.get("PRICE_PREMIUM_30D_UZS", str(PRICE_PREMIUM))),
}
# Temporarily lowered 9900 -> 4900 until the user base reaches ~500 (empty-
# market paywall pricing, see FIDEM strategic audit 2026-07). Override via env.
PRICE_CHAT_UNLOCK = int(os.environ.get("PRICE_CHAT_UNLOCK_UZS", "4900"))
CHAT_UNLOCK_COINS = int(os.environ.get("CHAT_UNLOCK_COINS", "100"))
CHAT_GUARANTEE_HOURS = int(os.environ.get("CHAT_GUARANTEE_HOURS", "48"))
# Free users may start this many NEW conversations per week at no cost — a
# freemium "taste" that seeds marketplace liquidity and converts better than a
# hard wall, without weakening the paid tiers (set to 0 to disable entirely).
FREE_WEEKLY_INITIATIONS = int(os.environ.get("FREE_WEEKLY_INITIATIONS", "1"))
PAID_PLANS = ("standard", "premium", "vip")
# Plans that unlock "who viewed / who saved me" (see PLANS.premium.perks in
# frontend/src/pages/Premium.jsx) — standard alone does not include it.
WHO_VIEWED_PLANS = ("premium", "vip")


async def payments_available() -> bool:
    """True when at least one way to pay is switched on (online payment keys or
    the admin's manual card top-up). While nothing can be bought, paywalls that
    hide people ("who viewed / liked me") would be a dead end, so they open."""
    from hamyon import hamyon_enabled
    from services import CLICK_MERCHANT_ID, CLICK_SECRET_KEY, CLICK_SERVICE_ID

    if hamyon_enabled():
        return True
    cfg = await db.settings.find_one({"id": "topup_config"}, {"_id": 0}) or {}
    return bool(cfg.get("p2p_enabled")) or bool(CLICK_SECRET_KEY and CLICK_MERCHANT_ID and CLICK_SERVICE_ID)
# Tiered PAID privacy (hidden mode is a monetization feature, free users
# cannot enable it):
#   standard  — your profile is invisible everywhere
#   premium+  — additionally, your visits are incognito: the people you view
#               never see you in "who viewed me" and get no notification
#   vip       — additionally, you may peek any locked photo once per profile
#               for 5 seconds (see /photo-peek)
INCOGNITO_PLANS = ("premium", "vip")


def mask_name(name: str) -> str:
    """First + last letter visible, middle replaced with a fixed run of
    asterisks (e.g. "Alisher" -> "A****r") — enough to feel like a real
    person in a teaser list without revealing who it is pre-unlock."""
    name = (name or "").strip()
    if len(name) <= 2:
        return (name[:1] + "***") if name else "***"
    return f"{name[0]}****{name[-1]}"


def get_webapp_url() -> str:
    return os.environ.get(
        "WEBAPP_URL",
        "https://fidem-frontend-production.up.railway.app",
    ).rstrip("/")


def get_admin_webapp_url() -> str:
    """Same deployed frontend, just opened straight at /admin - there is no
    separate admin build, only a separate bot pointing a Mini App button at
    this URL."""
    return f"{get_webapp_url()}/admin"


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


# ---- Launch promo: Premium is free for women ----
# Many more men than women use dating apps here; while the promo is on every
# woman gets all Premium features for free, so the gender balance (and the
# value of Premium for men) can grow. Admin switches it in the panel
# (settings.promo.women_free); WOMEN_FREE_PREMIUM=0 changes the default.
WOMEN_FREE_DEFAULT = os.environ.get("WOMEN_FREE_PREMIUM", "1").strip() != "0"
_PROMO_CACHE: dict = {"at": 0.0, "val": None}


async def women_free_active() -> bool:
    if _PROMO_CACHE["val"] is not None and time.time() - _PROMO_CACHE["at"] < 30:
        return _PROMO_CACHE["val"]
    doc = await db.settings.find_one({"id": "promo"}, {"_id": 0, "women_free": 1}) or {}
    val = bool(doc["women_free"]) if "women_free" in doc else WOMEN_FREE_DEFAULT
    _PROMO_CACHE.update(at=time.time(), val=val)
    return val


def reset_promo_cache() -> None:
    _PROMO_CACHE.update(at=0.0, val=None)


def apply_women_free(user: dict, active: bool) -> dict:
    """Give a selfie-verified woman Premium for this request while the promo
    is on. Verification is the price of the free plan: fake "women" (men or
    scammers behind someone else's photos) cannot pass a live selfie, so the
    promo never powers them. The stored plan is untouched: paid_plan keeps
    the real one for public badges, revenue and referral logic."""
    if active and user.get("gender") == "female" and user.get("plan", "free") not in PAID_PLANS:
        if user.get("verified_selfie"):
            user["paid_plan"] = user.get("plan", "free")
            user["plan"] = "premium"
            user["plan_source"] = "women_free"
        else:
            user["women_promo"] = "needs_selfie"
    return user


def selfie_required_to_write(user: dict) -> bool:
    """Women must pass the live selfie check before they can write: almost
    every scam on dating sites is a fake female profile in the chat."""
    return user.get("gender") == "female" and not user.get("verified_selfie") and not user.get("is_admin")


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
    if user.get("gender") == "female":
        apply_women_free(user, await women_free_active())
    return user


async def touch_active(uid: str) -> None:
    await db.users.update_one({"id": uid}, {"$set": {"last_active": iso(now_utc())}})


def own_photo_url(u: dict):
    """The photo as a host-independent path (/api/files/<id>), or None.

    Uploads used to be stored with the absolute URL of whatever backend domain
    served the app at that moment; after a domain change those stored URLs point
    at a dead host although the file itself is still ours. Returning only the
    path lets the client resolve it against the current backend. Anything that
    is not one of our own files (e.g. the stock/demo URLs the old seed data
    used) counts as "no photo"."""
    url = u.get("photo_url")
    if not isinstance(url, str):
        return None
    i = url.find("/api/files/")
    return url[i:] if i >= 0 else None


MAX_EXTRA_PHOTOS = 5  # besides the main photo


def own_photos(u: dict) -> list:
    """Extra gallery photos (host-independent paths), own files only, capped."""
    out = []
    for url in u.get("photos") or []:
        if isinstance(url, str) and "/api/files/" in url:
            path = url[url.find("/api/files/"):]
            if path not in out:
                out.append(path)
    return out[:MAX_EXTRA_PHOTOS]


def has_own_photo(u: dict) -> bool:
    return own_photo_url(u) is not None


def photo_required_missing(u: dict) -> bool:
    """True when this account must upload a photo before using the app.
    Admin accounts are exempt (same rule as the frontend gate)."""
    return not u.get("is_admin") and not has_own_photo(u)


def photo_kind(u: dict) -> str:
    """none / own / external - for diagnostics only (never logs the URL)."""
    url = u.get("photo_url")
    if not url:
        return "none"
    return "own" if own_photo_url(u) else "external"


def photo_is_public(u: dict) -> bool:
    """Profile photos are open by default; a user hides theirs with the
    "photo visible to everyone" privacy toggle (stored as photo_public=False)."""
    return bool(u.get("photo_public", True))


def strip_locked_photo(pub: dict) -> dict:
    """Remove photo_url from API payloads when the viewer has not unlocked the photo.

    Owners who opted in to a public photo (photo_public=True in their privacy
    settings) are treated as unlocked for everyone — the flag is normalized
    into photo_unlocked so the frontend needs no separate code path.
    """
    if pub.get("photo_public"):
        out = dict(pub)
        out["photo_unlocked"] = True
        return out
    if pub.get("photo_unlocked"):
        return pub
    out = dict(pub)
    out["photo_url"] = None
    out["photos"] = []
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
        "height_cm": u.get("height_cm") or 0,
        "weight_kg": u.get("weight_kg") or 0,
        "education": u.get("education", ""),
        "profession": u.get("profession", ""),
        "religion": u.get("religion", ""),
        "smoking": u.get("smoking") or "",
        "alcohol": u.get("alcohol") or "",
        "relocation": u.get("relocation"),
        "bio": u.get("bio", ""),
        "photo_url": own_photo_url(u),
        "photos": own_photos(u),
        "photo_verified": bool(u.get("photo_verified", False)),
        "verified_identity": u.get("verified_identity", False),
        "verified_selfie": u.get("verified_selfie", False),
        "verified_financial": u.get("verified_financial", False),
        # Public trust badge only. Raw GPS coordinates live in the separate
        # user_locations collection and are NEVER exposed via any user payload.
        "location_verified": bool(u.get("location_verified", False)),
        "last_active": la,
        "last_active_label": last_active_label(la),
        "last_active_minutes": last_active_minutes(la),
        "online": is_online(la),
        "completeness": u.get("completeness", compute_completeness(u)),
        "avg_response_min": u.get("avg_response_min"),
        "plan": u.get("plan", "free") if include_private else u.get("paid_plan", u.get("plan", "free")),
        "blocked": u.get("blocked", False),
        "prompts": u.get("prompts") or [],
        "big5_scores": u.get("big5_scores") or {},
        # Privacy settings: photo_public feeds strip_locked_photo (an opted-in
        # open photo renders for every viewer); hidden_profile keeps the user
        # out of candidate feeds / viewer lists (they can still browse).
        "photo_public": photo_is_public(u),
        "hidden_profile": bool(u.get("hidden_profile", False)),
        # 15s VIP video intro - public on the profile page by design.
        "video_intro_url": u.get("video_intro_url") or None,
    }
    if include_private:
        # Contact info, device/IP data and fraud-review fields - only for the
        # account owner (self) or an admin, never for other end users.
        out.update({
            # Wallet balance is the owner's business only — it used to sit in
            # the public payload, visible on every candidate/chat/leaderboard
            # row to anyone.
            "balance": u.get("balance", 0),
            "withdrawable_balance": int(u.get("referral_earnings_withdrawable", 0) or 0),
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
        "height_cm": u.get("height_cm") or 0,
        "education": u.get("education", ""),
        "profession": u.get("profession", ""),
        "bio": u.get("bio", ""),
        "photo_url": own_photo_url(u),
        "verified_selfie": u.get("verified_selfie", False),
        "verified_financial": u.get("verified_financial", False),
        "location_verified": bool(u.get("location_verified", False)),
        "last_active": la,
        "last_active_label": last_active_label(la),
        "online": is_online(la),
        "plan": u.get("paid_plan", u.get("plan", "free")),
        "blocked": u.get("blocked", False),
        "photo_public": photo_is_public(u),
    }


async def mark_telegram_unreachable(chat_id) -> None:
    """Telegram said this chat is closed to the bot (blocked / account gone).
    Flag it everywhere we keep that chat, so nudges and broadcasts skip it
    instead of failing (and logging a 403) on every pass. Cleared on /start."""
    ids = [chat_id, str(chat_id)]
    try:
        ids.append(int(chat_id))
    except (TypeError, ValueError):
        pass
    await db.users.update_many(
        {"telegram_id": {"$in": ids}},
        {"$set": {"telegram_unreachable": True, "telegram_unreachable_at": iso(now_utc())}},
    )
    await db.bot_starts.update_many({"chat_id": {"$in": ids}}, {"$set": {"unreachable": True}})


async def notify_telegram(uid: str, text: str, link: Optional[str] = None, kind: str = "general") -> None:
    """Send Telegram notification with user preference check and rate limiting."""
    user = await db.users.find_one(
        {"id": uid}, {"telegram_id": 1, "notification_prefs": 1, "telegram_unreachable": 1, "_id": 0}
    )
    if not user or not user.get("telegram_id"):
        return
    # Telegram already told us this chat is closed to the bot (blocked it /
    # deleted the account) - every further attempt is a wasted API call and
    # a 403 in the logs. Cleared again when the user /start's the bot or
    # signs back in through Telegram.
    if user.get("telegram_unreachable"):
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

        status = await send_telegram_message_status(
            int(user["telegram_id"]),
            text,
            reply_markup=reply_markup,
        )
        sent = status == "sent"
        if status == "unreachable":
            await db.users.update_one(
                {"id": uid},
                {"$set": {"telegram_unreachable": True, "telegram_unreachable_at": iso(now_utc())}},
            )

        # Only mark as sent (and start the cooldown window) if it actually
        # went out. send_telegram_message returning False (bad chat_id, user
        # blocked the bot, malformed payload...) used to be treated exactly
        # like a success here, so a real delivery failure both stayed
        # invisible AND blocked the next 20 minutes of that kind's retries.
        if sent:
            await db.users.update_one(
                {"id": uid},
                {"$set": {last_notif_key: iso(now_utc())}}
            )
        elif status == "failed":
            log.warning(f"telegram notify: send failed for user {uid} kind={kind}")
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


async def log_admin_action(admin_id: str, action: str, target_id: Optional[str] = None, details: Optional[dict] = None) -> None:
    """Audit trail for every admin mutation: who did what, to whom, when.
    Fire-and-forget from the caller's perspective — a logging failure must
    never block the admin action itself, so this never raises."""
    try:
        from models import new_id
        await db.admin_audit_log.insert_one({
            "id": new_id(),
            "admin_id": admin_id,
            "action": action,
            "target_id": target_id,
            "details": details or {},
            "at": iso(now_utc()),
        })
    except Exception:
        log.warning("admin audit log write failed", exc_info=True)


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

    # kind must be forwarded - notify_telegram's 20-min cooldown is keyed
    # per-kind (last_notif_{kind}). Without this, every push_notif call
    # silently fell back to notify_telegram's own "general" default, so ALL
    # notification kinds (referral, gift, boost, marketing/announcements...)
    # shared one Telegram cooldown bucket: any Telegram send of any kind
    # blocked every other kind's Telegram delivery for the next 20 minutes,
    # while the in-app notification (this insert, above) still went through
    # every time - explaining "it showed in the app but the bot never sent it".
    asyncio.create_task(notify_telegram(uid, text, link, kind=kind))
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
        fresh = [t for t in bucket if t > cutoff]
        if len(fresh) >= self.max:
            # Don't write the trimmed-but-still-over-limit bucket back — keep
            # the caller's rejected attempt out of the window so a client that
            # stops retrying ages out normally instead of freezing the count.
            self.hits[key] = fresh
            raise HTTPException(429, "Too many attempts. Try again later.")
        fresh.append(now)
        self.hits[key] = fresh

    def gc(self) -> None:
        """Drop buckets that are now empty (client IP idle past the window).
        Without this, self.hits keeps one entry per distinct IP forever —
        an unbounded, never-shrinking dict is a slow memory leak on a
        long-lived process serving many unique clients over time."""
        now = time.monotonic()
        cutoff = now - self.window
        dead = [k for k, bucket in self.hits.items() if not any(t > cutoff for t in bucket)]
        for k in dead:
            del self.hits[k]


# Uzbek mobile carriers put many subscribers behind one public IP (CGNAT),
# so a tight per-IP limit blocks real people during an ad wave. Per-account
# keys carry the tight limits; per-IP buckets only stop floods.
auth_limiter = RateLimiter(max_attempts=10, window_sec=300)          # per IP + email
auth_ip_limiter = RateLimiter(max_attempts=120, window_sec=300)      # per IP (flood guard)
payment_limiter = RateLimiter(max_attempts=5, window_sec=60)         # per account
verification_limiter = RateLimiter(max_attempts=5, window_sec=600)   # per account


def _client_ip(request: Request) -> str:
    ip = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # The first entry in X-Forwarded-For is whatever the CONNECTING
        # CLIENT claims (a client can send this header directly, with any
        # value it likes, unless a trusted proxy overwrites it). Proxies that
        # relay the header instead append to it, so the rightmost entry is
        # the one *our* edge proxy actually observed — the only hop that
        # can't be spoofed by the caller. Using [0] let anyone bypass rate
        # limiting for free by sending a fresh fake X-Forwarded-For on every
        # request.
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            ip = parts[-1]
    return ip


def rate_limit_auth(request: Request, account: str = "") -> None:
    ip = _client_ip(request)
    auth_ip_limiter.check(f"authip:{ip}")
    auth_limiter.check(f"auth:{ip}:{(account or '').strip().lower()}")


def rate_limit_payment(request: Request, uid: str = "") -> None:
    payment_limiter.check(f"payment:{uid or _client_ip(request)}")


def rate_limit_verification(request: Request, uid: str = "") -> None:
    # /verification/request triggers a Gemini/Claude vision API call per
    # submission - unlimited submissions is an unbounded-cost / provider-DoS
    # vector, not just a UX nuisance.
    verification_limiter.check(f"verification:{uid or _client_ip(request)}")


async def rate_limiter_gc_loop() -> None:
    """Runs for the life of the process; keeps the in-memory rate-limit
    tables from growing forever on a long-lived server with many unique
    visitor IPs over time."""
    while True:
        await asyncio.sleep(900)
        try:
            auth_limiter.gc()
            auth_ip_limiter.gc()
            payment_limiter.gc()
            verification_limiter.gc()
        except Exception:
            log.warning("rate limiter gc failed", exc_info=True)
