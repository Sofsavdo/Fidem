"""Account: delete it, attach an email + password, reset a forgotten password.

DELETION (POST /account/delete) removes the person and everything they left
behind: profile, photos and selfies (the stored files too), chats (both sides
of them), likes, views, unlocks, blocks, notifications, contact exchanges,
location, orders, stories. What stays, on purpose, carries no personal data:
- payment / top-up / gift ledgers (accounting): ids and amounts only; the
  receipt image is deleted, a withdrawal's card number is cut to its last 4;
- reports filed against the person (so a repeat offender stays visible to
  moderators), with their free text removed;
- a hash (never the value) of a banned person's email / Telegram id, so
  deleting an account does not lift a ban.
Money still in flight (a withdrawal or a top-up waiting for an admin) blocks
the deletion until it is settled; balances and earnings are forfeited, and the
app says so before the person confirms.

EMAIL + PASSWORD. A person who joined through Telegram has no password, so on
a phone app (no Telegram) they could never sign back in. They add an email
with a 6-digit code sent to it (proof they own it), then choose a password.
Forgot-password uses the same code mechanism. Codes live 15 minutes, allow 5
wrong tries, and every send is rate-limited. Without a mail provider
(mailer.py) these answer `email_unavailable`.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr

import core
import mailer
from auth import JWT_SECRET, create_token, forget_account, get_current_user_id
from core import RateLimiter, _client_ip, iso, now_utc, parse_dt

log = logging.getLogger("fidem.account")
router = APIRouter(tags=["account"])

CODE_TTL = timedelta(minutes=15)
MAX_CODE_ATTEMPTS = 5
PASSWORD_MIN = 8
DELETE_WORD = "DELETE"

send_limiter = RateLimiter(max_attempts=5, window_sec=900)       # code emails per IP + address
code_try_limiter = RateLimiter(max_attempts=15, window_sec=900)  # code guesses per IP
delete_limiter = RateLimiter(max_attempts=5, window_sec=600)     # deletion attempts per account


# ---------- small helpers ----------
def check_password(pw: str) -> None:
    """400 `weak_password` unless the password is at least PASSWORD_MIN long and
    not one character repeated."""
    pw = pw or ""
    if len(pw) < PASSWORD_MIN or len(pw) > 128 or len(set(pw)) < 3:
        raise HTTPException(400, "weak_password")


def _hash(value: str) -> str:
    return hmac.new(JWT_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def identity_hash(kind: str, value: str) -> str:
    return hashlib.sha256(f"{kind}:{str(value).strip().lower()}".encode()).hexdigest()


async def is_banned(kind: str, value: Optional[str]) -> bool:
    """Was this email ("email") or Telegram id ("tg") banned before its account was deleted?"""
    if not value:
        return False
    return await core.db.banned_identities.find_one({"hash": identity_hash(kind, value)}, {"_id": 1}) is not None


async def _issue_code(purpose: str, key: str, user_id: Optional[str] = None, email: str = "") -> str:
    code = f"{secrets.randbelow(10 ** 6):06d}"
    await core.db.auth_codes.delete_many({"purpose": purpose, "key": key})     # one live code per purpose
    await core.db.auth_codes.insert_one({
        "purpose": purpose, "key": key, "user_id": user_id, "email": email,
        "code_hash": _hash(f"{purpose}:{key}:{code}"),
        "expires_at": iso(now_utc() + CODE_TTL), "attempts": 0, "created_at": iso(now_utc()),
    })
    return code


async def _consume_code(purpose: str, key: str, code: str) -> Optional[dict]:
    """The stored record when `code` is right (and the record is used up), else None."""
    rec = await core.db.auth_codes.find_one({"purpose": purpose, "key": key})
    if not rec or parse_dt(rec["expires_at"]) < now_utc():
        if rec:
            await core.db.auth_codes.delete_one({"_id": rec["_id"]})
        return None
    if int(rec.get("attempts", 0)) >= MAX_CODE_ATTEMPTS:
        await core.db.auth_codes.delete_one({"_id": rec["_id"]})
        return None
    given = _hash(f"{purpose}:{key}:{(code or '').strip()}")
    if not hmac.compare_digest(given, rec["code_hash"]):
        await core.db.auth_codes.update_one({"_id": rec["_id"]}, {"$inc": {"attempts": 1}})
        return None
    await core.db.auth_codes.delete_one({"_id": rec["_id"]})
    return rec


def _need_mail() -> None:
    if not mailer.configured():
        raise HTTPException(503, "email_unavailable")


def _limit_send(request: Request, email: str) -> None:
    send_limiter.check(f"mail:{_client_ip(request)}:{email}")


# ---------- email + password ----------
class EmailStart(BaseModel):
    email: EmailStr


class EmailConfirm(BaseModel):
    code: str
    password: Optional[str] = None


class ForgotRequest(BaseModel):
    email: EmailStr


class ResetRequest(BaseModel):
    email: EmailStr
    code: str
    password: str


@router.get("/auth/email/status")
async def email_status():
    """Whether this server can send email (the app hides what would not work)."""
    return {"enabled": mailer.configured(), "password_min": PASSWORD_MIN}


@router.post("/auth/email/start")
async def email_start(req: EmailStart, request: Request, uid: str = Depends(get_current_user_id)):
    """Send a 6-digit code to the address the signed-in person wants to attach."""
    email = req.email.lower()
    _limit_send(request, email)
    _need_mail()
    user = await core.db.users.find_one({"id": uid}, {"_id": 0, "email": 1})
    if user is None:
        raise HTTPException(404, "User not found")
    if user.get("email") and user["email"] != email:
        raise HTTPException(400, "email_already_set")
    if await core.db.users.find_one({"email": email, "id": {"$ne": uid}}, {"_id": 1}):
        raise HTTPException(409, "email_taken")
    if await is_banned("email", email):
        raise HTTPException(403, "account_blocked")
    code = await _issue_code("verify_email", uid, user_id=uid, email=email)
    sent = await mailer.send_email(
        email, "FIDEM: tasdiqlash kodi",
        f"FIDEM tasdiqlash kodingiz: {code}\n\nKod 15 daqiqa amal qiladi. Siz so'ramagan bo'lsangiz, bu xatga e'tibor bermang.",
    )
    if not sent:
        await core.db.auth_codes.delete_many({"purpose": "verify_email", "key": uid})
        raise HTTPException(502, "email_send_failed")
    return {"ok": True}


@router.post("/auth/email/confirm")
async def email_confirm(req: EmailConfirm, request: Request, uid: str = Depends(get_current_user_id)):
    """Check the code; the address becomes the person's login. A Telegram-only
    account also sets its first password here."""
    code_try_limiter.check(f"codetry:{_client_ip(request)}")
    user = await core.db.users.find_one({"id": uid}, {"_id": 0, "password_hash": 1, "email": 1})
    if user is None:
        raise HTTPException(404, "User not found")
    has_password = bool(user.get("password_hash"))
    if not has_password:
        check_password(req.password or "")
    rec = await _consume_code("verify_email", uid, req.code)
    if not rec:
        raise HTTPException(400, "invalid_code")
    email = rec["email"]
    if await core.db.users.find_one({"email": email, "id": {"$ne": uid}}, {"_id": 1}):
        raise HTTPException(409, "email_taken")
    upd = {"email": email, "email_verified": True}
    if not has_password:
        import asyncio
        upd["password_hash"] = await asyncio.to_thread(core.hash_pw, req.password)
    await core.db.users.update_one({"id": uid}, {"$set": upd})
    from routers.auth_r import _build_me_payload
    return {"ok": True, "user": _build_me_payload(await core.db.users.find_one({"id": uid}, {"_id": 0}))}


@router.post("/auth/password/forgot")
async def password_forgot(req: ForgotRequest, request: Request):
    """Email a reset code. The answer is the same whether or not the address
    has an account, so this can't be used to find out who is registered."""
    email = req.email.lower()
    _limit_send(request, email)
    _need_mail()
    user = await core.db.users.find_one({"email": email, "password_hash": {"$exists": True}}, {"_id": 0, "id": 1, "is_admin": 1})
    if user and not user.get("is_admin"):
        code = await _issue_code("reset", email, user_id=user["id"], email=email)
        await mailer.send_email(
            email, "FIDEM: parolni tiklash kodi",
            f"Parolni tiklash kodingiz: {code}\n\nKod 15 daqiqa amal qiladi. Siz so'ramagan bo'lsangiz, bu xatga e'tibor bermang, parolingiz o'zgarmaydi.",
        )
    return {"ok": True}


