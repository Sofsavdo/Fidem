"""AI services. Compatibility reports, icebreakers and moderation are
lightweight template/regex fallbacks (no model call). Face verification is
a real Claude vision call - see verify_face_photo below.
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

_client = None


def _get_client():
    global _client
    if _client is None:
        import anthropic
        _client = anthropic.AsyncAnthropic()
    return _client


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


# ---------- 2) Icebreakers ----------
async def personalized_icebreakers(viewer: dict, candidate: dict, lang: str = "uz") -> list[str]:
    return _fallback_icebreakers(lang)


def _fallback_icebreakers(lang: str) -> list[str]:
    pools = {
        "uz": [
            "Profilingizdagi eng qiziq jihat haqida gapirib bering?",
            "Hayotda nimaga ko'proq qiymat berasiz?",
            "Ideal dam olish kuni qanday o'tadi?",
        ],
        "ru": [
            "Что в вашем профиле самое интересное?",
            "Что вы цените больше всего в жизни?",
            "Как выглядит ваш идеальный выходной?",
        ],
        "en": [
            "What's the most interesting thing about you?",
            "What do you value most in life?",
            "What does your ideal day off look like?",
        ],
    }
    return pools.get(lang, pools["uz"])


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
