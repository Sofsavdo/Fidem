"""AI services. Compatibility reports and moderation are lightweight
template/regex fallbacks (no model call). Face verification, verification-
document review, and P2P receipt review are real vision calls (Gemini
primary, Claude fallback) - see verify_face_photo, analyze_verification,
and analyze_p2p_receipt below.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import re

import httpx

log = logging.getLogger("fidem.ai")

ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")

# Primary vision provider: Gemini (Google AI Studio). All verification and
# photo checks go through it when GEMINI_API_KEY is set; the Anthropic path
# stays as an automatic fallback.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic()
    return _client


async def _gemini_json(prompt: str, images: list[tuple[str, str]], schema: dict) -> dict:
    """One Gemini generateContent call returning strict JSON.

    images: list of (media_type, base64_data). schema: Gemini response
    schema (uppercase type names). Raises on any transport/parse problem -
    callers decide the fallback.
    """
    parts = [{"inlineData": {"mimeType": mt, "data": b64}} for mt, b64 in images]
    parts.append({"text": prompt})
    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": schema,
            "maxOutputTokens": 500,
            "temperature": 0,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    async with httpx.AsyncClient(timeout=30.0) as cl:
        r = await cl.post(url, params={"key": GEMINI_API_KEY}, json=body)
        r.raise_for_status()
        data = r.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(text)


# ---------- 1) Compatibility narrative ----------
async def compatibility_report(
    viewer: dict,
    candidate: dict,
    big5_viewer: dict,
    big5_candidate: dict,
    score: int,
    lang: str = "uz",
) -> dict:
    return _fallback_report(score, lang)


def _fallback_report(score: int, lang: str) -> dict:
    base = {
        "uz": {
            "summary": f"Moslik darajasi: {score}/100. Profil ma'lumotlari asosida munosib nomzod.",
            "strengths": ["Asosiy qadriyatlar mos", "Hududiy yaqinlik", "Maqsad — oila qurish"],
            "watch_outs": ["Yashash tarzi va kelajak rejalarini batafsil muhokama qiling"],
            "conversation_starters": [
                "Hayotda eng ko'p ahamiyat beradigan 3 narsa nima?",
                "5 yildan keyin o'zingizni qayerda ko'rasiz?",
                "Idealdagi oila qanday bo'lishi kerak deb o'ylaysiz?",
            ],
        },
        "ru": {
            "summary": f"Совместимость: {score}/100. Достойный кандидат по профилю.",
            "strengths": ["Совпадение ценностей", "Близость по региону", "Цель — создать семью"],
            "watch_outs": ["Обсудите образ жизни и планы на будущее"],
            "conversation_starters": [
                "Какие 3 вещи для вас важнее всего в жизни?",
                "Где вы видите себя через 5 лет?",
                "Какой по-вашему идеальная семья?",
            ],
        },
        "en": {
            "summary": f"Compatibility: {score}/100. Solid match based on profile.",
            "strengths": ["Aligned values", "Geographic proximity", "Marriage-focused goals"],
            "watch_outs": ["Discuss lifestyle and future plans in depth"],
            "conversation_starters": [
                "What are the 3 most important things in your life?",
                "Where do you see yourself in 5 years?",
                "What does an ideal family look like to you?",
            ],
        },
    }
    out = base.get(lang, base["uz"]).copy()
    out["score"] = score
    out["ai_generated"] = False
    return out


# ---------- 3) Moderation ----------
BAD_WORDS_UZ = [
    "axmoq", "ahmoq", "tentak", "jinni", "xromoy", "fohisha", "qahba", "jalab",
    "pisi", "kuc̈hak", "yotamiz", "yotaylik", "yotib", "ko'kragim", "ko'krak rasm",
    "rasm berasanmi",
]

# Off-platform contact exchange. This is the free tier's main monetization
# leak: two free users use the weekly free chat to swap Telegram/phone and
# leave without ever paying. Detection is a plain algorithm (regex), no AI:
#   - phone numbers in common local formats (+998..., 90 123 45 67, digit runs)
#   - t.me / wa.me / instagram.com links and @usernames
#   - "let's move to telegram/instagram/whatsapp" keywords and
#     number-begging phrases in Uzbek/Russian.
# chat_r decides what a hit means: FREE senders are blocked with an upsell;
# PAID senders are allowed (the frontend shows a small confirm first).
_CONTACT_PATTERNS = [
    r"\+?998[\s\-]?\d{2}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",  # +998 xx xxx xx xx
    r"(?<!\d)\d{2}[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2}(?!\d)",      # 90 123 45 67
    r"(?<!\d)\d{9,12}(?!\d)",                                     # bare digit runs
    r"t\.me/|telegram\.me/|wa\.me/|instagram\.com/|ig\.me/",
    r"@[a-z0-9_.]{4,}",
    r"\btelegram\w*", r"\btg\b|\btg\s*ga\b", r"\binsta\w*",
    r"\bwhats?app\w*", r"\bvatsap\w*", r"\bviber\w*", r"\bimo\b",
    r"raqam\w*\s*(?:ber|yubor|yoz|tashla)", r"\bnomer\w*",
    r"телефон\w*", r"номер\w*", r"телеграм\w*", r"инстаграм\w*", r"ватсап\w*",
    # Spelled-out digit runs ("to'qson bir uch yetti...", "девять ноль один"):
    # 4+ consecutive number words is virtually always a dictated phone number.
    r"(?:\b(?:nol|bir|ikki|uch|to[':’ʻ`]?rt|besh|olti|yetti|sakkiz|to[':’ʻ`]?qqiz|o[':’ʻ`]?n|yigirma|o[':’ʻ`]?ttiz|qirq|ellik|oltmish|yetmish|sakson|to[':’ʻ`]?qson|yuz)\b[\s,.-]*){4,}",
    r"(?:\b(?:ноль|один|одна|два|две|три|четыре|пять|шесть|семь|восемь|девять|десять|двадцать|тридцать|сорок|пятьдесят|шестьдесят|семьдесят|восемьдесят|девяносто|сто)\b[\s,.-]*){4,}",
]
_CONTACT_RE = re.compile("|".join(f"(?:{p})" for p in _CONTACT_PATTERNS), re.IGNORECASE)


def detect_contact_info(text: str) -> bool:
    """True when the message looks like an attempt to exchange off-platform
    contact info (phone / telegram / instagram / whatsapp / usernames)."""
    return bool(_CONTACT_RE.search((text or "").lower()))


def quick_moderation(text: str) -> tuple[bool, str]:
    t = (text or "").lower()

    for bw in BAD_WORDS_UZ:
        if bw in t:
            return False, "Sizning xabaringizda noo'rin so'zlar bor. Iltimos, hurmatli bo'ling."

    return True, ""


async def ai_moderation(text: str) -> tuple[bool, str]:
    return quick_moderation(text)


# ---------- 4) Face verification ----------
_FACE_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "valid": {"type": "boolean"},
        "code": {
            "type": "string",
            "enum": ["ok", "no_face", "multiple_faces", "not_a_photo", "low_quality", "inappropriate"],
        },
        "reason_uz": {"type": "string"},
    },
    "required": ["valid", "code", "reason_uz"],
    "additionalProperties": False,
}


async def verify_face_photo(image_url: str = "", image_base64: str = "") -> dict:
    """Verify a submitted profile photo actually shows a single real human face.

    Fails closed: any failure to load the image or reach the verification
    model returns valid=False rather than silently approving, since this
    result gates the "verified" badge and downstream trust/withdrawal checks.
    """
    try:
        media_type, data_b64 = await _load_image_b64(image_url, image_base64)
    except Exception as e:
        log.warning("face_verify: could not load photo: %s", e)
        return {"valid": False, "code": "not_a_photo", "reason": "Rasmni ochib bo'lmadi", "ai_generated": False}

    _prompt = (
        "This photo was submitted to a dating/marriage platform for profile-photo "
        "verification. Check: (1) it shows exactly one real human face, clearly "
        "visible and in focus - not zero faces, not a group photo; (2) it is an actual "
        "photograph, not a screenshot, drawing, meme, logo, or AI-generated image; "
        "(3) it contains no nudity or sexually explicit content. Respond with the "
        "required JSON only. reason_uz should be a short explanation in Uzbek."
    )

    # Primary: Gemini
    if GEMINI_API_KEY:
        try:
            parsed = await _gemini_json(
                _prompt,
                [(media_type, data_b64)],
                {
                    "type": "OBJECT",
                    "properties": {
                        "valid": {"type": "BOOLEAN"},
                        "code": {"type": "STRING", "enum": ["ok", "no_face", "multiple_faces", "not_a_photo", "low_quality", "inappropriate"]},
                        "reason_uz": {"type": "STRING"},
                    },
                    "required": ["valid", "code", "reason_uz"],
                },
            )
            valid = bool(parsed.get("valid"))
            return {
                "valid": valid,
                "code": parsed.get("code") or ("ok" if valid else "not_a_photo"),
                "reason": parsed.get("reason_uz") or "",
                "ai_generated": True,
            }
        except Exception as e:
            log.warning("face_verify: gemini call failed, trying fallback: %s", e)

    try:
        client = _get_client()
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            output_config={"format": {"type": "json_schema", "schema": _FACE_VERIFY_SCHEMA}},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data_b64}},
                    {
                        "type": "text",
                        "text": (
                            "This photo was submitted to a dating/marriage platform for profile-photo "
                            "verification. Check: (1) it shows exactly one real human face, clearly "
                            "visible and in focus - not zero faces, not a group photo; (2) it is an actual "
                            "photograph, not a screenshot, drawing, meme, logo, or AI-generated image; "
                            "(3) it contains no nudity or sexually explicit content. Respond with the "
                            "required JSON only. reason_uz should be a short explanation in Uzbek."
                        ),
                    },
                ],
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        parsed = json.loads(text) if text else {}
        valid = bool(parsed.get("valid"))
        return {
            "valid": valid,
            "code": parsed.get("code") or ("ok" if valid else "not_a_photo"),
            "reason": parsed.get("reason_uz") or "",
            "ai_generated": True,
        }
    except Exception as e:
        log.warning("face_verify: verification call failed: %s", e)
        return {
            "valid": False,
            "code": "verification_unavailable",
            "reason": "Tekshiruv xizmati vaqtincha ishlamayapti. Birozdan so'ng qayta urinib ko'ring.",
            "ai_generated": False,
        }


# ---------- 6) P2P top-up receipt review ----------
_P2P_SCHEMA_GEMINI = {
    "type": "OBJECT",
    "properties": {
        "verdict": {"type": "STRING", "enum": ["approve", "reject", "unsure"]},
        "confidence": {"type": "NUMBER"},
        "amount_visible": {"type": "NUMBER"},
        "reason_uz": {"type": "STRING"},
    },
    "required": ["verdict", "confidence", "amount_visible", "reason_uz"],
}


async def analyze_p2p_receipt(image_url: str, claimed_amount: int) -> dict:
    """AI review of a P2P (card-transfer) top-up receipt screenshot.

    This can only judge whether the IMAGE plausibly shows a genuine bank/
    payment-app transfer confirmation matching the claimed amount - it has
    no way to confirm the money actually landed in the real bank account
    (no banking API access), so it deliberately stays conservative: unsure
    or any sign of tampering/mismatch/reuse must fall through to a human,
    never verdict=approve. Never raises - a failure returns verdict=unsure
    so the request simply stays in the admin queue exactly as before this
    feature existed.
    """
    try:
        media_type, data_b64 = await _load_image_b64(image_url, "")
    except Exception as e:
        log.warning("p2p_receipt: could not load image: %s", e)
        return {"verdict": "unsure", "confidence": 0, "reason": "Rasmni ochib bo'lmadi", "ai_generated": False}

    prompt = (
        "This is a payment receipt screenshot submitted by a user claiming they "
        f"transferred {claimed_amount} UZS (Uzbek so'm) by bank card to top up their "
        "balance on a dating platform. Carefully assess whether this looks like a "
        "genuine, unedited screenshot from a real Uzbek bank or payment app (Click, "
        "Payme, Uzcard, Humo, or a bank's own app) showing a SUCCESSFUL completed "
        "transfer - not a pending/failed one, not a balance-check screen, not an "
        "unrelated photo, not an obviously reused/duplicate-looking or edited image. "
        "Read whatever amount is visible in the screenshot into amount_visible (0 if "
        "you cannot read one). Only use verdict=\"approve\" if you are genuinely "
        "confident this is a real successful transfer AND the visible amount is "
        "reasonably close to the claimed amount. Use verdict=\"reject\" only if "
        "something is clearly wrong (unrelated image, failed/pending transfer, amount "
        "far off). Use verdict=\"unsure\" for anything ambiguous, low quality, or that "
        "you're not confident about - this is the safe default, since a human reviews "
        "every unsure/reject case anyway. Respond with the required JSON only; "
        "reason_uz should be a short explanation in Uzbek."
    )

    if GEMINI_API_KEY:
        try:
            parsed = await _gemini_json(prompt, [(media_type, data_b64)], _P2P_SCHEMA_GEMINI)
            verdict = parsed.get("verdict") if parsed.get("verdict") in ("approve", "reject", "unsure") else "unsure"
            return {
                "verdict": verdict,
                "confidence": int(parsed.get("confidence") or 0),
                "amount_visible": parsed.get("amount_visible") or 0,
                "reason": parsed.get("reason_uz") or "",
                "ai_generated": True,
            }
        except Exception as e:
            log.warning("p2p_receipt: gemini call failed, trying fallback: %s", e)

    try:
        client = _get_client()
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            output_config={"format": {"type": "json_schema", "schema": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": ["approve", "reject", "unsure"]},
                    "confidence": {"type": "number"},
                    "amount_visible": {"type": "number"},
                    "reason_uz": {"type": "string"},
                },
                "required": ["verdict", "confidence", "amount_visible", "reason_uz"],
                "additionalProperties": False,
            }}},
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": data_b64}},
                    {"type": "text", "text": prompt},
                ],
            }],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        parsed = json.loads(text) if text else {}
        verdict = parsed.get("verdict") if parsed.get("verdict") in ("approve", "reject", "unsure") else "unsure"
        return {
            "verdict": verdict,
            "confidence": int(parsed.get("confidence") or 0),
            "amount_visible": parsed.get("amount_visible") or 0,
            "reason": parsed.get("reason_uz") or "",
            "ai_generated": True,
        }
    except Exception as e:
        log.warning("p2p_receipt: no provider available: %s", e)
        return {"verdict": "unsure", "confidence": 0, "amount_visible": 0, "reason": "", "ai_generated": False}


async def _load_image_b64(image_url: str, image_base64: str) -> tuple[str, str]:
    if image_base64:
        raw = image_base64
        if raw.startswith("data:"):
            header, _, raw = raw.partition(",")
            media_type = header.split(";")[0].replace("data:", "") or "image/jpeg"
        else:
            media_type = _sniff_media_type(raw)
        return media_type, raw

    if not image_url:
        raise ValueError("no image provided")

    # Internal /api/files/ URLs require our own JWT to fetch, which an
    # external image fetcher can't present - read the bytes directly from
    # our own storage instead of asking Claude to fetch the URL.
    m = re.search(r"/api/files/(.+)$", image_url)
    if m:
        from storage import get_object
        data, content_type = await get_object(m.group(1))
        return content_type or "image/jpeg", base64.b64encode(data).decode()

    async with httpx.AsyncClient(timeout=15.0) as cl:
        r = await cl.get(image_url)
        r.raise_for_status()
        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0]
        return content_type, base64.b64encode(r.content).decode()


def _sniff_media_type(b64: str) -> str:
    head = b64[:12]
    if head.startswith("iVBOR"):
        return "image/png"
    if head.startswith("R0lGOD"):
        return "image/gif"
    if head.startswith("UklGR"):
        return "image/webp"
    return "image/jpeg"


# ---------- 5) Verification review (selfie / identity / financial) ----------
_VERIF_PROMPTS = {
    "selfie": (
        "A dating-platform user submitted a verification selfie. "
        "{profile_hint}Check: the proof image shows one real, live person "
        "(a fresh selfie - not a photo of a screen, not a downloaded/celebrity "
        "image, not AI-generated){match_clause}. Respond JSON only; reason_uz = short Uzbek explanation."
    ),
    "identity": (
        "A dating-platform user submitted a photo as proof of identity. "
        "Check: a real government-style ID document is clearly visible "
        "(structured fields, portrait photo, official layout) - not a random "
        "photo, meme or screenshot. Do NOT transcribe any personal data. "
        "Respond JSON only; reason_uz = short Uzbek explanation."
    ),
    "financial": (
        "A dating-platform user submitted a photo as proof of financial "
        "standing (property, car, business, income document). Check: the "
        "image plausibly shows such an asset/document and is not junk, a "
        "meme, or an obviously downloaded stock image. This is a plausibility "
        "check, not a forensic audit. Respond JSON only; reason_uz = short "
        "Uzbek explanation."
    ),
}

_VERIF_SCHEMA_GEMINI = {
    "type": "OBJECT",
    "properties": {
        "verdict": {"type": "STRING", "enum": ["approve", "reject", "unsure"]},
        "confidence": {"type": "NUMBER"},
        "reason_uz": {"type": "STRING"},
    },
    "required": ["verdict", "confidence", "reason_uz"],
}


async def analyze_verification(kind: str, images: list[tuple[str, str]], has_profile_photo: bool = False) -> dict:
    """AI review of a verification submission.

    images: [(media_type, b64), ...] - for selfies, the user's profile photo
    first (when available) then the proof, so the model can face-match.
    Returns {"verdict": approve|reject|unsure, "confidence": 0-100,
    "reason": uz-text, "ai_generated": bool}. Never raises: any failure
    returns verdict=unsure so the item simply stays in the admin queue.
    """
    prompt_tpl = _VERIF_PROMPTS.get(kind) or _VERIF_PROMPTS["financial"]
    prompt = prompt_tpl.format(
        profile_hint="Image 1 is their existing profile photo; image 2 is the new verification selfie. " if has_profile_photo else "",
        match_clause=" AND clearly the same person as the profile photo" if has_profile_photo else "",
    ) if kind == "selfie" else prompt_tpl

    if GEMINI_API_KEY:
        try:
            parsed = await _gemini_json(prompt, images, _VERIF_SCHEMA_GEMINI)
            verdict = parsed.get("verdict") if parsed.get("verdict") in ("approve", "reject", "unsure") else "unsure"
            return {
                "verdict": verdict,
                "confidence": int(parsed.get("confidence") or 0),
                "reason": parsed.get("reason_uz") or "",
                "ai_generated": True,
            }
        except Exception as e:
            log.warning("analyze_verification: gemini failed: %s", e)

    # Fallback: Claude vision (if configured)
    try:
        client = _get_client()
        content = [{"type": "image", "source": {"type": "base64", "media_type": mt, "data": b64}} for mt, b64 in images]
        content.append({"type": "text", "text": prompt})
        response = await client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=300,
            output_config={"format": {"type": "json_schema", "schema": {
                "type": "object",
                "properties": {
                    "verdict": {"type": "string", "enum": ["approve", "reject", "unsure"]},
                    "confidence": {"type": "number"},
                    "reason_uz": {"type": "string"},
                },
                "required": ["verdict", "confidence", "reason_uz"],
                "additionalProperties": False,
            }}},
            messages=[{"role": "user", "content": content}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        parsed = json.loads(text) if text else {}
        verdict = parsed.get("verdict") if parsed.get("verdict") in ("approve", "reject", "unsure") else "unsure"
        return {
            "verdict": verdict,
            "confidence": int(parsed.get("confidence") or 0),
            "reason": parsed.get("reason_uz") or "",
            "ai_generated": True,
        }
    except Exception as e:
        log.warning("analyze_verification: no provider available: %s", e)
        return {"verdict": "unsure", "confidence": 0, "reason": "", "ai_generated": False}
