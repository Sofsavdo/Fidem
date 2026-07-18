"""External services: Telegram Bot, CLICK payment, matching, helpers.

Telegram: this module is the ONLY place that reads TELEGRAM_BOT_TOKEN and
talks to api.telegram.org. Every other module (core.py, admin_bot.py,
routers/telegram_r.py) imports the token/helpers from here instead of
re-reading the env var and hand-rolling its own httpx calls - previously
three separate modules each defined their own TG_BOT_TOKEN/TG_API, which is
exactly how config drift (e.g. an admin id silently pointing at the wrong
value) creeps in unnoticed.
"""
from __future__ import annotations
import asyncio
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
_TG_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# Second, separate bot (Fidemadminbot) used only to open the admin panel as
# a Telegram Mini App and to receive its /start. Deliberately a distinct
# token/webhook/secret from the user-facing bot above - the admin bot must
# never be reachable by a regular user, and a shared token would mean any
# webhook payload for one bot could be replayed against the other.
# .strip(): a copy-pasted token picking up a trailing newline/space (a
# common paste mistake when setting a Railway variable) would otherwise
# silently make every call fail while still LOOKING configured (a non-empty
# string) to any check that only tests truthiness.
ADMIN_BOT_TOKEN = os.environ.get("ADMIN_BOT_TOKEN", "").strip()

CLICK_MERCHANT_ID = os.environ.get("CLICK_MERCHANT_ID", "")
CLICK_SERVICE_ID = os.environ.get("CLICK_SERVICE_ID", "")
CLICK_SECRET_KEY = os.environ.get("CLICK_SECRET_KEY", "")
CLICK_RETURN_URL = os.environ.get("CLICK_RETURN_URL", "")

# One pooled client for every Telegram API call in the process, instead of
# opening a fresh TCP+TLS connection per send - matters a lot once bulk
# passes (lifecycle nudges, winback, admin digest) fire dozens of sends back
# to back. Created lazily so import order never depends on an event loop
# already running.
_http_client: Optional[httpx.AsyncClient] = None


def _client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=20.0)
    return _http_client


async def _tg_call_as(token: str, method: str, **kwargs) -> Optional[httpx.Response]:
    """POST to a Telegram Bot API method for a given bot token, through the
    shared client, with a single capped-wait retry on HTTP 429 (Telegram's
    own rate-limit response, which carries the required backoff in
    `parameters.retry_after`)."""
    if not token:
        log.warning(f"bot token not set; skipping Telegram API call ({method})")
        return None
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        r = await _client().post(url, **kwargs)
        if r.status_code == 429:
            try:
                retry_after = int(r.json().get("parameters", {}).get("retry_after", 1))
            except Exception:
                retry_after = 1
            wait = min(max(retry_after, 1), 30)
            log.warning(f"Telegram {method} rate-limited, retrying once after {wait}s")
            await asyncio.sleep(wait)
            r = await _client().post(url, **kwargs)
        return r
    except Exception as e:
        log.error(f"Telegram {method} failed: {e}")
        return None


async def _tg_call(method: str, **kwargs) -> Optional[httpx.Response]:
    return await _tg_call_as(TELEGRAM_BOT_TOKEN, method, **kwargs)


async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """Send a message via Telegram Bot API. Returns True on success, False otherwise.

    No parse_mode: every caller sends plain human-typed text (notification
    copy, admin-authored announcement titles/text) with no intentional HTML
    formatting anywhere in the codebase. parse_mode="HTML" used to be set
    regardless, so any stray '<', '>' or '&' in that text (trivially common
    in free-form admin-typed announcements) made Telegram reject the whole
    message as unparsable HTML - and the failure was silent (see below),
    so it looked like the bot just never sent anything.
    """
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    r = await _tg_call("sendMessage", json=payload)
    if r is None:
        return False
    if r.status_code != 200:
        # Previously not logged at all - a non-exception failure (bad
        # chat_id, user blocked the bot, rate limit, malformed payload...)
        # was completely invisible; the caller went on to mark the
        # notification as delivered regardless.
        log.warning(f"Telegram sendMessage failed: {r.status_code} {r.text[:300]}")
    return r.status_code == 200


