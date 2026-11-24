"""Authentication helpers: Telegram WebApp + JWT."""
from __future__ import annotations

import time
import hashlib
import hmac
import json
import os
from datetime import datetime, timezone, timedelta
from operator import itemgetter
from typing import Optional
from urllib.parse import parse_qsl

import jwt
from fastapi import Depends, Header, HTTPException, status

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.environ.get("JWT_EXPIRE_HOURS", "720"))

# Validate JWT_SECRET in production. Accept both ENV and ENVIRONMENT since
# deploy docs have historically disagreed on which var name to set.
_is_production = os.environ.get("ENV", os.environ.get("ENVIRONMENT", "")).lower() == "production"
if _is_production and JWT_SECRET == "dev-secret":
    raise ValueError("JWT_SECRET must be set in production environment")


def create_token(user_id: str, is_admin: bool = False) -> str:
    payload = {
        "sub": user_id,
        "is_admin": is_admin,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail=f"Invalid token: {exc}")


# ---- Telegram WebApp initData validation ----
def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    """Validate and parse Telegram WebApp initData. Raises HTTPException on failure."""
    try:
        parsed = dict(parse_qsl(init_data, strict_parsing=True))
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid init_data")

    if "hash" not in parsed:
        raise HTTPException(status_code=403, detail="Missing hash")

    received_hash = parsed.pop("hash")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items(), key=itemgetter(0)))

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if calc_hash != received_hash:
        raise HTTPException(status_code=403, detail="Invalid Telegram hash")

    if "user" not in parsed:
        raise HTTPException(status_code=403, detail="Missing user field")

    return json.loads(parsed["user"])


# ---- is this token still good? (deleted account / password reset) ----
# A token is a signed 30-day pass and says nothing about the account behind
# it. Two things must end a pass early: the account was deleted, and the
# password was reset (`tokens_valid_after`: everything issued before it dies).
# One indexed lookup per account per _ACCOUNT_TTL seconds, not per request.
_ACCOUNT_TTL = 30.0
_ACCOUNT_CACHE: dict[str, tuple[float, bool, int]] = {}


def forget_account(uid: str) -> None:
    """Drop the cached answer after deleting an account or resetting a password."""
    _ACCOUNT_CACHE.pop(uid, None)


async def check_account(uid: str, iat) -> None:
    from core import db  # lazy: core imports this module

    now = time.monotonic()
    hit = _ACCOUNT_CACHE.get(uid)
    if not hit or hit[0] < now:
        doc = await db.users.find_one({"id": uid}, {"_id": 0, "tokens_valid_after": 1})
        if len(_ACCOUNT_CACHE) > 20000:
            _ACCOUNT_CACHE.clear()
        hit = (now + _ACCOUNT_TTL, doc is not None, int((doc or {}).get("tokens_valid_after") or 0))
        _ACCOUNT_CACHE[uid] = hit
    _, exists, valid_after = hit
    if not exists:
        raise HTTPException(status_code=401, detail="Account not found")
    if valid_after and int(iat or 0) < valid_after:
        raise HTTPException(status_code=401, detail="Session expired")


# ---- FastAPI dependency to extract user from Authorization header ----
async def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    data = decode_token(token)
    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    await check_account(user_id, data.get("iat"))
    return user_id


async def get_current_admin(
    authorization: Optional[str] = Header(default=None),
) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    data = decode_token(token)
    if not data.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin only")
    # The token's is_admin claim lives for the token's whole lifetime; check the
    # account too, so removing someone's admin rights (or blocking them) takes
    # effect immediately instead of when their token expires.
    from core import db  # lazy: core imports this module

    acct = await db.users.find_one({"id": data.get("sub")}, {"_id": 0, "is_admin": 1, "blocked": 1})
    if not acct or not acct.get("is_admin") or acct.get("blocked"):
        raise HTTPException(status_code=403, detail="Admin only")
    return data.get("sub")


async def optional_user_id(
    authorization: Optional[str] = Header(default=None),
) -> Optional[str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    try:
        token = authorization.split(" ", 1)[1].strip()
        data = decode_token(token)
        return data.get("sub")
    except HTTPException:
        return None
