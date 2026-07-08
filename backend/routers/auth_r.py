"""Auth, profile, file upload routes."""
from __future__ import annotations

import os
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Header, HTTPException, Query, Request, UploadFile
from starlette.responses import Response

from auth import (
    create_token,
    decode_token,
    get_current_user_id,
    validate_telegram_init_data,
)
from core import (
    ADMIN_EMAIL,
    TELEGRAM_BOT_TOKEN,
    check_pw,
    db,
    get_user,
    get_webapp_url,
    hash_pw,
    iso,
    log,
    now_utc,
    parse_dt,
    rate_limit_auth,
    user_public,
)
from models import (
    AuthResponse,
    LoginRequest,
    MessageFilters,
    OnboardingProfile,
    RegisterRequest,
    TelegramAuthRequest,
    UpdateProfileRequest,
    new_id,
)
from services import compute_completeness, age_from_birth, send_telegram_message
from storage import MIME, get_object, put_object

router = APIRouter(tags=["auth"])


async def _may_access_file(uid: str, is_admin: bool, rec: dict) -> bool:
    owner_id = rec.get("owner_id")
    if not owner_id:
        return bool(is_admin)
    # Admin can access all files
    if is_admin:
        return True
    # Owner can always access their own files
    if uid == owner_id:
        return True
    # All authenticated users can access profile photos (backward compatibility)
    # If is_public is not set, assume it's a profile photo and allow access
    if rec.get("is_public", True):
        return True
    # Private photos require approved unlock
    unlock = await db.photo_unlocks.find_one(
        {"requester_id": uid, "target_id": owner_id, "approved": True},
        {"_id": 1},
    )
    if unlock:
        return True
    path = rec.get("storage_path") or ""
    if path:
        shared = await db.messages.find_one(
            {
                "$or": [
                    {"from_user_id": uid, "to_user_id": owner_id},
                    {"from_user_id": owner_id, "to_user_id": uid},
                ],
                "meta.voice_url": {"$regex": path},
            },
            {"_id": 1},
        )
        if shared:
            return True
    return False


async def notify_new_profile_to_relevant_users(new_user: dict) -> None:
    uid = new_user.get("id")
    if not uid:
        return

    gender = new_user.get("gender")
    region = new_user.get("region")
    district = new_user.get("district")
    name = new_user.get("name") or "Yangi foydalanuvchi"
    age = age_from_birth(new_user.get("birth_date", "2000-01-01"))

    if gender == "female":
        target_gender = "male"
    elif gender == "male":
        target_gender = "female"
    else:
        return

    if not region:
        return

    webapp_url = get_webapp_url()
    profile_url = f"{webapp_url}/candidate/{uid}"

    location_line = region
    if district:
        location_line = f"{region} · {district}"

    text = (
        "💌 Sizga mos yangi anketa qo‘shildi\n\n"
        f"{name}, {age} yosh\n"
        f"{location_line}\n\n"
        "🟢 Yaqinda ro‘yxatdan o‘tgan\n\n"
        "👇 Anketani ko‘rish uchun bosing"
    )

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "👀 Anketani ko‘rish",
                    "web_app": {"url": profile_url},
                }
            ]
        ]
    }

    query = {
        "onboarded": True,
        "gender": target_gender,
        "region": region,
        "telegram_id": {"$exists": True, "$ne": None},
        "id": {"$ne": uid},
    }

    cursor = db.users.find(query, {"_id": 0, "id": 1, "telegram_id": 1}).limit(50)

    async for target in cursor:
        tg_id = target.get("telegram_id")
        if not tg_id:
            continue

        try:
            await send_telegram_message(
                int(tg_id),
                text,
                reply_markup=keyboard,
            )
        except Exception as e:
            log.warning(f"new profile telegram notification failed: {e}")


@router.get("/")
async def health():
    return {"status": "ok", "service": "fidem"}


