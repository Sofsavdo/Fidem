"""AI services powered by Emergent LLM (used for compatibility reports, icebreakers, moderation)."""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Optional

from emergentintegrations.llm.chat import LlmChat, UserMessage

log = logging.getLogger("fidem.ai")

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")
DEFAULT_PROVIDER = "openai"
DEFAULT_MODEL = "gpt-4o"   # multilingual, fast, good for Uzbek/Russian/English


def _new_chat(session_id: str, system_message: str) -> Optional[LlmChat]:
    if not EMERGENT_LLM_KEY:
        log.warning("EMERGENT_LLM_KEY not set; AI features disabled")
        return None
    try:
        return LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=session_id,
            system_message=system_message,
        ).with_model(DEFAULT_PROVIDER, DEFAULT_MODEL)
    except Exception as exc:
        log.error(f"LlmChat init failed: {exc}")
        return None


async def _send(chat: LlmChat, prompt: str) -> str:
    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        return str(resp).strip()
    except Exception as exc:
        log.error(f"LLM send failed: {exc}")
        return ""


# ---------- 1) Compatibility narrative ----------
async def compatibility_report(viewer: dict, candidate: dict, big5_viewer: dict, big5_candidate: dict, score: int, lang: str = "uz") -> dict:
    """Generate AI compatibility narrative based on Big 5 + profiles."""
    lang_label = {"uz": "o'zbek tilida", "ru": "на русском языке", "en": "in English"}.get(lang, "o'zbek tilida")
    sys = (
        "Siz jiddiy munosabat va oila qurish platformasida professional moslik analitiksiz. "
        "Ikki kishining shaxsiyat profillarini (Big5 / OCEAN) va asosiy ma'lumotlarini tahlil qiling. "
        "Strikt JSON formatda javob bering: "
        '{"summary": "qisqa xulosa (2-3 jumla)", "strengths": ["3 ta moslik nuqtasi"], '
        '"watch_outs": ["1-2 ta e\'tibor beriladigan jihat"], "conversation_starters": ["3 ta uchrashuv savoli"]}. '
        f"Hozirgi tilda javob bering: {lang_label}. Hech qanday qo'shimcha matn yo'q, faqat JSON."
    )
    chat = _new_chat(session_id=f"compat-{viewer.get('id')}-{candidate.get('id')}", system_message=sys)
    if not chat:
        return _fallback_report(score, lang)

    payload = {
        "score": score,
        "viewer": {
            "name": viewer.get("name"),
            "age": _safe_age(viewer),
            "gender": viewer.get("gender"),
            "region": viewer.get("region"),
            "profession": viewer.get("profession"),
            "religion": viewer.get("religion"),
            "looking_for": viewer.get("looking_for"),
            "big5": big5_viewer,
        },
        "candidate": {
            "name": candidate.get("name"),
            "age": _safe_age(candidate),
            "gender": candidate.get("gender"),
            "region": candidate.get("region"),
            "profession": candidate.get("profession"),
            "religion": candidate.get("religion"),
            "looking_for": candidate.get("looking_for"),
            "big5": big5_candidate,
        },
    }
    prompt = (
        f"Quyidagi ma'lumotlar asosida moslik hisobotini tayyorlang. "
        f"Profil: {json.dumps(payload, ensure_ascii=False)}"
    )
    raw = await _send(chat, prompt)
    parsed = _extract_json(raw)
    if not parsed:
        return _fallback_report(score, lang)
    parsed["score"] = score
    parsed["ai_generated"] = True
    return parsed


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
    out = base.get(lang, base["uz"])
    out["score"] = score
    out["ai_generated"] = False
    return out


