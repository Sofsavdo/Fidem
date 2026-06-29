"""FIDEM backend entrypoint — thin app + lifespan + router mounting."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI
from starlette.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
log = logging.getLogger("fidem")

from core import (  # noqa: E402  (must load env first)
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    client,
    db,
    hash_pw,
    iso,
    now_utc,
)
from models import new_id  # noqa: E402
from routers.admin_r import router as admin_router  # noqa: E402
from routers.auth_r import router as auth_router  # noqa: E402
from routers.candidates_r import router as candidates_router  # noqa: E402
from routers.chat_r import router as chat_router  # noqa: E402
from routers.growth_r import router as growth_router  # noqa: E402
from routers.payments_r import router as payments_router  # noqa: E402
from routers.telegram_r import router as telegram_router, setup_telegram_webhook  # noqa: E402
from routers.personality_r import router as personality_router  # noqa: E402
from routers.roses_r import router as roses_router  # noqa: E402
from routers.ai_r import router as ai_router  # noqa: E402
from routers.prompts_r import router as prompts_router  # noqa: E402
from routers.stories_r import router as stories_router  # noqa: E402
from routers.gamification_r import router as gamification_router  # noqa: E402
from routers.withdrawals_r import router as withdrawals_router  # noqa: E402
from routers.family_r import router as family_router  # noqa: E402
from routers.concierge_r import router as concierge_router  # noqa: E402
from routers.travel_r import router as travel_router  # noqa: E402
from routers.boost_analytics_r import router as boost_analytics_router  # noqa: E402
from routers.face_r import router as face_router  # noqa: E402
from services import compute_completeness  # noqa: E402
from storage import init_storage  # noqa: E402

app = FastAPI(title="FIDEM API")

api = APIRouter(prefix="/api")
api.include_router(auth_router)
api.include_router(candidates_router)
api.include_router(chat_router)
api.include_router(growth_router)
api.include_router(payments_router)
api.include_router(admin_router)
api.include_router(telegram_router)
api.include_router(personality_router)
api.include_router(roses_router)
api.include_router(ai_router)
api.include_router(prompts_router)
api.include_router(stories_router)
api.include_router(gamification_router)
api.include_router(withdrawals_router)
api.include_router(family_router)
api.include_router(concierge_router)
api.include_router(travel_router)
api.include_router(boost_analytics_router)
api.include_router(face_router)
app.include_router(api)


@app.on_event("startup")
async def startup() -> None:
    try:
        init_storage()
    except Exception as e:
        log.warning(f"Storage init: {e}")

    # Set Telegram webhook in background (non-fatal)
    import asyncio
    asyncio.create_task(setup_telegram_webhook())

    # Indexes
    await db.users.create_index("id", unique=True)
    await db.users.create_index("email", sparse=True)
    await db.users.create_index("telegram_id", sparse=True)
    await db.messages.create_index([("chat_id", 1), ("created_at", 1)])
    await db.saved.create_index([("owner_id", 1), ("target_id", 1)], unique=True)
    await db.profile_views.create_index([("viewer_id", 1), ("target_id", 1)], unique=True)
    await db.photo_unlocks.create_index([("requester_id", 1), ("target_id", 1)], unique=True)
    await db.payments.create_index("id", unique=True)
    await db.chaperones.create_index([("owner_id", 1), ("wali_id", 1)], unique=True)
    await db.chaperone_invites.create_index("code", unique=True)
    await db.roses.create_index([("from_user_id", 1), ("created_at", -1)])
    await db.compat_unlocks.create_index([("user_id", 1), ("target_id", 1)], unique=True)
    await db.success_stories.create_index("created_at")
    await db.files.create_index("path")
    await db.withdrawals.create_index([("user_id", 1), ("created_at", -1)])
    await db.withdrawals.create_index("status")
    await db.family_requests.create_index([("from_user_id", 1), ("to_user_id", 1)])
    await db.family_requests.create_index([("to_user_id", 1), ("status", 1)])
    await db.concierge_orders.create_index([("user_id", 1), ("status", 1)])

    # PERF: Compound indexes for candidates query (scales to 100K+ users).
    # The candidates endpoint filters by: onboarded, gender, region, birth_date range.
    await db.users.create_index(
        [("onboarded", 1), ("gender", 1), ("region", 1), ("birth_date", 1)],
        name="ix_candidates_main"
    )
    # For sort by activity / new
    await db.users.create_index([("last_active", -1)], name="ix_last_active")
    # For boost/spotlight float-to-top
    await db.users.create_index([("boost_until", -1)], name="ix_boost_until", sparse=True)
    await db.users.create_index([("spotlight_until", -1)], name="ix_spotlight_until", sparse=True)
    # For verification & financial filters
    await db.users.create_index([("verified_selfie", 1)], name="ix_verified_selfie", sparse=True)
    await db.users.create_index([("verified_financial", 1)], name="ix_verified_financial", sparse=True)
    # Notifications: list by user_id newest first
    await db.notifications.create_index([("user_id", 1), ("created_at", -1)], name="ix_notif_user_time")
    # Messages: chat reads pagination
    await db.messages.create_index([("from_user_id", 1), ("to_user_id", 1)], name="ix_msg_pair")
    # Referral lookup
    await db.users.create_index("referred_by", sparse=True, name="ix_referred_by")
    await db.users.create_index("referral_code", sparse=True, unique=False, name="ix_referral_code")
    await db.saved.create_index([("target_id", 1), ("at", -1)], name="ix_saved_target_at")
    await db.profile_views.create_index([("target_id", 1), ("at", -1)], name="ix_profile_views_target_at")
    await db.messages.create_index([("to_user_id", 1), ("created_at", -1)], name="ix_msg_to_user_time")
    await db.chat_unlocks.create_index([("user_id", 1), ("target_id", 1)], name="ix_chat_unlocks_user_target")

    # Seed admin
    admin = await db.users.find_one({"email": ADMIN_EMAIL.lower()})
    if not admin:
        await db.users.insert_one({
            "id": new_id(),
            "email": ADMIN_EMAIL.lower(),
            "password_hash": hash_pw(ADMIN_PASSWORD),
            "name": "FIDEM Admin",
            "is_admin": True,
            "onboarded": True,
            "verified_identity": True,
            "verified_selfie": True,
            "verified_financial": True,
            "plan": "vip",
            "balance": 0,
            "gender": "male",
            "birth_date": "1990-01-01",
            "country": "Uzbekistan",
            "region": "Toshkent",
            "district": "Markaz",
            "marital_status": "single",
            "has_children": False,
            "children_count": 0,
            "height_cm": 175,
            "weight_kg": 70,
            "education": "Oliy",
            "profession": "Admin",
            "religion": "Islom",
            "looking_for": "—",
            "search_gender": "female",
            "search_age_min": 18,
            "search_age_max": 60,
            "search_region": "Toshkent",
            "language": "uz",
            "created_at": iso(now_utc()),
            "last_active": iso(now_utc()),
        })
        log.info(f"Seeded admin: {ADMIN_EMAIL}")

    onboarded = await db.users.count_documents({"onboarded": True, "is_admin": {"$ne": True}})
    if onboarded < 12:
        await seed_demo_users()
    # Seed success stories if none exist (independent of users)
    stories_count = await db.success_stories.count_documents({})
    if stories_count == 0:
        await seed_success_stories()


async def seed_demo_users() -> None:
    demo = [
        ("Madina", "female", "1998-04-15", "Toshkent", "Yunusobod", 165, 55, "Oliy", "O'qituvchi", "Islom"),
        ("Aziza", "female", "1996-09-21", "Toshkent", "Chilonzor", 168, 58, "Magistr", "Dizayner", "Islom"),
        ("Dilnoza", "female", "2000-02-10", "Samarqand", "Markaz", 162, 52, "Oliy", "Tibbiyot", "Islom"),
        ("Shahnoza", "female", "1995-11-30", "Toshkent", "Mirzo Ulug'bek", 170, 60, "Magistr", "Iqtisodchi", "Islom"),
        ("Gulnora", "female", "1999-07-05", "Buxoro", "Markaz", 164, 54, "Oliy", "Bank", "Islom"),
        ("Sevara", "female", "1997-12-18", "Toshkent", "Sergeli", 167, 56, "Oliy", "IT", "Islom"),
        ("Lola", "female", "2001-03-22", "Andijon", "Markaz", 163, 53, "Bakalavr", "Talaba", "Islom"),
        ("Nigora", "female", "1994-06-12", "Toshkent", "Yashnobod", 169, 59, "Magistr", "Yurist", "Islom"),
        ("Bobur", "male", "1995-05-10", "Toshkent", "Yunusobod", 178, 75, "Oliy", "Muhandis", "Islom"),
        ("Sardor", "male", "1992-08-25", "Toshkent", "Mirzo Ulug'bek", 182, 80, "Magistr", "IT-Direktor", "Islom"),
        ("Jasur", "male", "1998-01-15", "Samarqand", "Markaz", 175, 72, "Oliy", "Vrach", "Islom"),
        ("Diyor", "male", "1996-10-08", "Toshkent", "Chilonzor", 180, 78, "Oliy", "Biznes", "Islom"),
        ("Otabek", "male", "1993-11-19", "Toshkent", "Yashnobod", 179, 77, "Magistr", "Marketing", "Islom"),
        ("Rustam", "male", "1997-04-30", "Buxoro", "Markaz", 176, 74, "Oliy", "Arxitektor", "Islom"),
    ]
    photos_f = [
        "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=800",
        "https://images.unsplash.com/photo-1438761681033-6461ffad8d80?w=800",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=800",
        "https://images.unsplash.com/photo-1488426862026-3ee34a7d66df?w=800",
        "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=800",
        "https://images.unsplash.com/photo-1502685104226-ee32379fefbe?w=800",
        "https://images.unsplash.com/photo-1531123897727-8f129e1688ce?w=800",
        "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=800",
    ]
    photos_m = [
        "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=800",
        "https://images.unsplash.com/photo-1599566150163-29194dcaad36?w=800",
        "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=800",
        "https://images.unsplash.com/photo-1531427186611-ecfd6d936c79?w=800",
        "https://images.unsplash.com/photo-1463453091185-61582044d556?w=800",
        "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=800",
    ]
    pf = pm = 0
    for name, gender, bd, region, district, h, w, edu, prof, rel in demo:
        uid = new_id()
        photo = photos_f[pf % len(photos_f)] if gender == "female" else photos_m[pm % len(photos_m)]
        if gender == "female":
            pf += 1
        else:
            pm += 1
        doc = {
            "id": uid,
            "name": name, "gender": gender, "birth_date": bd,
            "country": "Uzbekistan", "region": region, "district": district,
            "marital_status": "single", "has_children": False, "children_count": 0,
            "height_cm": h, "weight_kg": w,
            "education": edu, "profession": prof, "religion": rel,
            "looking_for": "Oila qurish, samimiy va vafodor inson",
            "search_gender": "male" if gender == "female" else "female",
            "search_age_min": 20, "search_age_max": 40,
            "search_region": region, "photo_url": photo,
            "bio": f"Salom! Men {name}. Oilaviy hayot tarafdoriman.",
            "onboarded": True, "verified_identity": True, "verified_selfie": True,
            "verified_financial": False, "plan": "free", "balance": 0,
            "language": "uz",
            "created_at": iso(now_utc()), "last_active": iso(now_utc()),
        }
        doc["completeness"] = compute_completeness(doc)
        await db.users.insert_one(doc)
    log.info("Seeded demo users")


async def seed_success_stories() -> None:
    stories = [
        {
            "couple_names": "Aziza & Bobur",
            "region": "Toshkent",
            "year": 2025,
            "story_text": "FIDEM orqali Bobur bilan tanishganimga 8 oy bo'ldi. Birinchi xabarni u atirgul yuborib boshladi — bu menga juda samimiy tuyuldi. Suhbatlarimizda halol va ochiq edik, oilalarimiz ham bir-birini yoqtirdi. Hozir nikohimizning birinchi yili.",
            "photo_url": "https://images.unsplash.com/photo-1519741497674-611481863552?w=800",
            "published": True, "featured": True, "views": 142,
        },
        {
            "couple_names": "Dilnoza & Sardor",
            "region": "Samarqand",
            "year": 2024,
            "story_text": "Onam menga FIDEM'ni tavsiya qildi. Sovchi tizimi ajoyib edi — onam suhbatlarimizni xolisona kuzata oldi va Sardorning oilasini yaxshi deb topdi. AI hisobot bizga moslik 91% ekanini ko'rsatdi. To'yimiz bahorda bo'ldi.",
            "photo_url": "https://images.unsplash.com/photo-1583939003579-730e3918a45a?w=800",
            "published": True, "featured": True, "views": 89,
        },
        {
            "couple_names": "Madina & Diyor",
            "region": "Toshkent · Chilonzor",
            "year": 2025,
            "story_text": "Diyor menga shaxsiyat testi orqali yo'l ko'rsatdi — biz ikkalamiz ham yuqori mas'uliyatli va xushmuomalalik darajasiga ega edik. Tanishganimizning 4 oyida nikohlashga qaror qildik. Alloh duosi bilan.",
            "photo_url": "https://images.unsplash.com/photo-1551027395-99f23ce0a8b1?w=800",
            "published": True, "featured": False, "views": 67,
        },
    ]
    for s in stories:
        s["id"] = new_id()
        s["created_at"] = iso(now_utc())
        await db.success_stories.insert_one(s)
    log.info(f"Seeded {len(stories)} success stories")


@app.on_event("shutdown")
async def shutdown() -> None:
    client.close()


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