@router.post("/auth/password/reset")
async def password_reset(req: ResetRequest, request: Request):
    """New password for the right code. Every session signed in before this
    moment is ended, and the person comes back signed in with a fresh one."""
    code_try_limiter.check(f"codetry:{_client_ip(request)}")
    check_password(req.password)
    email = req.email.lower()
    rec = await _consume_code("reset", email, req.code)
    if not rec:
        raise HTTPException(400, "invalid_code")
    user = await core.db.users.find_one({"id": rec["user_id"]}, {"_id": 0})
    if not user or user.get("email") != email or user.get("is_admin"):
        raise HTTPException(400, "invalid_code")
    import asyncio
    from routers.auth_r import _build_me_payload
    await core.db.users.update_one(
        {"id": user["id"]},
        {"$set": {"password_hash": await asyncio.to_thread(core.hash_pw, req.password),
                  "tokens_valid_after": int(now_utc().timestamp()), "email_verified": True}},
    )
    forget_account(user["id"])
    fresh = await core.db.users.find_one({"id": user["id"]}, {"_id": 0})
    return {"token": create_token(user["id"]), "user_id": user["id"], "onboarded": bool(fresh.get("onboarded")),
            "user": _build_me_payload(fresh)}


# ---------- deleting the account ----------
class DeleteRequest(BaseModel):
    confirm: str
    password: Optional[str] = None