async def send_telegram_photo(chat_id: int, photo: bytes, caption: str, reply_markup: Optional[dict] = None) -> bool:
    import json as _json

    data = {"chat_id": str(chat_id), "caption": caption}
    if reply_markup:
        data["reply_markup"] = _json.dumps(reply_markup)
    r = await _tg_call("sendPhoto", data=data, files={"photo": ("receipt.jpg", photo)})
    if r is None:
        return False
    if r.status_code != 200:
        log.warning(f"Telegram sendPhoto failed: {r.status_code} {r.text[:200]}")
    return r.status_code == 200


async def answer_callback_query(callback_id: str, text: str) -> None:
    await _tg_call("answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})


async def edit_message_caption(chat_id: int, message_id: int, caption: str) -> None:
    """Rewrite the alert caption after a decision so the buttons disappear
    and the thread shows what happened."""
    await _tg_call(
        "editMessageCaption",
        json={"chat_id": chat_id, "message_id": message_id, "caption": caption},
    )


async def telegram_set_webhook(url: str, secret_token: str) -> bool:
    """secret_token is delivered back by Telegram on every webhook call as
    the `X-Telegram-Bot-Api-Secret-Token` header (Bot API 6.0+) - the
    intended way to authenticate inbound webhook calls. The previous
    implementation instead appended the secret as a `?secret=` URL query
    parameter, which leaks into access logs/proxies and isn't what Telegram
    itself verifies or expects."""
    r = await _tg_call("setWebhook", json={
        "url": url,
        "secret_token": secret_token,
        "allowed_updates": ["message", "callback_query"],
    })
    ok = r is not None and r.status_code == 200
    log.info(f"Telegram webhook set: {r.status_code if r else 'no response'} {r.text[:200] if r else ''}")
    return ok


async def telegram_set_menu_button(webapp_url: str) -> bool:
    r = await _tg_call("setChatMenuButton", json={
        "menu_button": {"type": "web_app", "text": "💖 FIDEM", "web_app": {"url": webapp_url}},
    })
    ok = r is not None and r.status_code == 200
    log.info(f"Telegram menu button set: {r.status_code if r else 'no response'} {r.text[:200] if r else ''}")
    return ok


# ---- Admin bot (Fidemadminbot) - same wire format, separate token/chat ----
async def send_admin_bot_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    r = await _tg_call_as(ADMIN_BOT_TOKEN, "sendMessage", json=payload)
    if r is None:
        return False
    if r.status_code != 200:
        log.warning(f"Admin bot sendMessage failed: {r.status_code} {r.text[:300]}")
    return r.status_code == 200


async def send_admin_bot_photo(chat_id: int, photo: bytes, caption: str, reply_markup: Optional[dict] = None) -> bool:
    import json as _json

    data = {"chat_id": str(chat_id), "caption": caption}
    if reply_markup:
        data["reply_markup"] = _json.dumps(reply_markup)
    r = await _tg_call_as(ADMIN_BOT_TOKEN, "sendPhoto", data=data, files={"photo": ("receipt.jpg", photo)})
    if r is None:
        return False
    if r.status_code != 200:
        log.warning(f"Admin bot sendPhoto failed: {r.status_code} {r.text[:200]}")
    return r.status_code == 200


async def answer_admin_callback_query(callback_id: str, text: str) -> None:
    await _tg_call_as(ADMIN_BOT_TOKEN, "answerCallbackQuery", json={"callback_query_id": callback_id, "text": text})


async def edit_admin_message_caption(chat_id: int, message_id: int, caption: str) -> None:
    await _tg_call_as(
        ADMIN_BOT_TOKEN,
        "editMessageCaption",
        json={"chat_id": chat_id, "message_id": message_id, "caption": caption},
    )


async def admin_bot_set_webhook(url: str, secret_token: str) -> bool:
    r = await _tg_call_as(ADMIN_BOT_TOKEN, "setWebhook", json={
        "url": url,
        "secret_token": secret_token,
        # callback_query: the P2P approve/reject inline buttons, once alerts
        # are unified onto this bot (see admin_bot.py's send_admin_alert*).
        "allowed_updates": ["message", "callback_query"],
    })
    ok = r is not None and r.status_code == 200
    log.info(f"Admin bot webhook set: {r.status_code if r else 'no response'} {r.text[:200] if r else ''}")
    return ok


async def admin_bot_set_menu_button(webapp_url: str) -> bool:
    r = await _tg_call_as(ADMIN_BOT_TOKEN, "setChatMenuButton", json={
        "menu_button": {"type": "web_app", "text": "🛠 Admin panel", "web_app": {"url": webapp_url}},
    })
    ok = r is not None and r.status_code == 200
    log.info(f"Admin bot menu button set: {r.status_code if r else 'no response'} {r.text[:200] if r else ''}")
    return ok


async def _tg_set_profile_field(token: str, method: str, field: str, value, language_code: str = "") -> bool:
    """Shared body for the setMyName/setMyDescription/setMyShortDescription/
    setMyCommands family - all four take one payload field plus an optional
    language_code and are called identically for both bots."""
    payload = {field: value}
    if language_code:
        payload["language_code"] = language_code
    r = await _tg_call_as(token, method, json=payload)
    ok = r is not None and r.status_code == 200
    if not ok:
        log.warning(f"Telegram {method}({language_code or 'default'}) failed: {r.status_code if r else 'no response'} {r.text[:200] if r else ''}")
    return ok


# ---- Bot profile (BotFather-equivalent, settable via API): name shown in
# chat header, description shown in the empty chat before /start, short
# description shown on the bot's profile page and in shared-link previews,
# and the "/" command menu. Every field supports a per-language variant
# (falls back to the languageless default for any client language Telegram
# doesn't have an explicit override for) - unlike the profile PHOTO, which
# Telegram only allows BotFather to set (`/setuserpic`), there is no Bot API
# method for it.
async def telegram_set_my_name(name: str, language_code: str = "") -> bool:
    return await _tg_set_profile_field(TELEGRAM_BOT_TOKEN, "setMyName", "name", name, language_code)


async def telegram_set_my_description(description: str, language_code: str = "") -> bool:
    return await _tg_set_profile_field(TELEGRAM_BOT_TOKEN, "setMyDescription", "description", description, language_code)


async def telegram_set_my_short_description(short_description: str, language_code: str = "") -> bool:
    return await _tg_set_profile_field(TELEGRAM_BOT_TOKEN, "setMyShortDescription", "short_description", short_description, language_code)


async def telegram_set_my_commands(commands: list[dict], language_code: str = "") -> bool:
    return await _tg_set_profile_field(TELEGRAM_BOT_TOKEN, "setMyCommands", "commands", commands, language_code)


async def admin_bot_set_my_short_description(short_description: str) -> bool:
    return await _tg_set_profile_field(ADMIN_BOT_TOKEN, "setMyShortDescription", "short_description", short_description)


async def admin_bot_set_my_description(description: str) -> bool:
    return await _tg_set_profile_field(ADMIN_BOT_TOKEN, "setMyDescription", "description", description)


async def admin_bot_set_my_commands(commands: list[dict]) -> bool:
    return await _tg_set_profile_field(ADMIN_BOT_TOKEN, "setMyCommands", "commands", commands)


async def get_bot_info(token: str) -> Optional[dict]:
    """Live validity check via Telegram's getMe - a non-empty token string
    proves nothing on its own (a typo'd or truncated token still passes any
    check that only tests truthiness, then fails silently on every real
    call). Returns the bot's own profile (id, username, ...) on success,
    None if the token is invalid or Telegram is unreachable."""
    if not token:
        return None
    r = await _tg_call_as(token, "getMe")
    if r is None or r.status_code != 200:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    return data.get("result") if data.get("ok") else None


# ---- CLICK Shop pay-link (Merchant API checkout link) ----
def click_pay_link(amount_uzs: int, transaction_param: str, return_url: Optional[str] = None) -> str:
    base = "https://my.click.uz/services/pay"
    q = {
        "service_id": CLICK_SERVICE_ID,
        "merchant_id": CLICK_MERCHANT_ID,
        "amount": amount_uzs,
        "transaction_param": transaction_param,
        "return_url": return_url or CLICK_RETURN_URL,
    }
    return f"{base}?{urlencode(q)}"


def click_md5(*parts) -> str:
    raw = "".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def verify_click_sign(form: dict, action: str) -> bool:
    """Validate CLICK Merchant API callback signature.
    Prepare sign: click_trans_id + service_id + SECRET_KEY + merchant_trans_id + amount + action + sign_time
    Complete sign: click_trans_id + service_id + SECRET_KEY + merchant_trans_id + merchant_prepare_id + amount + action + sign_time
    """
    sign = form.get("sign_string", "")
    sign_time = form.get("sign_time", "")
    click_trans_id = form.get("click_trans_id", "")
    merchant_trans_id = form.get("merchant_trans_id", "")
    amount = form.get("amount", "")
    if action == "0":  # PREPARE
        expected = click_md5(click_trans_id, CLICK_SERVICE_ID, CLICK_SECRET_KEY, merchant_trans_id, amount, action, sign_time)
    else:  # COMPLETE
        merchant_prepare_id = form.get("merchant_prepare_id", "")
        expected = click_md5(click_trans_id, CLICK_SERVICE_ID, CLICK_SECRET_KEY, merchant_trans_id, merchant_prepare_id, amount, action, sign_time)
    return expected == sign


# ---- Matching ----
def age_from_birth(birth_date_iso: str) -> int:
    try:
        bd = datetime.fromisoformat(birth_date_iso).date()
        today = datetime.now(timezone.utc).date()
        years = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))
        return max(0, years)
    except Exception:
        return 0


