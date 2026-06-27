"""FIDEM backend — Telegram Mini App matchmaking platform."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import bcrypt
from dotenv import load_dotenv
from fastapi import Body, Depends, FastAPI, File, Form, HTTPException, Header, Query, Request, UploadFile, APIRouter
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import Response

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

from auth import (
    create_token,
    get_current_admin,
    get_current_user_id,
    optional_user_id,
    validate_telegram_init_data,
)
from storage import init_storage, put_object, get_object, MIME
from models import (
    AdminUpdateUserRequest,
    AuthResponse,
    CandidateCard,
    CandidateFilter,
    ChatOut,
    CreatePaymentRequest,
    GIFT_EMOJI,
    GIFT_PRICES,
    LoginRequest,
    MessageFilters,
    MessageOut,
    NotificationOut,
    OnboardingProfile,
    PaymentOut,
    PhotoUnlockDecision,
    PhotoUnlockRequest,
    RegisterRequest,
    ReportRequest,
    SaveRequest,
    SendGiftRequest,
    SendMessageRequest,
    TelegramAuthRequest,
    UpdateProfileRequest,
    UserPublic,
    VerificationRequest,
    new_id,
    now_utc,
)
from services import (
    age_from_birth,
    click_md5,
    click_pay_link,
    compute_completeness,
    compute_match,
    is_online,
    last_active_label,
    send_telegram_message,
    verify_click_sign,
    CLICK_SECRET_KEY,
    CLICK_SERVICE_ID,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("fidem")

# ---------- Database ----------
mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@fidem.uz")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Admin@123")
PRICE_PREMIUM = int(os.environ.get("PRICE_PREMIUM_UZS", "79000"))
PRICE_VIP = int(os.environ.get("PRICE_VIP_UZS", "199000"))
PRICE_SUPER = int(os.environ.get("PRICE_SUPER_APPLICATION_UZS", "15000"))

# ---------- FastAPI ----------
app = FastAPI(title="FIDEM API")
api = APIRouter(prefix="/api")


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
    # Subscription expiry check
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
        "blocked": u.get("blocked", False),
    }


async def notify_telegram(uid: str, text: str) -> None:
    user = await db.users.find_one({"id": uid}, {"telegram_id": 1, "_id": 0})
    if user and user.get("telegram_id"):
        try:
            await send_telegram_message(int(user["telegram_id"]), text)
        except Exception as e:
            log.warning(f"telegram notify failed: {e}")


async def push_notif(uid: str, kind: str, text: str, link: Optional[str] = None, marketing: bool = False) -> bool:
    """Persist + Telegram-DM a notification. If marketing=True, enforce daily cap of 2."""
    if marketing:
        from datetime import timedelta as _td
        cutoff = iso(now_utc() - _td(hours=24))
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
    asyncio.create_task(notify_telegram(uid, text))
    return True


# ---------- Health ----------
@api.get("/")
async def health():
    return {"status": "ok", "service": "fidem"}


# ---------- Auth ----------
@api.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest):
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    uid = new_id()
    doc = {
        "id": uid,
        "email": req.email.lower(),
        "password_hash": hash_pw(req.password),
        "name": req.name or req.email.split("@")[0],
        "created_at": iso(now_utc()),
        "last_active": iso(now_utc()),
        "onboarded": False,
        "verified_identity": False,
        "verified_selfie": False,
        "verified_financial": False,
        "plan": "free",
        "balance": 0,
        "blocked": False,
    }
    await db.users.insert_one(doc)
    return AuthResponse(token=create_token(uid), user_id=uid, onboarded=False)


@api.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not check_pw(req.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    is_admin = bool(user.get("is_admin", False))
    return AuthResponse(
        token=create_token(user["id"], is_admin=is_admin),
        user_id=user["id"],
        is_admin=is_admin,
        onboarded=user.get("onboarded", False),
    )


@api.post("/auth/telegram", response_model=AuthResponse)
async def auth_telegram(req: TelegramAuthRequest):
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(500, "Bot token not configured")
    tg_user = validate_telegram_init_data(req.init_data, TELEGRAM_BOT_TOKEN)
    tg_id = str(tg_user.get("id"))
    if not tg_id:
        raise HTTPException(400, "No telegram user id")
    existing = await db.users.find_one({"telegram_id": tg_id})
    if existing:
        await db.users.update_one({"id": existing["id"]}, {"$set": {"last_active": iso(now_utc())}})
        return AuthResponse(
            token=create_token(existing["id"], is_admin=existing.get("is_admin", False)),
            user_id=existing["id"],
            is_admin=existing.get("is_admin", False),
            onboarded=existing.get("onboarded", False),
        )
    uid = new_id()
    name = (tg_user.get("first_name", "") + " " + tg_user.get("last_name", "")).strip() or f"User{tg_id[-4:]}"
    doc = {
        "id": uid,
        "telegram_id": tg_id,
        "telegram_username": tg_user.get("username"),
        "telegram_language": tg_user.get("language_code", "uz"),
        "name": name,
        "created_at": iso(now_utc()),
        "last_active": iso(now_utc()),
        "onboarded": False,
        "verified_identity": True,  # Telegram-verified
        "verified_selfie": False,
        "verified_financial": False,
        "plan": "free",
        "balance": 0,
        "blocked": False,
    }
    await db.users.insert_one(doc)
    return AuthResponse(token=create_token(uid), user_id=uid, onboarded=False)


@api.get("/auth/me")
async def me(uid: str = Depends(get_current_user_id)):
    user = await get_user(uid)
    pub = user_public(user)
    pub["email"] = user.get("email")
    pub["telegram_id"] = user.get("telegram_id")
    pub["telegram_username"] = user.get("telegram_username")
    pub["onboarded"] = user.get("onboarded", False)
    pub["is_admin"] = user.get("is_admin", False)
    pub["message_filters"] = user.get("message_filters", {})
    pub["birth_date"] = user.get("birth_date")
    pub["country"] = user.get("country")
    pub["search_region"] = user.get("search_region")
    pub["search_age_min"] = user.get("search_age_min", 18)
    pub["search_age_max"] = user.get("search_age_max", 60)
    pub["search_gender"] = user.get("search_gender")
    pub["looking_for"] = user.get("looking_for")
    pub["language"] = user.get("language", "uz")
    return pub


# ---------- Onboarding / Profile ----------
@api.post("/profile/onboard")
async def onboard(req: OnboardingProfile, uid: str = Depends(get_current_user_id)):
    user = await get_user(uid)
    update = req.model_dump()
    update["onboarded"] = True
    update["last_active"] = iso(now_utc())
    # write-once fields locked after onboarding
    await db.users.update_one({"id": uid}, {"$set": update})
    fresh = await get_user(uid)
    completeness = compute_completeness(fresh)
    await db.users.update_one({"id": uid}, {"$set": {"completeness": completeness}})
    return {"ok": True, "completeness": completeness}


@api.patch("/profile")
async def update_profile(req: UpdateProfileRequest, uid: str = Depends(get_current_user_id)):
    user = await get_user(uid)
    update = {k: v for k, v in req.model_dump().items() if v is not None}
    # write-once fields require re-verify
    locked = {"height_cm", "weight_kg", "marital_status", "has_children", "children_count"}
    if user.get("onboarded") and any(k in update for k in locked):
        update["verified_selfie"] = False
        update["pending_admin_review"] = True
    await db.users.update_one({"id": uid}, {"$set": update})
    fresh = await get_user(uid)
    completeness = compute_completeness(fresh)
    await db.users.update_one({"id": uid}, {"$set": {"completeness": completeness}})
    return {"ok": True, "completeness": completeness}


@api.patch("/profile/language")
async def set_language(language: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    if language not in ("uz", "ru", "en"):
        raise HTTPException(400, "Unsupported language")
    await db.users.update_one({"id": uid}, {"$set": {"language": language}})
    return {"ok": True}


@api.patch("/profile/filters")
async def set_filters(req: MessageFilters, uid: str = Depends(get_current_user_id)):
    await db.users.update_one({"id": uid}, {"$set": {"message_filters": req.model_dump()}})
    return {"ok": True}


# ---------- Candidates ----------
@api.get("/candidates")
async def candidates(
    age_min: Optional[int] = None,
    age_max: Optional[int] = None,
    region: Optional[str] = None,
    marital_status: Optional[str] = None,
    has_children: Optional[bool] = None,
    height_min: Optional[int] = None,
    height_max: Optional[int] = None,
    verified_only: bool = False,
    financial_only: bool = False,
    sort: str = "match",
    limit: int = 30,
    uid: str = Depends(get_current_user_id),
):
    me_doc = await get_user(uid)
    if not me_doc.get("onboarded"):
        return []
    await touch_active(uid)

    # Target opposite gender to my search_gender
    query: dict = {"id": {"$ne": uid}, "onboarded": True, "blocked": {"$ne": True}}
    if me_doc.get("search_gender"):
        query["gender"] = me_doc["search_gender"]
    if region:
        query["region"] = region
    if marital_status:
        query["marital_status"] = marital_status
    if has_children is not None:
        query["has_children"] = has_children
    if verified_only:
        query["verified_selfie"] = True
    if financial_only:
        query["verified_financial"] = True

    cursor = db.users.find(query, {"_id": 0, "password_hash": 0}).limit(500)
    docs = await cursor.to_list(length=500)

    # filter by age
    a_lo = age_min or me_doc.get("search_age_min", 18)
    a_hi = age_max or me_doc.get("search_age_max", 60)
    enriched: list[dict] = []
    photo_unlocks = await db.photo_unlocks.find(
        {"requester_id": uid, "approved": True}, {"_id": 0}
    ).to_list(2000)
    unlocked_set = {p["target_id"] for p in photo_unlocks}

    for d in docs:
        age = age_from_birth(d.get("birth_date", "2000-01-01"))
        if age < a_lo or age > a_hi:
            continue
        if height_min and d.get("height_cm", 0) < height_min:
            continue
        if height_max and d.get("height_cm", 999) > height_max:
            continue
        score, reasons = compute_match(me_doc, d)
        pub = user_public(d)
        pub["match_score"] = score
        pub["match_reasons"] = reasons
        pub["photo_unlocked"] = d["id"] in unlocked_set
        pub["can_message"] = candidate_can_message(d, me_doc)
        enriched.append(pub)

    if sort == "match":
        enriched.sort(key=lambda x: (-x["match_score"], -x["completeness"]))
    elif sort == "active":
        enriched.sort(key=lambda x: (not x["online"], x["last_active"]), reverse=False)
    elif sort == "new":
        enriched.sort(key=lambda x: x["last_active"], reverse=True)
    return enriched[:limit]


def candidate_can_message(target: dict, sender: dict) -> bool:
    """Check whether sender passes target's message filters."""
    f = target.get("message_filters") or {}
    if not f:
        return True
    age = age_from_birth(sender.get("birth_date", "2000-01-01"))
    if age < f.get("age_min", 18) or age > f.get("age_max", 60):
        return False
    if f.get("region") and f["region"] != sender.get("region"):
        return False
    if f.get("marital_status") and f["marital_status"] != sender.get("marital_status"):
        return False
    if f.get("has_children") is not None and f["has_children"] != sender.get("has_children"):
        return False
    if f.get("height_min") and sender.get("height_cm", 0) < f["height_min"]:
        return False
    if f.get("height_max") and sender.get("height_cm", 999) > f["height_max"]:
        return False
    if f.get("weight_min") and sender.get("weight_kg", 0) < f["weight_min"]:
        return False
    if f.get("weight_max") and sender.get("weight_kg", 999) > f["weight_max"]:
        return False
    if f.get("require_verified") and not sender.get("verified_selfie"):
        return False
    if f.get("require_financial") and not sender.get("verified_financial"):
        return False
    return True