def _build_me_payload(user: dict) -> dict:
    """Full profile shape returned by GET /auth/me. Shared so login/register/
    telegram-auth can embed it directly and skip a follow-up /auth/me call."""
    pub = user_public(user, include_private=True)
    pub["email"] = user.get("email")
    pub["telegram_id"] = user.get("telegram_id")
    pub["telegram_username"] = user.get("telegram_username")
    pub["onboarded"] = user.get("onboarded", False)
    pub["is_admin"] = user.get("is_admin", False)
    pub["message_filters"] = user.get("message_filters", {})
    pub["birth_date"] = user.get("birth_date")
    pub["country"] = user.get("country")
    pub["search_country"] = user.get("search_country")
    pub["search_region"] = user.get("search_region")
    pub["search_age_min"] = user.get("search_age_min", 18)
    pub["search_age_max"] = user.get("search_age_max", 60)
    pub["search_gender"] = user.get("search_gender")
    pub["looking_for"] = user.get("looking_for")
    pub["language"] = user.get("language", "uz")
    return pub


@router.post("/auth/register", response_model=AuthResponse)
async def register(req: RegisterRequest, request: Request):
    rate_limit_auth(request)
    existing = await db.users.find_one({"email": req.email.lower()})
    if existing:
        raise HTTPException(400, "Email already registered")
    
    # Get client IP and user agent for analytics
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")
    
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
        "ip_address": client_ip,
        "user_agent": user_agent,
        "fraud_score": 0,
        "fraud_reasons": [],
        "flagged_as_bot": False,
    }
    
    # Check for multiple accounts from same IP (potential fraud)
    ip_count = await db.users.count_documents({"ip_address": client_ip, "created_at": {"$gte": iso(now_utc() - timedelta(hours=24))}})
    if ip_count >= 3:
        doc["fraud_score"] = 30
        doc["fraud_reasons"] = ["multiple_accounts_same_ip"]
        doc["flagged_as_bot"] = True
    
    await db.users.insert_one(doc)
    return AuthResponse(token=create_token(uid), user_id=uid, onboarded=False, user=_build_me_payload(doc))


