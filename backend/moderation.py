"""Chat moderation: a message that breaks FIDEM's rules never reaches the
other person.

Two layers, checked before a message is stored or delivered:
1. Rules: whole-word patterns for swearing, insults and sexual requests in
   Uzbek (Latin + Cyrillic), Russian and English. Instant, free, always on.
   Whole words only: the old substring list blocked ordinary words
   ("uyda yotibman" matched "yotib").
2. AI (Gemini): catches what word lists can't (disguised insults, threats,
   indecent proposals, hate). Admin can switch it off. It fails open: if the
   AI is slow or down, the message goes through. Chat must keep working,
   and the rules layer still applies.

Each block is recorded in moderation_events for the admin panel.
Repeat offenders get a 24-hour write mute and a report for the admin.
"""
from __future__ import annotations

import logging
import re
import time
from collections import OrderedDict
from datetime import timedelta

import core
from core import iso, now_utc, new_id, parse_dt

log = logging.getLogger("fidem.moderation")

# ---------- 1) Rules ----------
_W = r"(?<![\w'])"   # word start (letters, digits, apostrophe count as word)
_E = r"(?![\w'])"    # word end

_RULES: list[tuple[str, str]] = [
    # Uzbek insults / obscenities (Latin, then Cyrillic)
    ("insult", _W + r"(?:ahmoq|axmoq|ahmaq|tentak|dalba(?:yob|yo'b)\w*|dolba(?:yob|yo'b)\w*|padarla['’]?nat\w*|haromi|xaromi|manjalaqi)" + _E),
    ("obscene", _W + r"(?:fohisha\w*|qahba\w*|qanjiq\w*|jalab\w*|jallab\w*|sik(?:aman|ib|ay|dim|ish|tir)\w*|qo['’]?toq\w*)" + _E),
    ("insult", _W + r"(?:аҳмоқ|ахмоқ|ахмок|тентак|далбаёб\w*)" + _E),
    ("obscene", _W + r"(?:фоҳиша\w*|фохиша\w*|қаҳба\w*|кахба\w*|жалаб\w*)" + _E),
    # Russian mat (Cyrillic and common Latin spellings)
    ("obscene", _W + r"(?:(?:на|по)?ху[йяеёи]\w*|пизд\w*|[её]б(?:ать|ал|ан|у|ут|ись|нут)\w*|бля(?:д\w*|ть)?|сук[аи]|муда[кч]\w*|шлюх\w*|пидор\w*|гандон\w*|долбо[её]б\w*)" + _E),
    ("obscene", _W + r"(?:xuy\w*|huy\w*|pizd\w*|blya\w*|blyat|suka|na[xh]uy|dolboyob\w*|yeban\w*|eban\w*)" + _E),
    # English
    ("obscene", _W + r"(?:fuck\w*|bitch\w*|whore\w*|slut\w*|cunt\w*|motherfuck\w*)" + _E),
    # Sexual requests
    ("sexual", _W + r"(?:yotamiz|yotaylik|yotishamiz|seks|sex|sexy|секс\w*|интим\w*|intim|nudes?|yalang['’]?och\w*|голая|голые)" + _E),
    ("sexual", r"ko['’]?krak\w*\s+rasm|rasm\w*\s+ko['’]?krak|kiyimsiz\s+rasm|голое\s+фото"),
]
_RULES_RE = [(cat, re.compile(p, re.IGNORECASE | re.UNICODE)) for cat, p in _RULES]


def _norm(text: str) -> str:
    return re.sub(r"[‘’ʻʼ`]", "'", (text or "").lower())


def rule_check(text: str) -> str:
    """Category of the first rule the text breaks, or ""."""
    t = _norm(text)
    for cat, rx in _RULES_RE:
        if rx.search(t):
            return cat
    return ""


REASON_UZ = {
    "insult": "Haqoratli so'z",
    "obscene": "So'kinish / behayo so'z",
    "sexual": "Behayo, jinsiy mazmun",
    "harassment": "Bezovta qilish, tazyiq",
    "threat": "Tahdid",
    "hate": "Millat, din yoki jinsga nisbatan nafrat",
    "scam": "Firibgarlikka o'xshaydi",
    "drugs": "Giyohvandlik / taqiqlangan narsalar",
    "other": "FIDEM qoidalariga zid",
}

# ---------- 2) AI ----------
_AI_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "verdict": {"type": "STRING", "enum": ["allow", "block"]},
        "category": {"type": "STRING", "enum": list(REASON_UZ)},
    },
    "required": ["verdict", "category"],
}