@api.get("/candidates/{target_id}")
async def candidate_detail(target_id: str, uid: str = Depends(get_current_user_id)):
    if target_id == uid:
        raise HTTPException(400, "Cannot view self as candidate")
    target = await get_user(target_id)
    me_doc = await get_user(uid)
    # log view
    await db.profile_views.update_one(
        {"viewer_id": uid, "target_id": target_id},
        {"$set": {"viewer_id": uid, "target_id": target_id, "at": iso(now_utc())}},
        upsert=True,
    )
    score, reasons = compute_match(me_doc, target)
    pub = user_public(target)
    pub["match_score"] = score
    pub["match_reasons"] = reasons
    # photo unlock state
    unlock = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": target_id}, {"_id": 0}
    )
    pub["photo_unlocked"] = bool(unlock and unlock.get("approved"))
    pub["photo_unlock_status"] = unlock.get("status") if unlock else "none"
    pub["can_message"] = candidate_can_message(target, me_doc)
    # interested_in_me notification
    asyncio.create_task(push_notif(target_id, "view", f"Profilingizni {me_doc.get('name','')} ko'rdi"))
    return pub


# ---------- Photo Unlock ----------
@api.post("/photo-unlock/request")
async def request_photo_unlock(req: PhotoUnlockRequest, uid: str = Depends(get_current_user_id)):
    existing = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": req.target_user_id}
    )
    if existing and existing.get("approved"):
        return {"status": "approved"}
    if existing and existing.get("status") == "pending":
        return {"status": "pending"}
    doc = {
        "id": new_id(),
        "requester_id": uid,
        "target_id": req.target_user_id,
        "status": "pending",
        "approved": False,
        "created_at": iso(now_utc()),
    }
    await db.photo_unlocks.replace_one(
        {"requester_id": uid, "target_id": req.target_user_id}, doc, upsert=True
    )
    me_doc = await get_user(uid)
    await push_notif(
        req.target_user_id, "photo_request",
        f"{me_doc.get('name','')} rasmingizni ko'rishni so'rayapti"
    )
    return {"status": "pending"}


