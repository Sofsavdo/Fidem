"""External services: Telegram Bot, CLICK payment, matching, helpers."""
from __future__ import annotations
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_API = f"https://api.telegram.org/bot{TG_BOT_TOKEN}"

CLICK_MERCHANT_ID = os.environ.get("CLICK_MERCHANT_ID", "")
CLICK_SERVICE_ID = os.environ.get("CLICK_SERVICE_ID", "")
CLICK_SECRET_KEY = os.environ.get("CLICK_SECRET_KEY", "")
CLICK_RETURN_URL = os.environ.get("CLICK_RETURN_URL", "")


async def send_telegram_message(chat_id: int, text: str, reply_markup: Optional[dict] = None) -> bool:
    """Send a message via Telegram Bot API. Returns True on success, False otherwise."""
    if not TG_BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set; skipping notification")
        return False
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(f"{TG_API}/sendMessage", json=payload)
            return r.status_code == 200
    except Exception as e:
        log.error(f"Telegram send failed: {e}")
        return False


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