# Every field that can point at a person. A document that has none equal to the
# id is untouched, so listing a field a collection doesn't use is harmless.
_REF_FIELDS = (
    "user_id", "owner_id", "target_id", "from_user_id", "to_user_id", "viewer_id", "requester_id",
    "reporter_id", "target_user_id", "sender_id", "recipient_id", "other_id", "author_id",
)
# Collections where nothing about the person should remain.
_SWEEP = (
    "saved", "profile_views", "messages", "photo_unlocks", "photo_peeks", "chat_unlocks", "blocks",
    "notifications", "compat_unlocks", "compat_reports", "contact_exchanges", "family_requests",
    "daily_picks", "user_locations", "applications", "announcement_views", "success_stories",
    "concierge_orders", "gift_inventory", "verifications", "moderation_events", "referral_usernames",
)


def _refs(uid: str) -> dict:
    return {"$or": [{f: uid} for f in _REF_FIELDS]}


async def delete_blockers(uid: str) -> list[str]:
    """Money still being settled by an admin; deleting now would lose track of it."""
    out = []
    if await core.db.withdrawals.find_one({"user_id": uid, "status": "pending"}, {"_id": 1}):
        out.append("pending_withdrawal")
    if await core.db.manual_topups.find_one({"user_id": uid, "status": "pending"}, {"_id": 1}):
        out.append("pending_topup")
    return out


async def delete_account_data(uid: str, user: dict) -> dict:
    """Remove the account and its data (see the module docstring). Safe to run
    again after a failure: the user document goes last."""
    from storage import delete_object

    db = core.db
    # A ban must survive the deletion: keep only hashes of the identifiers.
    if user.get("blocked") or user.get("shadow_banned"):
        rows = [("email", user.get("email")), ("tg", user.get("telegram_id"))]
        for kind, value in rows:
            if value:
                await db.banned_identities.update_one(
                    {"hash": identity_hash(kind, value)},
                    {"$set": {"kind": kind, "at": iso(now_utc())}}, upsert=True,
                )

    files = await db.files.find({"owner_id": uid}, {"_id": 0, "storage_path": 1}).to_list(5000)
    for f in files:
        if f.get("storage_path"):
            await delete_object(f["storage_path"])
    await db.files.delete_many({"owner_id": uid})

    for name in _SWEEP:
        await db[name].delete_many(_refs(uid))
    # reports: what the person filed goes; what was filed about them stays, without the text
    await db.reports.delete_many({"reporter_id": uid})
    await db.reports.update_many({"target_id": uid}, {"$set": {"details": ""}})
    # ledgers stay (accounting) but hold no personal data
    await db.manual_topups.update_many({"user_id": uid}, {"$set": {"proof_url": ""}})
    async for w in db.withdrawals.find({"user_id": uid}, {"_id": 1, "card_number": 1}):
        card = str(w.get("card_number") or "")
        await db.withdrawals.update_one(
            {"_id": w["_id"]}, {"$set": {"card_number": ("*" * 12 + card[-4:]) if card else "", "holder_name": ""}},
        )
    # the bot must stop writing to them, and /start must begin from scratch
    if user.get("telegram_id"):
        await db.bot_starts.delete_many({"telegram_id": user["telegram_id"]})
        await db.pending_refs.delete_many({"telegram_id": user["telegram_id"]})
    await db.auth_codes.delete_many({"$or": [{"user_id": uid}, {"key": uid}]})

    await db.users.delete_one({"id": uid})
    forget_account(uid)
    # close live sockets
    for ws in list(core.manager.connections.get(uid, ())):
        try:
            await ws.close(code=4401)
        except Exception:
            pass
    await core.log_admin_action(uid, "account_deleted_by_user", uid, {})
    return {"files": len(files)}


@router.get("/account/delete-info")
async def delete_info(uid: str = Depends(get_current_user_id)):
    """What the confirmation screen has to show before anything is deleted."""
    user = await core.db.users.find_one({"id": uid}, {"_id": 0})
    if user is None:
        raise HTTPException(404, "User not found")
    return {
        "has_password": bool(user.get("password_hash")),
        "is_admin": bool(user.get("is_admin")),
        "balance": int(user.get("balance") or 0),
        "earnings": int(user.get("referral_earnings_withdrawable") or 0) + int(user.get("referral_earnings_pending") or 0),
        "blockers": await delete_blockers(uid),
        "confirm_word": DELETE_WORD,
    }


@router.post("/account/delete")
async def delete_account(req: DeleteRequest, request: Request, uid: str = Depends(get_current_user_id)):
    delete_limiter.check(f"del:{uid}")
    if (req.confirm or "").strip().upper() != DELETE_WORD:
        raise HTTPException(400, "confirm_required")
    user = await core.db.users.find_one({"id": uid}, {"_id": 0})
    if user is None:
        raise HTTPException(404, "User not found")
    if user.get("is_admin"):
        raise HTTPException(400, "admin_account")          # an admin could lock the panel out
    if user.get("password_hash"):
        import asyncio
        if not req.password or not await asyncio.to_thread(core.check_pw, req.password, user["password_hash"]):
            # 403, not 401: the app treats any 401 as "your session ended" and signs the person out
            raise HTTPException(403, "wrong_password")
    if await delete_blockers(uid):
        raise HTTPException(409, "pending_money")
    await delete_account_data(uid, user)
    return {"ok": True}