def compute_match(viewer: dict, candidate: dict, lang: str = "uz") -> tuple[int, list[str]]:
    """Compute match% (0-100) and list of human-readable reasons."""
    if lang not in ("uz", "ru", "en"):
        lang = "uz"

    def reason(key: str, **kwargs) -> str:
        templates = {
            "age_in_range": {
                "uz": "Yosh oralig'i ({age})",
                "ru": "Возраст в диапазоне ({age})",
                "en": "Age in range ({age})",
            },
            "marital": {
                "uz": "Oilaviy holat mos",
                "ru": "Семейное положение совпадает",
                "en": "Marital status matches",
            },
            "no_children": {
                "uz": "Farzandsiz",
                "ru": "Без детей",
                "en": "No children",
            },
            "has_children": {
                "uz": "Farzandli",
                "ru": "С детьми",
                "en": "Has children",
            },
            "height": {
                "uz": "Bo'y mos",
                "ru": "Рост подходит",
                "en": "Height compatible",
            },
            "religion": {
                "uz": "Din: {religion}",
                "ru": "Религия: {religion}",
                "en": "Religion: {religion}",
            },
            "goals_close": {
                "uz": "Maqsadlar yaqin",
                "ru": "Цели близки",
                "en": "Goals align well",
            },
            "goals_partial": {
                "uz": "Maqsadlar qisman mos",
                "ru": "Цели частично совпадают",
                "en": "Goals partially align",
            },
            "family_goal": {
                "uz": "Oila qurish maqsadi",
                "ru": "Цель — создание семьи",
                "en": "Family-building goal",
            },
            "interests": {
                "uz": "Qiziqishlar yaqin",
                "ru": "Интересы близки",
                "en": "Shared interests",
            },
        }
        tmpl = templates.get(key, {}).get(lang) or templates.get(key, {}).get("uz", key)
        return tmpl.format(**kwargs)

    score = 0
    reasons: list[str] = []

    v_age = age_from_birth(viewer.get("birth_date", "2000-01-01"))
    c_age = age_from_birth(candidate.get("birth_date", "2000-01-01"))

    # 1. Gender preference (mandatory)
    if viewer.get("search_gender") and viewer["search_gender"] == candidate.get("gender"):
        score += 5
    if candidate.get("search_gender") and candidate["search_gender"] == viewer.get("gender"):
        score += 5

    # 2. Age within viewer's search range (20 pts)
    a_min = viewer.get("search_age_min", 18)
    a_max = viewer.get("search_age_max", 60)
    if a_min <= c_age <= a_max:
        score += 20
        reasons.append(reason("age_in_range", age=c_age))
    elif abs(c_age - (a_min + a_max) / 2) <= 5:
        score += 10

    # 3. Region (20 pts)
    if viewer.get("region") and candidate.get("region"):
        if viewer.get("search_region", "any") in ("", "any", candidate["region"]):
            score += 10
            reasons.append(candidate["region"])
        if viewer["region"] == candidate["region"]:
            score += 10

    # 4. Marital status alignment (10 pts)
    if viewer.get("marital_status") == candidate.get("marital_status"):
        score += 10
        reasons.append(reason("marital"))

    # 5. Children alignment (10 pts)
    if viewer.get("has_children") == candidate.get("has_children"):
        score += 10
        if not candidate.get("has_children"):
            reasons.append(reason("no_children"))
        else:
            reasons.append(reason("has_children"))

    # 6. Height delta (10 pts) — prefer opposite-gender adult-typical
    vh = viewer.get("height_cm", 170)
    ch = candidate.get("height_cm", 170)
    if 5 <= abs(vh - ch) <= 30:
        score += 10
        reasons.append(reason("height"))
    elif abs(vh - ch) < 5:
        score += 5

    # 7. Religion (10 pts)
    if viewer.get("religion") and viewer.get("religion") == candidate.get("religion"):
        score += 10
        reasons.append(reason("religion", religion=candidate.get("religion")))

    # 8. Goal text & looking_for similarity (10 pts) — token overlap
    a = (viewer.get("looking_for") or "").lower()
    b = (candidate.get("looking_for") or "").lower()
    if a and b:
        a_tokens = set(t for t in a.split() if len(t) >= 3)
        b_tokens = set(t for t in b.split() if len(t) >= 3)
        if a_tokens and b_tokens:
            overlap = len(a_tokens & b_tokens) / max(1, len(a_tokens | b_tokens))
            if overlap >= 0.4:
                score += 10
                reasons.append(reason("goals_close"))
            elif overlap > 0:
                score += 5
                reasons.append(reason("goals_partial"))
            else:
                score += 2  # both have goal text — minor bonus
                reasons.append(reason("family_goal"))
        else:
            score += 3
    # Bio token overlap (5 pts)
    ba = (viewer.get("bio") or "").lower()
    bb = (candidate.get("bio") or "").lower()
    if ba and bb:
        ba_tokens = set(t for t in ba.split() if len(t) >= 4)
        bb_tokens = set(t for t in bb.split() if len(t) >= 4)
        if ba_tokens and bb_tokens:
            o = len(ba_tokens & bb_tokens) / max(1, len(ba_tokens | bb_tokens))
            if o >= 0.2:
                score += 5
                reasons.append(reason("interests"))

    return min(100, score), reasons[:6]


