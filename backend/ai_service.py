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
        "Siz halol nikoh va oilaviy hayotga e'tibor qaratuvchi musulmon sovchi-mutaxassissiz. "
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
        "Siz musulmon sovchi-mutaxassissiz, halol nikoh uchun ilk suhbat savollarini tayyorlaysiz. "
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
        "Siz halol musulmon platforma uchun moderatorisz. Berilgan xabar ruxsat etilganmi? "
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