# ---------- 2) AI Icebreakers ----------
async def personalized_icebreakers(viewer: dict, candidate: dict, lang: str = "uz") -> list[str]:
    lang_label = {"uz": "o'zbek tilida", "ru": "на русском языке", "en": "in English"}.get(lang, "o'zbek tilida")
    sys = (
        "Siz jiddiy tanishuv platformasi uchun ilk suhbat savollarini tayyorlovchi mutaxassissiz. "
        "Savollar samimiy, hurmatli, qiziqarli bo'lsin. JSON array qaytaring: [\"savol1\", \"savol2\", \"savol3\"]. "
        f"Til: {lang_label}. Faqat JSON array, boshqa matn yo'q."
    )
    chat = _new_chat(session_id=f"ice-{viewer.get('id','x')}-{candidate.get('id','y')}", system_message=sys)
    if not chat:
        return _fallback_icebreakers(lang)
    info = {
        "candidate_name": candidate.get("name"),
        "candidate_profession": candidate.get("profession"),
        "candidate_region": candidate.get("region"),
        "candidate_looking_for": candidate.get("looking_for"),
        "viewer_name": viewer.get("name"),
        "viewer_profession": viewer.get("profession"),
    }
    raw = await _send(chat, f"Profile: {json.dumps(info, ensure_ascii=False)}. 3 ta shaxsiy savol tayyorlang.")
    arr = _extract_json(raw)
    if isinstance(arr, list) and arr:
        return [str(q) for q in arr[:5]]
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


# ---------- 3) AI Moderation ----------
BAD_WORDS_UZ = [
    # Profanity / sexual / hate — minimal seed list (extendable)
    "axmoq", "ahmoq", "tentak", "jinni", "xromoy", "fohisha", "qahba", "jalab",
    "pisi", "kuc̈hak", "yotamiz", "yotaylik", "yotib", "telefon raqam", "raqam yuboring",
    "instagramga", "tg ga", "telegramga", "ko'kragim", "ko'krak rasm", "rasm berasanmi",
]
# Quick fast-path: hard-block obvious slurs / scam markers


def quick_moderation(text: str) -> tuple[bool, str]:
    """Returns (is_allowed, reason)."""
    t = (text or "").lower()
    # 1. external contact spam
    if re.search(r"\+?998\s*\d{2}[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}", t):
        return False, "Telefon raqamlarni almashish chatda ruxsat etilmagan. Avval tanishing."
    if re.search(r"@[a-z0-9_]{4,}", t):
        return False, "Tashqi havolalar ruxsat etilmagan. Iltimos, FIDEM ichida suhbatlashing."
    # 2. crude profanity list
    for bw in BAD_WORDS_UZ:
        if bw in t:
            return False, "Sizning xabaringizda noo'rin so'zlar bor. Iltimos, hurmatli bo'ling."
    return True, ""


async def ai_moderation(text: str) -> tuple[bool, str]:
    """Optional AI deep-check (used when quick passes but message is suspicious or > 200 chars)."""
    if len(text) < 12:
        return True, ""
    sys = (
        "Siz jiddiy tanishuv platformasi uchun moderatorisz. Berilgan xabar ruxsat etilganmi? "
        'JSON qaytaring: {"allowed": true/false, "reason": "qisqa sabab agar bloklansa"}. '
        "Bloklang: jinsiy, haqorat, telefon raqam, tashqi havola, firibgarlik, nikoh maqsadiga zid."
    )
    chat = _new_chat(session_id="mod", system_message=sys)
    if not chat:
        return True, ""
    raw = await _send(chat, f"Xabar: {text}")
    parsed = _extract_json(raw)
    if isinstance(parsed, dict):
        return bool(parsed.get("allowed", True)), str(parsed.get("reason", ""))
    return True, ""


# ---------- Helpers ----------
def _extract_json(text: str):
    if not text:
        return None
    # Strip code fences
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        # Try to find first JSON block
        m = re.search(r"(\{.*\}|\[.*\])", cleaned, flags=re.DOTALL)
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                return None
        return None


def _safe_age(u: dict) -> int:
    from services import age_from_birth
    return age_from_birth(u.get("birth_date", "2000-01-01"))



