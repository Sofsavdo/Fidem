"""FIDEM assistant: an AI helper pinned at the top of Messages.

It answers questions about the app (prices, selfie check, contact exchange,
safety), and helps with the profile and first messages. It is clearly an
assistant (name, robot avatar, "AI" tag), never shown in the candidate feed
(hidden_profile), text only, and replies through Gemini. The admin can
switch it off (Admin > Moderatsiya > Chat nazorati).
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from datetime import timedelta

import core
from core import iso, now_utc, new_id, push_notif, manager

log = logging.getLogger("fidem.ai_assistant")

ASSISTANT_ID = "ai_assistant"
AVATAR_VERSION = 1
DAILY_REPLY_CAP = 60           # assistant replies one person can get per 24 h (cost guard)

ASSISTANT = dict(
    slug="assistant", name="FIDEM yordamchisi", gender="female", age=25, region="Toshkent", district="",
    marital="single", kids=0, height=0, weight=0, edu="", job="AI yordamchi", rel="", reloc=None,
    look=dict(assistant=True), character="", bio="Ilova bo'yicha savollar, profil va birinchi xabar bo'yicha maslahatlar.",
)


def persona_id(p: dict) -> str:
    return ASSISTANT_ID


# ---------- Drawn avatars (SVG) ----------
def avatar_svg(p: dict) -> bytes:
    return _assistant_svg()


def _assistant_svg() -> bytes:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 500" width="800" height="1000">'
        '<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ec4899"/>'
        '<stop offset="1" stop-color="#8b5cf6"/></linearGradient></defs>'
        '<rect width="400" height="500" fill="url(#g)"/>'
        '<rect x="110" y="150" width="180" height="150" rx="40" fill="#ffffff"/>'
        '<rect x="190" y="110" width="20" height="44" rx="10" fill="#ffffff"/><circle cx="200" cy="104" r="14" fill="#ffffff"/>'
        '<circle cx="160" cy="220" r="17" fill="#8b5cf6"/><circle cx="240" cy="220" r="17" fill="#8b5cf6"/>'
        '<path d="M168,262 Q200,282 232,262" stroke="#ec4899" stroke-width="8" fill="none" stroke-linecap="round"/>'
        '<path d="M200,400 C150,365 120,340 120,312 C120,295 134,284 150,284 C168,284 186,296 200,312 C214,296 232,284 250,284 C266,284 280,295 280,312 C280,340 250,365 200,400 Z" fill="#ffffff" opacity=".9"/>'
        '</svg>'
    ).encode()


# ---------- Seeding ----------
def _birth_date(age: int) -> str:
    today = now_utc().date()
    return today.replace(year=today.year - age, month=3, day=15).isoformat() if today.month > 3 else \
        today.replace(year=today.year - age - 1, month=3, day=15).isoformat()


def _doc(p: dict) -> dict:
    return {
        "id": ASSISTANT_ID, "name": p["name"], "gender": p["gender"],
        "birth_date": _birth_date(p["age"]), "country": "Uzbekistan", "region": p["region"],
        "bio": p["bio"], "language": "uz", "onboarded": True, "terms_accepted": True,
        "is_ai": True, "ai_role": "assistant", "plan": "free",
        "hidden_profile": True,   # never in the feed; pinned in Messages instead
    }


async def _ensure_avatar(p: dict, existing: dict | None) -> dict:
    if existing and existing.get("ai_avatar_version") == AVATAR_VERSION and existing.get("photo_url"):
        return {}
    from storage import put_object
    pid = persona_id(p)
    res = await put_object(f"fidem/ai/{pid}_v{AVATAR_VERSION}.svg", avatar_svg(p), "image/svg+xml")
    await core.db.files.insert_one({
        "id": new_id(), "owner_id": pid, "storage_path": res["path"], "content_type": "image/svg+xml",
        "size": res.get("size", 0), "is_deleted": False, "is_public": True, "created_at": iso(now_utc()),
    })
    return {"photo_url": f"/api/files/{res['path']}", "ai_avatar_version": AVATAR_VERSION}


async def ensure_assistant() -> None:
    """Create / refresh the assistant's user record (idempotent, at startup)."""
    for p in [ASSISTANT]:
        pid = persona_id(p)
        try:
            existing = await core.db.users.find_one({"id": pid}, {"_id": 0, "photo_url": 1, "ai_avatar_version": 1})
            doc = _doc(p)
            doc.update(await _ensure_avatar(p, existing))
            doc["last_active"] = iso(now_utc())
            await core.db.users.update_one(
                {"id": pid},
                {"$set": doc, "$setOnInsert": {"created_at": iso(now_utc() - timedelta(days=random.randint(3, 40)))}},
                upsert=True,
            )
        except Exception:
            log.warning("could not set up AI persona %s", pid, exc_info=True)


# ---------- Settings (admin switch) ----------
_SETTINGS = {"at": 0.0, "on": None}
ENABLED_DEFAULT = os.environ.get("AI_ASSISTANT", "1").strip().lower() not in ("0", "false", "off", "no")


async def enabled() -> bool:
    if _SETTINGS["on"] is not None and time.time() - _SETTINGS["at"] < 30:
        return _SETTINGS["on"]
    doc = await core.db.settings.find_one({"id": "ai_assistant"}, {"_id": 0, "enabled": 1}) or {}
    val = bool(doc["enabled"]) if "enabled" in doc else ENABLED_DEFAULT
    _SETTINGS.update(at=time.time(), on=val)
    return val