@router.post("/auth/login", response_model=AuthResponse)
async def login(req: LoginRequest, request: Request):
    rate_limit_auth(request)
    user = await db.users.find_one({"email": req.email.lower()})
    if not user or not check_pw(req.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")
    is_admin = bool(user.get("is_admin", False))
    return AuthResponse(
        token=create_token(user["id"], is_admin=is_admin),
        user_id=user["id"],
        is_admin=is_admin,
        onboarded=user.get("onboarded", False),
        user=_build_me_payload(user),
    )


@router.post("/auth/telegram", response_model=AuthResponse)
async def auth_telegram(req: TelegramAuthRequest, request: Request):
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(500, "Bot token not configured")
    tg_user = validate_telegram_init_data(req.init_data, TELEGRAM_BOT_TOKEN)
    tg_id = str(tg_user.get("id"))
    if not tg_id:
        raise HTTPException(400, "No telegram user id")

    # Get client IP and user agent for analytics
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    existing = await db.users.find_one({"telegram_id": tg_id})
    if existing:
        await db.users.update_one(
            {"id": existing["id"]},
            {"$set": {"last_active": iso(now_utc()), "ip_address": client_ip, "user_agent": user_agent}},
        )
        existing.update({"last_active": iso(now_utc()), "ip_address": client_ip, "user_agent": user_agent})
        return AuthResponse(
            token=create_token(existing["id"], is_admin=existing.get("is_admin", False)),
            user_id=existing["id"],
            is_admin=existing.get("is_admin", False),
            onboarded=existing.get("onboarded", False),
            user=_build_me_payload(existing),
        )

    uid = new_id()
    name = (tg_user.get("first_name", "") + " " + tg_user.get("last_name", "")).strip() or f"User{tg_id[-4:]}"
    
    # Check for multiple accounts from same IP (potential fraud)
    ip_count = await db.users.count_documents({"ip_address": client_ip, "created_at": {"$gte": iso(now_utc() - timedelta(hours=24))}})
    fraud_score = 0
    fraud_reasons = []
    flagged_as_bot = False
    if ip_count >= 3:
        fraud_score = 30
        fraud_reasons = ["multiple_accounts_same_ip"]
        flagged_as_bot = True
    
    doc = {
        "id": uid,
        "telegram_id": tg_id,
        "telegram_username": tg_user.get("username"),
        "telegram_language": tg_user.get("language_code", "uz"),
        "name": name,
        "created_at": iso(now_utc()),
        "last_active": iso(now_utc()),
        "onboarded": False,
        "verified_identity": True,
        "verified_selfie": False,
        "verified_financial": False,
        "plan": "free",
        "balance": 0,
        "blocked": False,
        "ip_address": client_ip,
        "user_agent": user_agent,
        "fraud_score": fraud_score,
        "fraud_reasons": fraud_reasons,
        "flagged_as_bot": flagged_as_bot,
        "referral_id": uid[:8],
    }
    await db.users.insert_one(doc)

    pend = await db.pending_refs.find_one({"telegram_id": tg_id})
    if pend:
        # Phase 1.6: Anti-fraud - self-referral prevention
        ref_code = pend["ref_code"]
        ref_owner = await db.users.find_one({"referral_id": ref_code})
        if not ref_owner:
            ref_owner = await db.users.find_one({"referral_username_lower": ref_code.lower()})
        
        # Block self-referral (same telegram_id)
        if ref_owner and ref_owner.get("telegram_id") == tg_id:
            await db.pending_refs.delete_one({"telegram_id": tg_id})
        else:
            await db.users.update_one({"id": uid}, {"$set": {"referred_by": ref_code}})
            await db.pending_refs.delete_one({"telegram_id": tg_id})

    return AuthResponse(token=create_token(uid), user_id=uid, onboarded=False, user=_build_me_payload(doc))


@router.get("/auth/me")
async def me(uid: str = Depends(get_current_user_id)):
    user = await get_user(uid)
    return _build_me_payload(user)


@router.post("/profile/onboard")
async def onboard(req: OnboardingProfile, uid: str = Depends(get_current_user_id)):
    update = req.model_dump()

    photo_url = (update.get("photo_url") or "").strip()
    if not photo_url:
        raise HTTPException(400, "photo_required")

    user = await get_user(uid)
    was_onboarded = bool(user.get("onboarded"))

    if not user.get("photo_verified"):
        from ai_service import verify_face_photo

        result = await verify_face_photo(image_url=photo_url)
        if not result.get("valid"):
            await db.users.update_one(
                {"id": uid},
                {
                    "$set": {
                        "photo_verified": False,
                        "photo_verification_code": result.get("code"),
                    }
                },
            )
            raise HTTPException(400, f"photo_invalid:{result.get('code') or 'other'}")

        await db.users.update_one(
            {"id": uid},
            {
                "$set": {
                    "photo_verified": True,
                    "photo_verified_at": iso(now_utc()),
                    "photo_verification_code": "ok",
                }
            },
        )

    update["onboarded"] = True
    update["last_active"] = iso(now_utc())

    await db.users.update_one({"id": uid}, {"$set": update})

    fresh = await get_user(uid)
    completeness = compute_completeness(fresh)

    await db.users.update_one(
        {"id": uid},
        {"$set": {"completeness": completeness}},
    )

    if not was_onboarded:
        await notify_new_profile_to_relevant_users(fresh)
        
        # Referral signup reward
        # 100 so'm to inviter's referral earnings if inviter account age >= 30 days and user has 80%+ profile
        referred_by = fresh.get("referred_by")
        if referred_by and completeness >= 80:
            inviter = await db.users.find_one({"referral_id": referred_by})
            if not inviter:
                inviter = await db.users.find_one({"referral_username_lower": referred_by.lower()})
            
            if inviter:
                # Check inviter account age >= 30 days
                inviter_age = now_utc() - parse_dt(inviter.get("created_at", now_utc()))
                if inviter_age >= timedelta(days=30):
                    # Check for duplicate earning (idempotency)
                    existing_earning = await db.users.find_one(
                        {
                            "id": inviter["id"],
                            "referral_earnings.referred_user_id": uid,
                            "referral_earnings.type": "signup_free"
                        }
                    )
                    
                    if not existing_earning:
                        hold_until = now_utc() + timedelta(days=30)
                        
                        # Record referral earning with 1 month hold
                        earning_record = {
                            "id": new_id(),
                            "user_id": inviter["id"],
                            "referred_user_id": uid,
                            "type": "signup_free",
                            "amount": 100,
                            "status": "pending",
                            "created_at": iso(now_utc()),
                            "hold_until": iso(hold_until),
                            "approved_at": None,
                            "paid_at": None,
                            "gross_amount": 100,
                            "tax_amount": 0,
                            "net_amount": 100,
                            "level": 1,
                        }
                        await db.users.update_one(
                            {"id": inviter["id"]},
                            {
                                "$push": {"referral_earnings": earning_record},
                                "$inc": {"referral_earnings_pending": 100}
                            }
                        )

    return {"ok": True, "completeness": completeness}


@router.patch("/profile")
async def update_profile(req: UpdateProfileRequest, uid: str = Depends(get_current_user_id)):
    user = await get_user(uid)
    update = {k: v for k, v in req.model_dump().items() if v is not None}
    locked = {"height_cm", "weight_kg", "marital_status", "has_children", "children_count"}

    if user.get("onboarded") and any(k in update for k in locked):
        update["verified_selfie"] = False
        update["pending_admin_review"] = True

    await db.users.update_one({"id": uid}, {"$set": update})

    fresh = await get_user(uid)
    completeness = compute_completeness(fresh)

    await db.users.update_one(
        {"id": uid},
        {"$set": {"completeness": completeness}},
    )

    return {"ok": True, "completeness": completeness}


@router.patch("/profile/language")
async def set_language(language: str = Body(..., embed=True), uid: str = Depends(get_current_user_id)):
    if language not in ("uz", "ru", "en"):
        raise HTTPException(400, "Unsupported language")
    await db.users.update_one({"id": uid}, {"$set": {"language": language}})
    return {"ok": True}


@router.patch("/profile/filters")
async def set_filters(req: MessageFilters, uid: str = Depends(get_current_user_id)):
    await db.users.update_one({"id": uid}, {"$set": {"message_filters": req.model_dump()}})
    return {"ok": True}


@router.post("/files/upload")
async def upload_file(request: Request, file: UploadFile = File(...), uid: str = Depends(get_current_user_id)):
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > 9 * 1024 * 1024:
        raise HTTPException(413, "Max file size 8MB")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else "bin"

    if ext not in MIME:
        raise HTTPException(400, "Only image (jpg/png/gif/webp) or PDF files are allowed")

    data = await file.read()

    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(413, "Max file size 8MB")

    storage_path = f"{os.environ.get('APP_NAME', 'fidem')}/uploads/{uid}/{new_id()}.{ext}"

    try:
        result = await put_object(storage_path, data, MIME[ext])
    except Exception as e:
        log.error(f"upload failed: {e}")
        raise HTTPException(500, "Upload failed")

    await db.files.insert_one(
        {
            "id": new_id(),
            "owner_id": uid,
            "storage_path": result["path"],
            "content_type": MIME[ext],
            "size": result.get("size", len(data)),
            "is_deleted": False,
            "is_public": True,  # Profile photos are public by default
            "created_at": iso(now_utc()),
        }
    )

    return {"path": result["path"], "url": f"/api/files/{result['path']}"}


@router.get("/files/{path:path}")
async def serve_file(
    path: str,
    auth: Optional[str] = Query(None),
    authorization: Optional[str] = Header(default=None),
):
    token = None

    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    elif auth:
        token = auth

    if not token:
        raise HTTPException(401, "Auth required")

    payload = decode_token(token)
    uid = payload.get("sub")
    if not uid:
        raise HTTPException(401, "Invalid token")

    rec = await db.files.find_one(
        {"storage_path": path, "is_deleted": False},
        {"_id": 0},
    )

    if not rec:
        raise HTTPException(404, "File not found")

    if not await _may_access_file(uid, bool(payload.get("is_admin")), rec):
        raise HTTPException(403, "Forbidden")

    try:
        data, content_type = await get_object(path)
    except Exception:
        raise HTTPException(500, "Storage read failed")

    # Each upload gets a fresh UUID-based storage_path (see /files/upload), so
    # a given path's bytes never change - safe to cache aggressively. This is
    # the single biggest win for perceived speed on photo-heavy pages
    # (candidates grid, saved, chat avatars): without it every photo re-fetches
    # from GridFS on every render, even the same photo seen seconds earlier.
    # `private` (not `public`) because access is per-user authorized above -
    # only the requesting browser may cache it, not shared/proxy caches.
    return Response(
        content=data,
        media_type=rec.get("content_type", content_type),
        headers={"Cache-Control": "private, max-age=31536000, immutable"},
    )