_AI_PROMPT = """You moderate one chat message on FIDEM, a serious, family-oriented
marriage app in Uzbekistan (messages are in Uzbek Latin/Cyrillic, Russian or English).

BLOCK only clear violations:
- insults, swearing, humiliation of the other person
- sexual content, indecent proposals, requests for intimate photos, "let's sleep together"
- harassment or pressure after the other person said no; threats; blackmail
- hate toward a nation, religion or gender
- scams, prostitution/escort offers, drugs, gambling
ALLOW everything else, including: greetings, compliments ("chiroylisiz", "you are beautiful"),
questions about family, religion, work, age, city, children, marriage plans,
polite refusals, jokes, emojis, mild flirting, discussing meeting with families.
When unsure, ALLOW.

Message:
<<<{text}>>>

Answer JSON: verdict (allow/block) and category (use "other" when allowed)."""

_AI_MIN_CHARS = 12          # "salom", "rahmat", "ha" - nothing for the AI to judge
_AI_TIMEOUT = 4.0
_cache: "OrderedDict[str, str]" = OrderedDict()
_CACHE_MAX = 3000


async def ai_check(text: str) -> str:
    """Category when the AI says block, "" to allow (also on any AI error)."""
    key = _norm(text).strip()
    if len(key) < _AI_MIN_CHARS:
        return ""
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    try:
        from ai_service import GEMINI_API_KEY, _gemini_json
        if not GEMINI_API_KEY:
            return ""
        res = await _gemini_json(
            _AI_PROMPT.replace("{text}", text[:1500]), [], _AI_SCHEMA,
            max_tokens=60, timeout=_AI_TIMEOUT, thinking_budget=0, retry=False,
        )
        cat = (res.get("category") or "other") if res.get("verdict") == "block" else ""
        if cat and cat not in REASON_UZ:
            cat = "other"
    except Exception as e:  # fail open: chat keeps working without the AI
        log.info("ai moderation skipped: %s", type(e).__name__)
        return ""
    _cache[key] = cat
    if len(_cache) > _CACHE_MAX:
        _cache.popitem(last=False)
    return cat


# ---------- Settings (admin switch) ----------
_SETTINGS = {"at": 0.0, "ai": None}


async def ai_enabled() -> bool:
    if _SETTINGS["ai"] is not None and time.time() - _SETTINGS["at"] < 30:
        return _SETTINGS["ai"]
    doc = await core.db.settings.find_one({"id": "moderation"}, {"_id": 0, "ai_enabled": 1}) or {}
    val = bool(doc.get("ai_enabled", True))
    _SETTINGS.update(at=time.time(), ai=val)
    return val


def reset_settings_cache() -> None:
    _SETTINGS.update(at=0.0, ai=None)


# ---------- Decision + strikes ----------
STRIKES_TO_MUTE = 3            # blocked messages within STRIKE_WINDOW
STRIKE_WINDOW = timedelta(hours=24)
MUTE_FOR = timedelta(hours=24)


async def check_message(text: str) -> tuple[str, str]:
    """(category, source) when the message must be blocked, ("", "") if fine."""
    cat = rule_check(text)
    if cat:
        return cat, "rules"
    if await ai_enabled():
        cat = await ai_check(text)
        if cat:
            return cat, "ai"
    return "", ""


async def record_block(uid: str, to_user_id: str, text: str, category: str, source: str) -> bool:
    """Store the blocked message for the admin; returns True when this strike
    muted the sender for 24 hours."""
    now = now_utc()
    await core.db.moderation_events.insert_one({
        "id": new_id(), "from_user_id": uid, "to_user_id": to_user_id,
        "text": text[:500], "category": category, "source": source,
        "created_at": iso(now),
    })
    await core.db.users.update_one({"id": uid}, {"$inc": {"moderation_strikes": 1}})
    recent = await core.db.moderation_events.count_documents(
        {"from_user_id": uid, "created_at": {"$gte": iso(now - STRIKE_WINDOW)}},
    )
    if recent >= STRIKES_TO_MUTE:
        await core.db.users.update_one({"id": uid}, {"$set": {"muted_until": iso(now + MUTE_FOR)}})
        await core.db.reports.insert_one({
            "id": new_id(), "reporter_id": "system", "target_id": uid,
            "reason": "abuse", "details": f"{recent} ta qoidabuzar xabar 24 soatda: {REASON_UZ.get(category, category)}",
            "to_user_id": to_user_id, "created_at": iso(now), "status": "open",
        })
        return True
    return False


def muted_now(user: dict) -> bool:
    until = user.get("muted_until")
    if not until:
        return False
    try:
        return parse_dt(until) > now_utc()
    except Exception:
        return False