def reset_settings_cache() -> None:
    _SETTINGS.update(at=0.0, on=None)


# ---------- Replies ----------
_RULES = """Strict rules (never break them):
- You are FIDEM's AI assistant, not a person; say so plainly if asked. Never claim to be human.
- Never give or ask for phone numbers, addresses, photos, money or card details.
- No sexual or vulgar content; keep Uzbek family values. Stay respectful even if they are rude.
- Write like a friendly messenger reply: short, no markdown, emojis rarely. Answer in the language the person writes in (Uzbek Latin by default, Russian or English if they use it).
- Be helpful and specific; ask a short follow-up question only when it helps."""

_SCHEMA = {"type": "OBJECT", "properties": {"reply": {"type": "STRING"}}, "required": ["reply"]}

_ASSISTANT_FACTS = """You are "FIDEM yordamchisi", the AI helper of FIDEM, a marriage-intent dating
Telegram Mini App in Uzbekistan. Help with: how the app works, filling the profile, writing a good
first message, staying safe. Facts:
- Premium: 1 day 9,900 so'm, 15 days 49,900, 1 month 79,000; pay by card transfer, turns on right away, not a subscription.
- Women: Premium is free during the launch after the selfie check. Women can write after the selfie check.
- Selfie check: Men > Profil tasdiqlash; the app asks for a random hand gesture; AI or admin checks it.
- Contacts can't be sent in messages. Use the "Kontakt almashish" button: both selfie-verified,
  10+ messages each, the person asking has Premium, the other agrees.
- FIDEM never asks for money. Report anyone who asks for money or a card (chat menu > Shikoyat). Insults are blocked.
- Family contact: Premium users can request parents' contact on a profile.
- Human support: Telegram @Medik005.
Be warm and brief (2-4 sentences). If you don't know, say so and point to @Medik005."""


def _persona_prompt(p: dict, me: dict, history: list[dict], pid: str) -> str:
    head = _ASSISTANT_FACTS
    who = f"The person: {me.get('name', '')}, {core.age_from_birth(me.get('birth_date', '2000-01-01'))} y.o., {me.get('region', '')}."
    lines = []
    for m in history:
        speaker = "Siz" if m["from_user_id"] == pid else (me.get("name") or "Suhbatdosh")
        lines.append(f"{speaker}: {m.get('text', '')}")
    return f"{head}\n{_RULES}\n{who}\n\nConversation so far:\n" + "\n".join(lines) + "\n\nWrite your next message."


def _persona_by_id(pid: str) -> dict | None:
    return ASSISTANT if pid == ASSISTANT_ID else None


_pending: dict[str, asyncio.Task] = {}


def schedule_reply(uid: str, pid: str, chat_id: str) -> None:
    """Reply after a short, human-looking pause. A new message from the same
    person restarts the pause, so a burst of messages gets one answer."""
    old = _pending.get(chat_id)
    if old and not old.done():
        old.cancel()
    _pending[chat_id] = asyncio.ensure_future(_reply(uid, pid, chat_id))


async def _reply(uid: str, pid: str, chat_id: str) -> None:
    try:
        await asyncio.sleep(random.uniform(2.5, 6.0))      # "reading"
        p = _persona_by_id(pid)
        if not p or not await enabled():
            return
        since = iso(now_utc() - timedelta(hours=24))
        sent_today = await core.db.messages.count_documents(
            {"to_user_id": uid, "from_user_id": ASSISTANT_ID, "created_at": {"$gte": since}},
        )
        if sent_today >= DAILY_REPLY_CAP:
            return
        me = await core.db.users.find_one({"id": uid}, {"_id": 0, "name": 1, "birth_date": 1, "region": 1})
        rows = await core.db.messages.find(
            {"chat_id": chat_id, "kind": "text"}, {"_id": 0, "from_user_id": 1, "text": 1},
        ).sort("created_at", -1).limit(16).to_list(16)
        history = list(reversed(rows))
        from ai_service import GEMINI_API_KEY, _gemini_json
        if not GEMINI_API_KEY:
            return
        res = await _gemini_json(_persona_prompt(p, me or {}, history, pid), [], _SCHEMA,
                                 max_tokens=400, timeout=25.0, thinking_budget=0)
        text = (res.get("reply") or "").strip()[:800]
        if not text:
            return
        # the same safety net as for people
        from ai_service import detect_contact_info, detect_money_request
        if detect_contact_info(text) or detect_money_request(text):
            return
        await asyncio.sleep(min(1.5 + len(text) / 30.0, 9.0))  # "typing"
        await core.db.messages.update_many({"chat_id": chat_id, "to_user_id": pid, "read": False}, {"$set": {"read": True}})
        msg = {
            "id": new_id(), "chat_id": chat_id, "from_user_id": pid, "to_user_id": uid,
            "text": text, "kind": "text", "created_at": iso(now_utc()), "read": False, "status": "chat",
        }
        await core.db.messages.insert_one(dict(msg))
        await manager.broadcast_chat([uid], {"type": "message", "data": msg})
        await push_notif(uid, "message", f"🤖 {p['name']} javob yozdi", link=f"/chat/{pid}")
    except asyncio.CancelledError:
        pass
    except Exception:
        log.warning("ai persona reply failed", exc_info=True)
    finally:
        if _pending.get(chat_id) is asyncio.current_task():
            _pending.pop(chat_id, None)