# ---------- 5) Face verification (photo onboarding) ----------
async def verify_face_photo(image_url: str = "", image_base64: str = "") -> dict:
    """
    Verify a photo is a real, single adult human face.
    Returns: {"valid": bool, "code": "ok|no_face|multiple_faces|cartoon|minor|celebrity|other", "reason": str}
    """
    if not EMERGENT_LLM_KEY:
        # Fail open in dev (no key) — accept but warn
        return {"valid": True, "code": "ok", "reason": "verification skipped (no LLM key)"}

    if not image_url and not image_base64:
        return {"valid": False, "code": "no_image", "reason": "Rasm taqdim etilmadi"}

    # If only URL provided, we need to fetch & base64-encode
    if image_url and not image_base64:
        try:
            import httpx
            import base64 as b64lib
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as cli:
                r = await cli.get(image_url)
                if r.status_code != 200:
                    return {"valid": False, "code": "no_image", "reason": "Rasm yuklab bo'lmadi"}
                content_type = r.headers.get("content-type", "image/jpeg").lower()
                # Restrict to common image types
                if not any(t in content_type for t in ("jpeg", "jpg", "png", "webp")):
                    return {"valid": False, "code": "bad_format", "reason": "Faqat JPEG/PNG/WEBP qabul qilinadi"}
                image_base64 = b64lib.b64encode(r.content).decode("ascii")
        except Exception as exc:
            log.error(f"face: image fetch failed: {exc}")
            return {"valid": False, "code": "no_image", "reason": "Rasmni yuklab bo'lmadi"}

    sys_msg = (
        "You are a strict photo-verification AI for a serious matchmaking platform. "
        "Analyze the user-uploaded profile photo and decide if it is acceptable. "
        "Reject for ANY of these reasons:\n"
        "1) NO real human face is clearly visible (drawing, blank, scenery, object, animal)\n"
        "2) MULTIPLE distinct human faces in the same photo (must be exactly one person)\n"
        "3) The person looks UNDER 18 (child / teenager younger than 18)\n"
        "4) CARTOON, anime, painting, sketch, 3D render, AI-generated avatar, or heavily filtered/morphed\n"
        "5) Recognizable CELEBRITY, politician, athlete, or other widely-known public figure\n"
        "6) Face is too small, blurred beyond recognition, fully covered, or back of head only\n"
        "Reply STRICTLY in JSON, no extra text:\n"
        '{"valid": true|false, "code": "ok|no_face|multiple_faces|minor|cartoon|celebrity|too_blurry|other", '
        '"reason": "short user-friendly Uzbek sentence (<=80 chars)"}'
    )

    try:
        from emergentintegrations.llm.chat import ImageContent
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"face-verify-{os.urandom(4).hex()}",
            system_message=sys_msg,
        ).with_model("openai", "gpt-4o-mini")
        msg = UserMessage(
            text="Tekshiring va JSON qaytaring.",
            file_contents=[ImageContent(image_base64=image_base64)],
        )
        resp = await chat.send_message(msg)
        text = str(resp).strip()
        # Parse JSON
        cleaned = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
        m = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if m:
            cleaned = m.group(0)
        data = json.loads(cleaned)
        if not isinstance(data, dict):
            raise ValueError("not dict")
        valid = bool(data.get("valid"))
        code = str(data.get("code") or ("ok" if valid else "other"))
        reason = str(data.get("reason") or ("OK" if valid else "Rasm talablarga javob bermaydi"))
        # Uzbek reason fallback by code
        UZ_REASONS = {
            "no_face": "Rasmda yuz aniqlanmadi",
            "multiple_faces": "Faqat bitta odam bo'lishi kerak",
            "minor": "Foydalanuvchi 18 yoshdan katta bo'lishi kerak",
            "cartoon": "Rasm, multfilm yoki sun'iy tasvir qabul qilinmaydi",
            "celebrity": "Mashhur shaxs rasmi taqiqlanadi — o'z rasmingizni yuklang",
            "too_blurry": "Rasm xira yoki yuz aniq ko'rinmaydi",
        }
        if not valid and code in UZ_REASONS:
            reason = UZ_REASONS[code]
        return {"valid": valid, "code": code, "reason": reason}
    except Exception as exc:
        log.error(f"face: verify failed: {exc}")
        # Fail open on transient errors so onboarding isn't broken
        return {"valid": True, "code": "ok", "reason": "verification unavailable"}