@api.get("/photo-unlock/requests")
async def list_photo_unlock_requests(uid: str = Depends(get_current_user_id)):
    rows = await db.photo_unlocks.find({"target_id": uid, "status": "pending"}, {"_id": 0}).to_list(200)
    enriched = []
    for r in rows:
        u = await db.users.find_one({"id": r["requester_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            enriched.append({"request": r, "requester": user_public(u)})
    return enriched


@api.post("/photo-unlock/decide")
async def decide_photo_unlock(req: PhotoUnlockDecision, uid: str = Depends(get_current_user_id)):
    row = await db.photo_unlocks.find_one({"id": req.request_id})
    if not row or row.get("target_id") != uid:
        raise HTTPException(404, "Request not found")
    new_status = "approved" if req.approve else "rejected"
    await db.photo_unlocks.update_one(
        {"id": req.request_id},
        {"$set": {"status": new_status, "approved": req.approve, "decided_at": iso(now_utc())}},
    )
    if req.approve:
        await push_notif(row["requester_id"], "photo_grant", "Rasm ochildi — endi ko'rishingiz mumkin")
    return {"ok": True, "status": new_status}


# ---------- Save / Like ----------
@api.post("/saved")
async def save_user(req: SaveRequest, uid: str = Depends(get_current_user_id)):
    if req.user_id == uid:
        raise HTTPException(400, "Cannot save self")
    await db.saved.update_one(
        {"owner_id": uid, "target_id": req.user_id},
        {"$set": {"owner_id": uid, "target_id": req.user_id, "at": iso(now_utc())}},
        upsert=True,
    )
    me_doc = await get_user(uid)
    await push_notif(req.user_id, "saved", f"{me_doc.get('name','')} sizni saqladi")
    return {"ok": True}


@api.delete("/saved/{target_id}")
async def unsave_user(target_id: str, uid: str = Depends(get_current_user_id)):
    await db.saved.delete_one({"owner_id": uid, "target_id": target_id})
    return {"ok": True}


@api.get("/saved/mine")
async def saved_mine(uid: str = Depends(get_current_user_id)):
    rows = await db.saved.find({"owner_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    for r in rows:
        u = await db.users.find_one({"id": r["target_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            result.append(user_public(u))
    return result


@api.get("/saved/by-others")
async def saved_by_others(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    rows = await db.saved.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    for r in rows:
        u = await db.users.find_one({"id": r["owner_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["region"] = "•••"
                pub["locked"] = True
            result.append(pub)
    return result


@api.get("/saved/viewers")
async def viewers(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    rows = await db.profile_views.find({"target_id": uid}, {"_id": 0}).sort("at", -1).to_list(500)
    result = []
    seen = set()
    for r in rows:
        vid = r["viewer_id"]
        if vid in seen or vid == uid:
            continue
        seen.add(vid)
        u = await db.users.find_one({"id": vid}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["region"] = "•••"
                pub["locked"] = True
            result.append(pub)
    return result


@api.get("/saved/interested")
async def interested_in_me(uid: str = Depends(get_current_user_id)):
    """Users who saved me OR sent application/message to me."""
    me_doc = await get_user(uid)
    is_premium = me_doc.get("plan") in ("premium", "vip")
    saved_rows = await db.saved.find({"target_id": uid}, {"_id": 0}).to_list(500)
    msg_rows = await db.messages.find({"to_user_id": uid}, {"_id": 0}).to_list(500)
    user_ids = {r["owner_id"] for r in saved_rows} | {m["from_user_id"] for m in msg_rows}
    user_ids.discard(uid)
    result = []
    for vid in user_ids:
        u = await db.users.find_one({"id": vid}, {"_id": 0, "password_hash": 0})
        if u:
            pub = user_public(u)
            if not is_premium:
                pub["name"] = "•••••"
                pub["photo_url"] = None
                pub["locked"] = True
            result.append(pub)
    return result


# ---------- Messages ----------
@api.get("/messages/chats")
async def list_chats(uid: str = Depends(get_current_user_id)):
    pipeline = [
        {"$match": {"$or": [{"from_user_id": uid}, {"to_user_id": uid}]}},
        {"$sort": {"created_at": -1}},
        {"$group": {"_id": "$chat_id", "last": {"$first": "$$ROOT"}}},
        {"$sort": {"last.created_at": -1}},
    ]
    cursor = db.messages.aggregate(pipeline)
    items = []
    async for row in cursor:
        last = row["last"]
        other_id = last["to_user_id"] if last["from_user_id"] == uid else last["from_user_id"]
        u = await db.users.find_one({"id": other_id}, {"_id": 0, "password_hash": 0})
        if not u:
            continue
        # determine status
        status = last.get("status", "chat")
        # unread
        unread = await db.messages.count_documents(
            {"chat_id": row["_id"], "to_user_id": uid, "read": {"$ne": True}}
        )
        items.append({
            "chat_id": row["_id"],
            "other": user_public(u),
            "last_message": {
                "id": last["id"], "text": last["text"],
                "kind": last.get("kind", "text"),
                "from_user_id": last["from_user_id"],
                "to_user_id": last["to_user_id"],
                "created_at": parse_dt(last["created_at"]),
            },
            "unread": unread,
            "status": status,
        })
    return items


@api.get("/messages/applications")
async def list_applications(uid: str = Depends(get_current_user_id)):
    """First-message-from-other awaiting response."""
    rows = await db.applications.find({"to_user_id": uid, "status": "pending"}, {"_id": 0}).to_list(200)
    enriched = []
    for r in rows:
        u = await db.users.find_one({"id": r["from_user_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            enriched.append({"application": r, "from_user": user_public(u)})
    return enriched


@api.post("/messages/applications/{app_id}/decide")
async def decide_application(app_id: str, approve: bool = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    row = await db.applications.find_one({"id": app_id, "to_user_id": uid})
    if not row:
        raise HTTPException(404, "Application not found")
    await db.applications.update_one({"id": app_id}, {"$set": {"status": "approved" if approve else "rejected"}})
    if approve:
        await push_notif(row["from_user_id"], "match", "Sizning murojaatingiz qabul qilindi 🎉")
    return {"ok": True}


@api.get("/messages/{chat_id}")
async def chat_history(chat_id: str, uid: str = Depends(get_current_user_id)):
    a, b = chat_id.split("_", 1)
    if uid not in (a, b):
        raise HTTPException(403, "Not your chat")
    rows = await db.messages.find({"chat_id": chat_id}, {"_id": 0}).sort("created_at", 1).to_list(500)
    await db.messages.update_many({"chat_id": chat_id, "to_user_id": uid}, {"$set": {"read": True}})
    for r in rows:
        r["created_at"] = parse_dt(r["created_at"])
    return rows


@api.post("/messages/send")
async def send_message(req: SendMessageRequest, uid: str = Depends(get_current_user_id)):
    if req.to_user_id == uid:
        raise HTTPException(400, "Cannot message self")
    sender = await get_user(uid)
    target = await get_user(req.to_user_id)
    cid = chat_id_for(uid, req.to_user_id)
    existing_msgs = await db.messages.count_documents({"chat_id": cid})
    can_msg = candidate_can_message(target, sender)
    is_first = existing_msgs == 0
    kind = "super" if req.is_super else "text"
    status = "chat"

    if req.is_super:
        if sender.get("balance", 0) < PRICE_SUPER:
            raise HTTPException(402, "Insufficient balance for super application")
        await db.users.update_one({"id": uid}, {"$inc": {"balance": -PRICE_SUPER}})
        status = "application"
    elif not can_msg:
        raise HTTPException(403, "You don't pass recipient's filters. Use super application.")
    elif is_first:
        # First-time application even if pass filters - record application
        status = "application"

    msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "text": req.text,
        "kind": kind,
        "created_at": iso(now_utc()),
        "read": False,
        "status": status,
    }
    await db.messages.insert_one(msg)
    msg.pop("_id", None)
    if is_first or req.is_super:
        await db.applications.update_one(
            {"from_user_id": uid, "to_user_id": req.to_user_id},
            {"$set": {
                "id": new_id(), "from_user_id": uid, "to_user_id": req.to_user_id,
                "is_super": req.is_super, "status": "pending",
                "created_at": iso(now_utc()), "text": req.text,
            }},
            upsert=True,
        )
    # ---- Response time tracking: if this message is a reply, record delta ----
    if not is_first:
        last_incoming = await db.messages.find_one(
            {"chat_id": cid, "to_user_id": uid},
            sort=[("created_at", -1)],
            projection={"_id": 0, "created_at": 1, "from_user_id": 1},
        )
        if last_incoming and last_incoming.get("from_user_id") == req.to_user_id:
            try:
                delta_min = (now_utc() - parse_dt(last_incoming["created_at"])).total_seconds() / 60.0
                if 0 < delta_min < 7 * 24 * 60:  # cap at 1 week
                    samples = sender.get("response_samples", []) or []
                    samples.append(round(delta_min, 1))
                    samples = samples[-20:]
                    avg = round(sum(samples) / len(samples))
                    await db.users.update_one(
                        {"id": uid},
                        {"$set": {"response_samples": samples, "avg_response_min": avg}},
                    )
            except Exception:
                pass
    await push_notif(req.to_user_id, "message", f"Yangi xabar: {sender.get('name','')}")
    msg["created_at"] = parse_dt(msg["created_at"])
    return msg


@api.post("/messages/block")
async def block_user(req: SaveRequest, uid: str = Depends(get_current_user_id)):
    await db.blocks.update_one(
        {"owner_id": uid, "target_id": req.user_id},
        {"$set": {"owner_id": uid, "target_id": req.user_id, "at": iso(now_utc())}},
        upsert=True,
    )
    return {"ok": True}


@api.post("/messages/report")
async def report_user(req: ReportRequest, uid: str = Depends(get_current_user_id)):
    await db.reports.insert_one({
        "id": new_id(),
        "reporter_id": uid,
        "target_id": req.user_id,
        "reason": req.reason,
        "created_at": iso(now_utc()),
        "status": "open",
    })
    return {"ok": True}


# ---------- Gifts ----------
@api.post("/gifts/send")
async def send_gift(req: SendGiftRequest, uid: str = Depends(get_current_user_id)):
    price = GIFT_PRICES.get(req.gift_kind)
    if not price:
        raise HTTPException(400, "Invalid gift")
    sender = await get_user(uid)
    if sender.get("balance", 0) < price:
        raise HTTPException(402, "Insufficient balance")
    target = await get_user(req.to_user_id)
    await db.users.update_one({"id": uid}, {"$inc": {"balance": -price, "gifts_sent_total": price}})
    await db.users.update_one({"id": req.to_user_id}, {"$inc": {"gifts_received_total": price}})
    gift = {
        "id": new_id(),
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "kind": req.gift_kind,
        "price": price,
        "created_at": iso(now_utc()),
    }
    await db.gifts.insert_one(gift)
    # also drop a chat message
    cid = chat_id_for(uid, req.to_user_id)
    gift_msg = {
        "id": new_id(),
        "chat_id": cid,
        "from_user_id": uid,
        "to_user_id": req.to_user_id,
        "text": f"{GIFT_EMOJI[req.gift_kind]} Sovg'a yuborildi",
        "kind": "gift",
        "meta": {"gift": req.gift_kind, "price": price},
        "created_at": iso(now_utc()),
        "read": False,
    }
    await db.messages.insert_one(gift_msg)
    gift_msg.pop("_id", None)
    await push_notif(req.to_user_id, "gift", f"Sizga {GIFT_EMOJI[req.gift_kind]} sovg'a yuborildi")
    return {"ok": True, "balance": sender.get("balance", 0) - price}


# ---------- Leaderboard ----------
@api.get("/leaderboard")
async def leaderboard(period: str = "all"):
    """TOP supporters by gifts sent."""
    pipeline = [
        {"$group": {"_id": "$from_user_id", "total": {"$sum": "$price"}, "count": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": 50},
    ]
    if period == "day":
        cutoff = iso(datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})
    elif period == "week":
        from datetime import timedelta as _td
        cutoff = iso(datetime.now(timezone.utc) - _td(days=7))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})
    elif period == "month":
        from datetime import timedelta as _td
        cutoff = iso(datetime.now(timezone.utc) - _td(days=30))
        pipeline.insert(0, {"$match": {"created_at": {"$gte": cutoff}}})

    rows = []
    async for r in db.gifts.aggregate(pipeline):
        u = await db.users.find_one({"id": r["_id"]}, {"_id": 0, "password_hash": 0})
        if u:
            rows.append({"user": user_public(u), "total": r["total"], "count": r["count"]})
    return rows


# ---------- Verification ----------
@api.post("/verification/request")
async def request_verification(req: VerificationRequest, uid: str = Depends(get_current_user_id)):
    doc = {
        "id": new_id(),
        "user_id": uid,
        "kind": req.kind,
        "note": req.note,
        "proof_url": req.proof_url,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    await db.verifications.insert_one(doc)
    return {"ok": True, "id": doc["id"]}


# ---------- Payments (CLICK) ----------
@api.post("/payments/create")
async def create_payment(req: CreatePaymentRequest, uid: str = Depends(get_current_user_id)):
    if req.purpose == "premium":
        amount = PRICE_PREMIUM
    elif req.purpose == "vip":
        amount = PRICE_VIP
    elif req.purpose == "super_application":
        amount = PRICE_SUPER
    elif req.purpose == "balance_topup":
        amount = req.amount or 0
        if amount < 1000:
            raise HTTPException(400, "Minimum top-up is 1000")
    elif req.purpose == "gift":
        amount = req.amount or 0
        if amount < 50:
            raise HTTPException(400, "Minimum 50")
    else:
        raise HTTPException(400, "Unknown purpose")
    pid = new_id()
    doc = {
        "id": pid,
        "user_id": uid,
        "amount": amount,
        "purpose": req.purpose,
        "target_user_id": req.target_user_id,
        "gift_kind": req.gift_kind,
        "status": "pending",
        "created_at": iso(now_utc()),
    }
    link = click_pay_link(amount, pid)
    doc["payment_link"] = link
    await db.payments.insert_one(doc)
    return {"id": pid, "amount": amount, "payment_link": link, "status": "pending"}


@api.post("/payments/click/callback")
async def click_callback(request: Request):
    form_data = await request.form()
    form = dict(form_data)
    action = form.get("action", "0")
    pid = form.get("merchant_trans_id", "")
    payment = await db.payments.find_one({"id": pid})

    # Try to verify signature; if SECRET_KEY missing or sandbox, accept.
    sign_ok = True
    if CLICK_SECRET_KEY:
        sign_ok = verify_click_sign(form, action)

    if not sign_ok:
        return JSONResponse({"error": -1, "error_note": "SIGN CHECK FAILED"})
    if not payment:
        return JSONResponse({"error": -5, "error_note": "Order not found"})
    if payment["status"] == "success":
        return JSONResponse({"error": -4, "error_note": "Already paid"})
    if action == "0":
        await db.payments.update_one({"id": pid}, {"$set": {"status": "prepared", "click_trans_id": form.get("click_trans_id")}})
        return JSONResponse({
            "error": 0, "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid, "merchant_prepare_id": pid,
        })
    if action == "1":
        await apply_payment_success(payment)
        return JSONResponse({
            "error": 0, "error_note": "Success",
            "click_trans_id": form.get("click_trans_id"),
            "merchant_trans_id": pid, "merchant_confirm_id": pid,
        })
    return JSONResponse({"error": -3, "error_note": "Action not found"})


async def apply_payment_success(payment: dict) -> None:
    from datetime import timedelta as _td
    pid = payment["id"]
    await db.payments.update_one({"id": pid}, {"$set": {"status": "success", "paid_at": iso(now_utc())}})
    uid = payment["user_id"]
    purpose = payment["purpose"]
    amount = payment["amount"]
    expiry_iso = iso(now_utc() + _td(days=30))
    if purpose == "premium":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "premium", "plan_until": expiry_iso}})
        await push_notif(uid, "premium", "Premium tarif faollashtirildi 💎")
    elif purpose == "vip":
        await db.users.update_one({"id": uid}, {"$set": {"plan": "vip", "plan_until": expiry_iso}})
        await push_notif(uid, "premium", "VIP tarif faollashtirildi 👑")
    elif purpose == "balance_topup":
        await db.users.update_one({"id": uid}, {"$inc": {"balance": amount}})
        await push_notif(uid, "balance", f"Balansingiz {amount:,} so'mga to'ldirildi")
    elif purpose == "super_application":
        await db.users.update_one({"id": uid}, {"$inc": {"super_applications_available": 1}})
        await push_notif(uid, "balance", "Super murojaat sotib olindi")
    elif purpose == "gift":
        await db.users.update_one({"id": uid}, {"$inc": {"balance": amount}})


@api.post("/payments/admin-confirm/{payment_id}")
async def admin_confirm_payment(payment_id: str, _: str = Depends(get_current_admin)):
    payment = await db.payments.find_one({"id": payment_id})
    if not payment:
        raise HTTPException(404, "Not found")
    if payment["status"] == "success":
        return {"ok": True}
    await apply_payment_success(payment)
    return {"ok": True}


@api.get("/payments/mine")
async def my_payments(uid: str = Depends(get_current_user_id)):
    rows = await db.payments.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(200)
    return rows


# ---------- Notifications ----------
@api.get("/notifications")
async def list_notifications(uid: str = Depends(get_current_user_id)):
    rows = await db.notifications.find({"user_id": uid}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return rows


@api.post("/notifications/read-all")
async def mark_all_read(uid: str = Depends(get_current_user_id)):
    await db.notifications.update_many({"user_id": uid, "read": False}, {"$set": {"read": True}})
    return {"ok": True}


# ---------- Referral ----------
@api.get("/referral/mine")
async def my_referral(uid: str = Depends(get_current_user_id)):
    me_doc = await get_user(uid)
    code = me_doc.get("referral_code")
    if not code:
        code = uid[:8]
        await db.users.update_one({"id": uid}, {"$set": {"referral_code": code}})
    count = await db.users.count_documents({"referred_by": code})
    bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Fidem_Appbot")
    link = f"https://t.me/{bot_username}?start={code}"
    return {"code": code, "link": link, "invited_count": count, "bonus_per_invite": 1000}


# ---------- Admin ----------
@api.get("/admin/stats")
async def admin_stats(_: str = Depends(get_current_admin)):
    total = await db.users.count_documents({})
    males = await db.users.count_documents({"gender": "male"})
    females = await db.users.count_documents({"gender": "female"})
    onboarded = await db.users.count_documents({"onboarded": True})
    premium = await db.users.count_documents({"plan": "premium"})
    vip = await db.users.count_documents({"plan": "vip"})
    from datetime import timedelta as _td
    today_iso = iso(datetime.now(timezone.utc) - _td(days=1))
    week_iso = iso(datetime.now(timezone.utc) - _td(days=7))
    dau = await db.users.count_documents({"last_active": {"$gte": today_iso}})
    wau = await db.users.count_documents({"last_active": {"$gte": week_iso}})
    rev_agg = await db.payments.aggregate([
        {"$match": {"status": "success"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]).to_list(1)
    revenue = rev_agg[0]["total"] if rev_agg else 0
    pending_payments = await db.payments.count_documents({"status": "pending"})
    pending_verif = await db.verifications.count_documents({"status": "pending"})
    open_reports = await db.reports.count_documents({"status": "open"})
    return {
        "total_users": total, "males": males, "females": females,
        "onboarded": onboarded, "premium": premium, "vip": vip,
        "dau": dau, "wau": wau, "revenue_uzs": revenue,
        "conversion_premium": round((premium + vip) / total * 100, 2) if total else 0,
        "pending_payments": pending_payments,
        "pending_verifications": pending_verif,
        "open_reports": open_reports,
    }


@api.get("/admin/users")
async def admin_list_users(q: str = "", limit: int = 100, _: str = Depends(get_current_admin)):
    query = {}
    if q:
        query["$or"] = [
            {"email": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"telegram_username": {"$regex": q, "$options": "i"}},
        ]
    rows = await db.users.find(query, {"_id": 0, "password_hash": 0}).limit(limit).to_list(limit)
    return [user_public(u) for u in rows]


@api.patch("/admin/users/{target_id}")
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


@api.get("/admin/payments")
async def admin_payments(status: Optional[str] = None, _: str = Depends(get_current_admin)):
    q: dict = {}
    if status:
        q["status"] = status
    rows = await db.payments.find(q, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return rows


@api.get("/admin/verifications")
async def admin_verifications(_: str = Depends(get_current_admin)):
    rows = await db.verifications.find({"status": "pending"}, {"_id": 0}).to_list(200)
    return rows


@api.post("/admin/verifications/{vid}/decide")
async def admin_decide_verif(vid: str, approve: bool = Body(..., embed=True), _: str = Depends(get_current_admin)):
    v = await db.verifications.find_one({"id": vid})
    if not v:
        raise HTTPException(404, "Not found")
    await db.verifications.update_one({"id": vid}, {"$set": {"status": "approved" if approve else "rejected"}})
    if approve:
        field = {"identity": "verified_identity", "selfie": "verified_selfie", "financial": "verified_financial"}[v["kind"]]
        await db.users.update_one({"id": v["user_id"]}, {"$set": {field: True}})
        await push_notif(v["user_id"], "verified", f"Verification tasdiqlandi: {v['kind']}")
    return {"ok": True}


@api.get("/admin/reports")
async def admin_reports(_: str = Depends(get_current_admin)):
    rows = await db.reports.find({}, {"_id": 0}).sort("created_at", -1).limit(200).to_list(200)
    return rows


@api.post("/admin/notification/broadcast")
async def admin_broadcast(text: str = Body(..., embed=True), _: str = Depends(get_current_admin)):
    """Send a marketing notification to all onboarded users (daily-cap 2 enforced)."""
    users = await db.users.find({"onboarded": True, "blocked": {"$ne": True}}, {"_id": 0, "id": 1}).to_list(10000)
    sent, skipped = 0, 0
    for u in users:
        ok = await push_notif(u["id"], "marketing", text, marketing=True)
        if ok:
            sent += 1
        else:
            skipped += 1
    return {"sent": sent, "skipped_daily_cap": skipped}


# ---------- Object Storage (photo upload) ----------
@api.post("/files/upload")
async def upload_file(file: UploadFile = File(...), uid: str = Depends(get_current_user_id)):
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"
    if ext not in MIME:
        raise HTTPException(400, "Only image files (jpg/png/gif/webp) are allowed")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Max file size 8MB")
    storage_path = f"{os.environ.get('APP_NAME','fidem')}/uploads/{uid}/{new_id()}.{ext}"
    try:
        result = await put_object(storage_path, data, MIME[ext])
    except Exception as e:
        log.error(f"upload failed: {e}")
        raise HTTPException(500, "Upload failed")
    await db.files.insert_one({
        "id": new_id(),
        "owner_id": uid,
        "storage_path": result["path"],
        "content_type": MIME[ext],
        "size": result.get("size", len(data)),
        "is_deleted": False,
        "created_at": iso(now_utc()),
    })
    # Path-only (frontend will append viewer's own JWT when rendering)
    return {"path": result["path"], "url": f"/api/files/{result['path']}"}


@api.get("/files/{path:path}")
async def serve_file(path: str, auth: Optional[str] = Query(None), authorization: Optional[str] = Header(default=None)):
    """Serve a stored file. Auth via Authorization header or ?auth= query param."""
    from auth import decode_token
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif auth:
        token = auth
    if not token:
        raise HTTPException(401, "Auth required")
    try:
        decode_token(token)
    except HTTPException:
        raise
    rec = await db.files.find_one({"storage_path": path, "is_deleted": False}, {"_id": 0})
    if not rec:
        raise HTTPException(404, "File not found")
    try:
        data, content_type = await get_object(path)
    except Exception:
        raise HTTPException(500, "Storage read failed")
    return Response(content=data, media_type=rec.get("content_type", content_type))


# ---------- Telegram bot webhook ----------
TELEGRAM_WEBHOOK_SECRET = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "fidem-tg")


async def setup_telegram_webhook():
    if not TELEGRAM_BOT_TOKEN:
        return
    public_base = os.environ.get("CLICK_RETURN_URL", "").split("/payment/return")[0]
    if not public_base:
        return
    webhook_url = f"{public_base}/api/telegram/webhook?secret={TELEGRAM_WEBHOOK_SECRET}"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15.0) as cl:
            r = await cl.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
                json={"url": webhook_url, "allowed_updates": ["message"]},
            )
            log.info(f"Telegram webhook set: {r.status_code} {r.text[:200]}")
    except Exception as e:
        log.warning(f"setWebhook failed: {e}")


@api.post("/telegram/webhook")
async def telegram_webhook(request: Request, secret: Optional[str] = Query(None)):
    if secret != TELEGRAM_WEBHOOK_SECRET:
        raise HTTPException(403, "bad secret")
    body = await request.json()
    msg = body.get("message")
    if not msg:
        return {"ok": True}
    text = (msg.get("text") or "").strip()
    chat_id = msg["chat"]["id"]
    tg_user_id = str(msg["from"]["id"])

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        ref_code = parts[1].strip() if len(parts) > 1 else None
        # Attach referral if user is new
        existing = await db.users.find_one({"telegram_id": tg_user_id}, {"_id": 0, "id": 1, "referred_by": 1})
        if ref_code and (not existing or not existing.get("referred_by")):
            ref_owner = await db.users.find_one({"referral_code": ref_code}, {"_id": 0, "id": 1})
            if ref_owner and (not existing or existing["id"] != ref_owner["id"]):
                if existing:
                    await db.users.update_one({"id": existing["id"]}, {"$set": {"referred_by": ref_code}})
                else:
                    # store pending referral until first auth
                    await db.pending_refs.update_one(
                        {"telegram_id": tg_user_id},
                        {"$set": {"telegram_id": tg_user_id, "ref_code": ref_code, "at": iso(now_utc())}},
                        upsert=True,
                    )
                # Reward referrer
                await db.users.update_one({"id": ref_owner["id"]}, {"$inc": {"balance": 1000, "ref_count": 1}})
                await push_notif(ref_owner["id"], "referral", "Yangi taklif bonus +1000 so'm")

        bot_username = os.environ.get("TELEGRAM_BOT_USERNAME", "Fidem_Appbot")
        webapp_url = os.environ.get("CLICK_RETURN_URL", "").split("/payment/return")[0]
        reply = (
            "Assalomu alaykum! FIDEM — Sizga mos insonni xavfsiz topishga yordam beramiz.\n\n"
            f"@{bot_username} ilovasini ochish uchun pastdagi tugmani bosing 👇"
        )
        keyboard = {
            "inline_keyboard": [[{"text": "FIDEM'ni ochish", "web_app": {"url": webapp_url}}]]
        } if webapp_url else None
        await send_telegram_message(chat_id, reply, reply_markup=keyboard)
    return {"ok": True}


# ---------- Seed admin + indexes ----------
@app.on_event("startup")
async def startup():
    # Object storage init (non-fatal if fails)
    try:
        init_storage()
    except Exception as e:
        log.warning(f"Storage startup warning: {e}")

    # Set Telegram webhook (non-fatal)
    asyncio.create_task(setup_telegram_webhook())

    # Indexes
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", sparse=True)
    await db.users.create_index("telegram_id", sparse=True)
    await db.messages.create_index([("chat_id", 1), ("created_at", 1)])
    await db.saved.create_index([("owner_id", 1), ("target_id", 1)], unique=True)
    await db.profile_views.create_index([("viewer_id", 1), ("target_id", 1)], unique=True)
    await db.photo_unlocks.create_index([("requester_id", 1), ("target_id", 1)], unique=True)
    await db.payments.create_index("id", unique=True)

    # Seed admin
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not admin:
        await db.users.insert_one({
            "id": new_id(),
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_pw(ADMIN_PASSWORD),
            "name": "FIDEM Admin",
            "is_admin": True,
            "onboarded": True,
            "verified_identity": True,
            "verified_selfie": True,
            "verified_financial": True,
            "plan": "vip",
            "balance": 0,
            "gender": "male",
            "birth_date": "1990-01-01",
            "country": "Uzbekistan",
            "region": "Toshkent",
            "district": "Markaz",
            "marital_status": "single",
            "has_children": False,
            "children_count": 0,
            "height_cm": 175,
            "weight_kg": 70,
            "education": "Oliy",
            "profession": "Admin",
            "religion": "Islom",
            "looking_for": "—",
            "search_gender": "female",
            "search_age_min": 18,
            "search_age_max": 60,
            "search_region": "Toshkent",
            "language": "uz",
            "created_at": iso(now_utc()),
            "last_active": iso(now_utc()),
        })
        log.info(f"Seeded admin: {ADMIN_EMAIL}")

    # Seed demo users if collection has fewer than 10 onboarded
    onboarded = await db.users.count_documents({"onboarded": True, "is_admin": {"$ne": True}})
    if onboarded < 12:
        await seed_demo_users()


async def seed_demo_users():
    demo = [
        ("Madina", "female", "1998-04-15", "Toshkent", "Yunusobod", 165, 55, "Oliy", "O'qituvchi", "Islom"),
        ("Aziza", "female", "1996-09-21", "Toshkent", "Chilonzor", 168, 58, "Magistr", "Dizayner", "Islom"),
        ("Dilnoza", "female", "2000-02-10", "Samarqand", "Markaz", 162, 52, "Oliy", "Tibbiyot", "Islom"),
        ("Shahnoza", "female", "1995-11-30", "Toshkent", "Mirzo Ulug'bek", 170, 60, "Magistr", "Iqtisodchi", "Islom"),
        ("Gulnora", "female", "1999-07-05", "Buxoro", "Markaz", 164, 54, "Oliy", "Bank", "Islom"),
        ("Sevara", "female", "1997-12-18", "Toshkent", "Sergeli", 167, 56, "Oliy", "IT", "Islom"),
        ("Lola", "female", "2001-03-22", "Andijon", "Markaz", 163, 53, "Bakalavr", "Talaba", "Islom"),
        ("Nigora", "female", "1994-06-12", "Toshkent", "Yashnobod", 169, 59, "Magistr", "Yurist", "Islom"),
        ("Bobur", "male", "1995-05-10", "Toshkent", "Yunusobod", 178, 75, "Oliy", "Muhandis", "Islom"),
        ("Sardor", "male", "1992-08-25", "Toshkent", "Mirzo Ulug'bek", 182, 80, "Magistr", "IT-Direktor", "Islom"),
        ("Jasur", "male", "1998-01-15", "Samarqand", "Markaz", 175, 72, "Oliy", "Vrach", "Islom"),
        ("Diyor", "male", "1996-10-08", "Toshkent", "Chilonzor", 180, 78, "Oliy", "Biznes", "Islom"),
        ("Otabek", "male", "1993-11-19", "Toshkent", "Yashnobod", 179, 77, "Magistr", "Marketing", "Islom"),
        ("Rustam", "male", "1997-04-30", "Buxoro", "Markaz", 176, 74, "Oliy", "Arxitektor", "Islom"),
    ]
    photos_f = [
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800",
        "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800",
        "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800",
        "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=800",
        "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=800",
        "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=800",
    ]
    photos_m = [
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800",
        "https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=800",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800",
        "https://images.unsplash.com/photo-1531427186611-ecfd6d936c79?w=800",
        "https://images.unsplash.com/photo-1463453091185-61582044d556?w=800",
        "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=800",
    ]
    pf = 0
    pm = 0
    for name, gender, bd, region, district, h, w, edu, prof, rel in demo:
        uid = new_id()
        photo = photos_f[pf % len(photos_f)] if gender == "female" else photos_m[pm % len(photos_m)]
        if gender == "female":
            pf += 1
        else:
            pm += 1
        doc = {
            "id": uid,
            "name": name,
            "gender": gender,
            "birth_date": bd,
            "country": "Uzbekistan",
            "region": region,
            "district": district,
            "marital_status": "single",
            "has_children": False,
            "children_count": 0,
            "height_cm": h,
            "weight_kg": w,
            "education": edu,
            "profession": prof,
            "religion": rel,
            "looking_for": "Oila qurish, samimiy va vafodor inson",
            "search_gender": "male" if gender == "female" else "female",
            "search_age_min": 20,
            "search_age_max": 40,
            "search_region": region,
            "photo_url": photo,
            "bio": f"Salom! Men {name}. Oilaviy hayot tarafdoriman.",
            "onboarded": True,
            "verified_identity": True,
            "verified_selfie": True,
            "verified_financial": False,
            "plan": "free",
            "balance": 0,
            "language": "uz",
            "created_at": iso(now_utc()),
            "last_active": iso(now_utc()),
        }
        doc["completeness"] = compute_completeness(doc)
        await db.users.insert_one(doc)
    log.info("Seeded demo users")


@app.on_event("shutdown")
async def shutdown():
    client.close()


# ---------- Mount + CORS ----------
app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
