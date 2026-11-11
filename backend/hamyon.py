"""Hamyon API (hamyon-api.uz) card-transfer payments.

How it works: we ask Hamyon to open a payment for an amount; it answers with
a card number. The user transfers exactly that amount to the card, Hamyon
sees the money arrive and POSTs the result (paid / cancel after 5 minutes)
to our complete_url. A payment is recognised by its AMOUNT, so one shop can
never have two open payments with the same amount at once - when an amount
is busy we add 1 so'm and try again (the user pays e.g. 79 001 instead of
79 000).

Settings (Railway, backend service):
  HAMYON_SHOP_ID   - shop_id from the Hamyon bot
  HAMYON_SHOP_KEY  - shop_key from the Hamyon bot (secret)
  HAMYON_BASE_URL  - optional, defaults to https://hamyon-api.uz
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os

import httpx

log = logging.getLogger("fidem.hamyon")

HAMYON_BASE_URL = os.environ.get("HAMYON_BASE_URL", "https://hamyon-api.uz").strip().rstrip("/")
HAMYON_SHOP_ID = os.environ.get("HAMYON_SHOP_ID", "").strip()
HAMYON_SHOP_KEY = os.environ.get("HAMYON_SHOP_KEY", "").strip()

# How many 1-so'm steps to try when an amount already has an open payment.
MAX_AMOUNT_BUMPS = 30


class HamyonError(Exception):
    """Hamyon refused the request or could not be reached."""


def hamyon_enabled() -> bool:
    return bool(HAMYON_SHOP_ID and HAMYON_SHOP_KEY)


def hamyon_sign(payment_id: str, amount) -> str:
    raw = f"{HAMYON_SHOP_ID}{payment_id}{amount}{HAMYON_SHOP_KEY}"
    return hashlib.md5(raw.encode()).hexdigest()


def verify_hamyon_sign(form: dict) -> bool:
    """sign = md5(shop_id + payment_id + amount + shop_key), with the values
    exactly as Hamyon sent them. The shop_id in the form must be ours too."""
    if not hamyon_enabled():
        return False
    if str(form.get("shop_id", "")).strip() != HAMYON_SHOP_ID:
        return False
    calc = hamyon_sign(str(form.get("payment_id", "")), str(form.get("amount", "")))
    return hmac.compare_digest(calc, str(form.get("sign", "")).strip().lower())


def _is_amount_busy(err: str) -> bool:
    e = (err or "").lower()
    return "ochiq" in e and "summa" in e


async def _post(path: str, data: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=15.0) as cl:
            r = await cl.post(f"{HAMYON_BASE_URL}{path}", data=data)
    except httpx.HTTPError as e:
        raise HamyonError(f"connection: {type(e).__name__}") from e
    try:
        body = r.json()
    except ValueError:
        body = {}
    if r.status_code >= 400 or (isinstance(body, dict) and body.get("error")):
        raise HamyonError(str((body or {}).get("error") or f"HTTP {r.status_code}"))
    return body if isinstance(body, dict) else {}


async def create_hamyon_payment(order_id: str, amount: int, busy_amounts: set[int] | None = None) -> dict:
    """Open a payment, stepping the amount up by 1 so'm while it is taken.
    Returns Hamyon's answer plus "amount" = the exact sum the user must pay."""
    busy = set(busy_amounts or ())
    candidate = amount
    last_err = ""
    for _ in range(MAX_AMOUNT_BUMPS):
        while candidate in busy:
            candidate += 1
        try:
            res = await _post("/payment/create", {
                "shop_id": HAMYON_SHOP_ID,
                "shop_key": HAMYON_SHOP_KEY,
                "amount": candidate,
                "order_id": order_id,
            })
        except HamyonError as e:
            last_err = str(e)
            if _is_amount_busy(last_err):
                busy.add(candidate)
                continue
            raise
        if not res.get("payment_id") or not res.get("card"):
            raise HamyonError("incomplete answer")
        res["amount"] = int(res.get("amount") or candidate)
        return res
    raise HamyonError(last_err or "no free amount")


async def hamyon_payment_status(payment_id: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10.0) as cl:
            r = await cl.get(f"{HAMYON_BASE_URL}/payment/status", params={"payment_id": payment_id})
        body = r.json()
    except (httpx.HTTPError, ValueError) as e:
        raise HamyonError(f"status: {type(e).__name__}") from e
    if r.status_code >= 400 or not isinstance(body, dict) or body.get("error"):
        raise HamyonError(str((body or {}).get("error") if isinstance(body, dict) else "") or f"HTTP {r.status_code}")
    return body


async def cancel_hamyon_payment(payment_id: str) -> None:
    await _post("/payment/cancel", {"payment_id": payment_id, "shop_key": HAMYON_SHOP_KEY})
