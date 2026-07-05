"""Authentication helpers: Telegram WebApp + JWT."""
from __future__ import annotations
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

# Validate JWT_SECRET in production
if os.environ.get("ENV") == "production" and JWT_SECRET == "dev-secret":
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


# ---- FastAPI dependency to extract user from Authorization header ----
async def get_current_user_id(authorization: Optional[str] = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    data = decode_token(token)
    user_id = data.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
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