def match_label(score: int) -> str:
    if score >= 80:
        return "Juda mos"
    if score >= 60:
        return "Mos"
    if score >= 40:
        return "Qisman mos"
    return "Mos emas"


# ---- Completeness ----
PROFILE_FIELDS = [
    "gender", "birth_date", "country", "region", "district",
    "marital_status", "has_children", "height_cm", "weight_kg",
    "education", "profession", "religion", "looking_for",
    "search_region", "photo_url", "bio", "name",
]


def compute_completeness(user: dict) -> int:
    filled = 0
    for f in PROFILE_FIELDS:
        v = user.get(f)
        if v not in (None, "", 0) or (isinstance(v, bool)):
            filled += 1
    return int(filled / len(PROFILE_FIELDS) * 100)


# ---- Last-active formatting ----
def last_active_minutes(dt: Optional[datetime]) -> int:
    """Return total minutes since `dt`. -1 if unknown/null. 0 if < 1 min."""
    if not dt:
        return -1
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return -1
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = (datetime.now(timezone.utc) - dt).total_seconds()
    return max(0, int(diff / 60))


def last_active_label(dt: Optional[datetime]) -> str:
    """Legacy label, retained for backward compatibility. Frontend should use last_active_minutes."""
    mins = last_active_minutes(dt)
    if mins < 0:
        return "—"
    if mins < 5:
        return "Online"
    if mins < 60:
        return f"{mins}m"
    if mins < 1440:
        return f"{mins // 60}h"
    return f"{mins // 1440}d"


def is_online(dt: Optional[datetime]) -> bool:
    if not dt:
        return False
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except Exception:
            return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds() < 300
