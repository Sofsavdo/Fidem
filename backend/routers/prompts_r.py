"""Hinge-style profile prompts — text + voice answers.

Users pick up to 3 prompts from a curated list and provide text or voice answers.
Adds depth and personality to profiles beyond static fields.
"""
from __future__ import annotations
import os
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile

from auth import get_current_user_id
from core import db, get_user, iso, now_utc
from models import new_id
from storage import MIME, put_object

router = APIRouter(tags=["prompts"])

# Curated prompt list (Hinge-inspired, halal-appropriate)
PROMPT_LIBRARY = [
    {"id": "p_family", "category": "family",
     "uz": "Sizning oilangiz haqida bir narsa ayting...",
     "ru": "Расскажите что-нибудь о вашей семье...",
     "en": "Tell me something about your family..."},
    {"id": "p_values", "category": "values",
     "uz": "Hayotda eng muhim deb hisoblagan 3 narsa...",
     "ru": "3 самые важные вещи в жизни...",
     "en": "The 3 most important things in my life..."},
    {"id": "p_dream", "category": "future",
     "uz": "5 yildan keyin o'zimni shu yerda ko'raman...",
     "ru": "Через 5 лет я вижу себя...",
     "en": "In 5 years I see myself..."},
    {"id": "p_partner", "category": "partner",
     "uz": "Mening kelajakdagi turmush o'rtog'imda eng muhim sifat...",
     "ru": "Самое важное качество в моей будущей половинке...",
     "en": "The most important quality in my future partner..."},
    {"id": "p_perfect_day", "category": "lifestyle",
     "uz": "Idealdagi dam olish kuni — bu...",
     "ru": "Идеальный выходной день — это...",
     "en": "My perfect day off looks like..."},
    {"id": "p_passion", "category": "lifestyle",
     "uz": "Men chin yurakdan sevgan ishim...",
     "ru": "То, что я делаю с настоящей страстью...",
     "en": "Something I do with true passion..."},
    {"id": "p_faith", "category": "faith",
     "uz": "Iymonim menga shu narsani o'rgatdi...",
     "ru": "Моя вера научила меня...",
     "en": "My faith has taught me..."},
    {"id": "p_proud", "category": "achievement",
     "uz": "Men eng faxrlanadigan yutug'im...",
     "ru": "Мое самое значимое достижение...",
     "en": "What I am most proud of..."},
    {"id": "p_food", "category": "fun",
     "uz": "Eng yaxshi pishiradigan taomim...",
     "ru": "Блюдо, которое я готовлю лучше всего...",
     "en": "The dish I cook best..."},
    {"id": "p_book", "category": "fun",
     "uz": "Mening hayotimni o'zgartirgan kitob...",
     "ru": "Книга, изменившая мою жизнь...",
     "en": "A book that changed my life..."},
    {"id": "p_travel", "category": "fun",
     "uz": "Borib ko'rmoqchi bo'lgan joyim...",
     "ru": "Место, куда я хочу поехать...",
     "en": "A place I want to visit..."},
    {"id": "p_kindness", "category": "values",
     "uz": "Boshqalarga qilgan eng yaxshi ishim...",
     "ru": "Лучшее, что я сделал для других...",
     "en": "The kindest thing I have done for others..."},
    {"id": "p_marriage", "category": "partner",
     "uz": "Nikoh men uchun nimani anglatadi...",
     "ru": "Что для меня значит брак...",
     "en": "What marriage means to me..."},
    {"id": "p_hobby", "category": "fun",
     "uz": "Bo'sh vaqtimda nima qilaman...",
     "ru": "Чем я занимаюсь в свободное время...",
     "en": "What I do in my free time..."},
    {"id": "p_strength", "category": "self",
     "uz": "Mening eng kuchli tomonim...",
     "ru": "Моя самая сильная сторона...",
     "en": "My biggest strength..."},
    {"id": "p_growth", "category": "self",
     "uz": "Hozir o'zim ustida ishlayotgan jihat...",
     "ru": "Над чем я сейчас работаю в себе...",
     "en": "What I am working on in myself right now..."},
]


@router.get("/prompts/library")
async def prompts_library(lang: str = "uz"):
    out = []
    for p in PROMPT_LIBRARY:
        out.append({
            "id": p["id"],
            "category": p["category"],
            "text": p.get(lang, p["uz"]),
        })
    return out


@router.get("/prompts/mine")
async def prompts_mine(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    return me.get("prompts") or []


@router.post("/prompts/save")
async def prompts_save(prompts: list = Body(..., embed=False), uid: str = Depends(get_current_user_id)):
    """prompts = [{"id":"p_family","answer":"...","kind":"text"|"voice","voice_url":"..."}]
    Max 3 prompts."""
    if not isinstance(prompts, list):
        raise HTTPException(400, "prompts must be a list")
    if len(prompts) > 3:
        raise HTTPException(400, "Maksimal 3 ta prompt")
    cleaned = []
    valid_ids = {p["id"] for p in PROMPT_LIBRARY}
    for p in prompts:
        if not isinstance(p, dict) or p.get("id") not in valid_ids:
            continue
        cleaned.append({
            "id": p["id"],
            "answer": (p.get("answer") or "").strip()[:500],
            "kind": p.get("kind", "text") if p.get("kind") in ("text", "voice") else "text",
            "voice_url": p.get("voice_url") if p.get("kind") == "voice" else None,
            "duration_sec": int(p.get("duration_sec", 0) or 0),
            "updated_at": iso(now_utc()),
        })
    await db.users.update_one({"id": uid}, {"$set": {"prompts": cleaned}})
    # Award XP for first prompt
    me = await get_user(uid)
    if cleaned and not me.get("prompts_xp_awarded"):
        await db.users.update_one({"id": uid}, {"$set": {"prompts_xp_awarded": True}, "$inc": {"xp": 50}})
    return {"ok": True, "prompts": cleaned}


# ---------- Voice prompt upload ----------
ALLOWED_AUDIO = {"mp3", "wav", "ogg", "webm", "m4a"}
MAX_AUDIO_SIZE = 5 * 1024 * 1024   # 5 MB
MAX_AUDIO_DURATION = 60            # 60 sec


@router.post("/prompts/voice-upload")
async def upload_voice(file: UploadFile = File(...), uid: str = Depends(get_current_user_id)):
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in ALLOWED_AUDIO:
        raise HTTPException(400, f"Faqat audio: {', '.join(sorted(ALLOWED_AUDIO))}")
    data = await file.read()
    if len(data) > MAX_AUDIO_SIZE:
        raise HTTPException(413, "Audio fayl 5MB dan oshmasligi kerak")
    storage_path = f"{os.environ.get('APP_NAME','fidem')}/voice/{uid}/{new_id()}.{ext}"
    try:
        await put_object(storage_path, data, MIME.get(ext, "audio/mpeg"))
    except Exception as e:
        raise HTTPException(500, f"Upload failed: {e}")
    # Track in DB
    rec = {
        "id": new_id(),
        "user_id": uid,
        "path": storage_path,
        "content_type": MIME.get(ext, "audio/mpeg"),
        "size": len(data),
        "created_at": iso(now_utc()),
        "kind": "voice_prompt",
    }
    await db.files.insert_one(rec)
    return {"id": rec["id"], "path": storage_path, "url": f"/api/files/{storage_path}"}
