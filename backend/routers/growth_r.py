"""Growth & monetization features: boost, daily check-in, quiz, icebreakers, invites."""
from __future__ import annotations

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException

from auth import get_current_user_id
from core import db, get_user, iso, now_utc, parse_dt, push_notif, user_public
from models import new_id

router = APIRouter(tags=["growth"])

# Pricing
BOOST_PRICE = 5000        # 24h boost in UZS (deducts from balance or paid via CLICK)
SPOTLIGHT_PRICE = 25000   # 7d spotlight
DAILY_BONUS = 50          # +50 balance per daily check-in
STREAK_7_BONUS = 500      # week-7 streak bonus
INVITE_REWARD_GIVES_PREMIUM_DAYS = 7  # 3 invites → 7 free Premium days


# ---------- Daily check-in / Streak ----------
@router.get("/daily/status")
async def daily_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    last = me.get("daily_last_at")
    streak = me.get("daily_streak", 0)
    today_iso = iso(now_utc().replace(hour=0, minute=0, second=0, microsecond=0))
    claimed_today = last is not None and last >= today_iso
    return {
        "claimed_today": claimed_today,
        "streak": streak,
        "next_bonus": DAILY_BONUS if not claimed_today else 0,
        "streak_7_bonus_in": max(0, 7 - (streak % 7 or 0)) if not claimed_today else None,
    }


@router.post("/daily/claim")
async def daily_claim(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    today = now_utc().replace(hour=0, minute=0, second=0, microsecond=0)
    today_iso_str = iso(today)
    yesterday_iso = iso(today - timedelta(days=1))
    last = me.get("daily_last_at")
    if last and last >= today_iso_str:
        raise HTTPException(400, "Bugun olingan")
    # Streak math
    streak = me.get("daily_streak", 0)
    if last and last >= yesterday_iso:
        streak += 1
    else:
        streak = 1
    bonus = DAILY_BONUS
    if streak % 7 == 0:
        bonus += STREAK_7_BONUS
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {"daily_last_at": iso(now_utc()), "daily_streak": streak},
            "$inc": {"balance": bonus, "xp": 20 + (50 if streak % 7 == 0 else 0)},
        },
    )
    await push_notif(uid, "balance", f"Daily bonus +{bonus:,} so'm (streak {streak})")
    return {"streak": streak, "bonus": bonus, "balance_after": (me.get("balance", 0) + bonus)}


# ---------- Profile Boost (24h 5x visibility) ----------
@router.get("/boost/status")
async def boost_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    until = me.get("boost_until")
    active = bool(until and parse_dt(until) > now_utc())
    return {"active": active, "until": until, "price": BOOST_PRICE}


@router.post("/boost/activate")
async def boost_activate(use_balance: bool = Body(True, embed=True), uid: str = Depends(get_current_user_id)):
    """Activate 24h boost. If use_balance=True, deduct from balance; otherwise client should redirect to CLICK payment."""
    if not use_balance:
        from routers.payments_r import create_payment
        from models import CreatePaymentRequest
        return await create_payment(CreatePaymentRequest(purpose="balance_topup", amount=BOOST_PRICE), uid=uid)
    me = await get_user(uid)
    if me.get("balance", 0) < BOOST_PRICE:
        raise HTTPException(402, f"Need {BOOST_PRICE:,} so'm balance")
    until = now_utc() + timedelta(hours=24)
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {
                "boost_until": iso(until),
                "boost_metrics.started_at": iso(now_utc()),
                "boost_metrics.impressions": 0,
                "boost_metrics.views": 0,
                "boost_metrics.likes": 0,
                "boost_metrics.messages": 0,
                "boost_metrics.roses": 0,
            },
            "$inc": {"balance": -BOOST_PRICE},
        },
    )
    await push_notif(uid, "boost", "Profile Boost faollashtirildi — 24 soat 5x ko'proq ko'rinish 🚀")
    return {"active": True, "until": iso(until), "balance_after": me.get("balance", 0) - BOOST_PRICE}


# ---------- Spotlight (7d top of region) ----------
@router.post("/spotlight/activate")
async def spotlight_activate(use_balance: bool = Body(True, embed=True), uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    if not use_balance:
        from routers.payments_r import create_payment
        from models import CreatePaymentRequest
        return await create_payment(CreatePaymentRequest(purpose="balance_topup", amount=SPOTLIGHT_PRICE), uid=uid)
    if me.get("balance", 0) < SPOTLIGHT_PRICE:
        raise HTTPException(402, f"Need {SPOTLIGHT_PRICE:,} so'm balance")
    until = now_utc() + timedelta(days=7)
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {
                "spotlight_until": iso(until),
                "boost_metrics.sp_started_at": iso(now_utc()),
                "boost_metrics.sp_impressions": 0,
                "boost_metrics.sp_views": 0,
            },
            "$inc": {"balance": -SPOTLIGHT_PRICE},
        },
    )
    await push_notif(uid, "boost", "Spotlight 7 kunlik faollashtirildi 🌟")
    return {"active": True, "until": iso(until)}


# ---------- Icebreaker prompts ----------
ICEBREAKERS_UZ = [
    "Sizning eng yoqimli xotirangiz qaysi?",
    "Hayotda 3 ta eng muhim narsa nima?",
    "Idealdagi dam olish kuni qanday o'tadi?",
    "Qaysi kitob/film sizga juda ta'sir qildi?",
    "Bo'sh vaqtingizda nima qilishni yoqtirasiz?",
    "Eng katta orzuingiz nima?",
    "Oilada nima eng muhim deb o'ylaysiz?",
    "Hayotda eng katta yutuq qaysi?",
    "Qayerda yashashni xohlaysiz?",
    "Eng yaxshi maslahatchingiz kim?",
]
ICEBREAKERS_RU = [
    "Какое ваше любимое воспоминание?",
    "Три самые важные вещи в жизни?",
    "Как выглядит идеальный выходной?",
    "Какая книга/фильм на вас сильнее всего повлияли?",
    "Чем любите заниматься в свободное время?",
    "Какая ваша самая большая мечта?",
    "Что самое важное в семье?",
    "Самое большое достижение в жизни?",
    "Где бы хотели жить?",
    "Кто ваш лучший советчик?",
]
ICEBREAKERS_EN = [
    "What's your favorite memory?",
    "Three most important things in life?",
    "What does your ideal day off look like?",
    "Which book/film impacted you the most?",
    "What do you like to do in free time?",
    "What's your biggest dream?",
    "What matters most in family?",
    "Your biggest achievement so far?",
    "Where would you want to live?",
    "Who's your best advisor?",
]


@router.get("/icebreakers")
async def icebreakers(lang: str = "uz"):
    pool = {"ru": ICEBREAKERS_RU, "en": ICEBREAKERS_EN}.get(lang, ICEBREAKERS_UZ)
    return pool


# ---------- Compatibility Quiz ----------
QUIZ_QUESTIONS = [
    {
        "id": "lifestyle",
        "q_uz": "Sizga qaysi turdagi hayot yaqin?", "q_ru": "Какой образ жизни вам ближе?", "q_en": "Which lifestyle suits you?",
        "options": [
            {"key": "family", "uz": "Oilaviy va tinch", "ru": "Семейный и спокойный", "en": "Family-oriented & calm"},
            {"key": "active", "uz": "Faol va sayohatchi", "ru": "Активный и путешественник", "en": "Active & traveler"},
            {"key": "career", "uz": "Karyera fokusi", "ru": "Карьерный фокус", "en": "Career-focused"},
            {"key": "spiritual", "uz": "Ma'naviy va sodda", "ru": "Духовный и простой", "en": "Spiritual & simple"},
        ],
    },
    {
        "id": "marriage_timeline",
        "q_uz": "Turmush qurishni qachon xohlaysiz?", "q_ru": "Когда хотели бы создать семью?", "q_en": "When do you want to marry?",
        "options": [
            {"key": "year1", "uz": "1 yil ichida", "ru": "В течение года", "en": "Within a year"},
            {"key": "year2", "uz": "1-2 yil", "ru": "1-2 года", "en": "1-2 years"},
            {"key": "year3plus", "uz": "Shoshmasdan", "ru": "Не торопясь", "en": "No rush"},
        ],
    },
    {
        "id": "kids",
        "q_uz": "Farzandlar haqida fikr?", "q_ru": "Мысли о детях?", "q_en": "Thoughts on kids?",
        "options": [
            {"key": "soon", "uz": "Tezroq", "ru": "Скоро", "en": "Soon"},
            {"key": "later", "uz": "Kuting", "ru": "Подождать", "en": "Later"},
            {"key": "many", "uz": "Ko'p", "ru": "Много", "en": "Many"},
            {"key": "few", "uz": "1-2", "ru": "1-2", "en": "1-2"},
        ],
    },
    {
        "id": "communication",
        "q_uz": "Munosabatda eng muhim?", "q_ru": "Главное в отношениях?", "q_en": "Most important in relationship?",
        "options": [
            {"key": "trust", "uz": "Ishonch", "ru": "Доверие", "en": "Trust"},
            {"key": "respect", "uz": "Hurmat", "ru": "Уважение", "en": "Respect"},
            {"key": "love", "uz": "Sevgi", "ru": "Любовь", "en": "Love"},
            {"key": "support", "uz": "Qo'llab-quvvatlash", "ru": "Поддержка", "en": "Support"},
        ],
    },
    {
        "id": "weekend",
        "q_uz": "Ideal dam olish kuni?", "q_ru": "Идеальный выходной?", "q_en": "Ideal weekend?",
        "options": [
            {"key": "home", "uz": "Uyda oila bilan", "ru": "Дома с семьёй", "en": "Home with family"},
            {"key": "outdoor", "uz": "Tabiatda", "ru": "На природе", "en": "Outdoors"},
            {"key": "city", "uz": "Shaharda", "ru": "В городе", "en": "In the city"},
            {"key": "travel", "uz": "Sayohat", "ru": "Путешествие", "en": "Travel"},
        ],
    },
    {
        "id": "spending",
        "q_uz": "Pulga munosabat?", "q_ru": "Отношение к деньгам?", "q_en": "Money mindset?",
        "options": [
            {"key": "save", "uz": "Tejovchi", "ru": "Экономный", "en": "Saver"},
            {"key": "invest", "uz": "Sarmoyalovchi", "ru": "Инвестор", "en": "Investor"},
            {"key": "enjoy", "uz": "Sevgan narsaga sarflash", "ru": "Тратить на любимое", "en": "Spend on what I love"},
            {"key": "balanced", "uz": "Muvozanat", "ru": "Баланс", "en": "Balanced"},
        ],
    },
    {
        "id": "religion",
        "q_uz": "Dindorlik darajasi?", "q_ru": "Уровень религиозности?", "q_en": "Religion level?",
        "options": [
            {"key": "strong", "uz": "Kuchli", "ru": "Сильно", "en": "Strong"},
            {"key": "moderate", "uz": "O'rta", "ru": "Средне", "en": "Moderate"},
            {"key": "private", "uz": "Shaxsiy", "ru": "Личное", "en": "Personal"},
        ],
    },
]


@router.get("/quiz/questions")
async def quiz_questions():
    return QUIZ_QUESTIONS


@router.post("/quiz/submit")
async def quiz_submit(answers: dict = Body(...), uid: str = Depends(get_current_user_id)):
    """answers = {question_id: option_key}"""
    valid_ids = {q["id"] for q in QUIZ_QUESTIONS}
    cleaned = {k: v for k, v in answers.items() if k in valid_ids and isinstance(v, str)}
    await db.users.update_one(
        {"id": uid},
        {"$set": {"quiz_answers": cleaned, "quiz_completed_at": iso(now_utc())}},
    )
    # Give small bonus for completing
    await db.users.update_one({"id": uid}, {"$inc": {"balance": 100}})
    return {"ok": True, "answered": len(cleaned), "bonus": 100}


# ---------- Invite Friends (3 → free Premium week) ----------
@router.get("/invites/status")
async def invites_status(uid: str = Depends(get_current_user_id)):
    me = await get_user(uid)
    code = me.get("referral_code") or uid[:8]
    if not me.get("referral_code"):
        await db.users.update_one({"id": uid}, {"$set": {"referral_code": code}})
    invited = await db.users.count_documents({"referred_by": code})
    redeemed = me.get("invite_premium_redeemed", 0)
    eligible_redemptions = invited // 3
    available_redemptions = max(0, eligible_redemptions - redeemed)
    from core import TELEGRAM_BOT_USERNAME
    link = f"https://t.me/{TELEGRAM_BOT_USERNAME}?start={code}"
    return {
        "code": code,
        "link": link,
        "invited": invited,
        "redeemed_weeks": redeemed,
        "available_weeks": available_redemptions,
        "next_milestone": 3 - (invited % 3) if invited % 3 != 0 else 3,
    }


@router.post("/invites/redeem")
async def invites_redeem(uid: str = Depends(get_current_user_id)):
    """Claim 1 free Premium week per 3 invited friends."""
    me = await get_user(uid)
    code = me.get("referral_code") or uid[:8]
    invited = await db.users.count_documents({"referred_by": code})
    redeemed = me.get("invite_premium_redeemed", 0)
    if invited // 3 <= redeemed:
        raise HTTPException(400, "Not enough invites for redemption")
    # Extend plan by 7 days; if currently free, set premium with new expiry
    cur_until = me.get("plan_until")
    base = parse_dt(cur_until) if cur_until else now_utc()
    if base < now_utc():
        base = now_utc()
    new_until = base + timedelta(days=INVITE_REWARD_GIVES_PREMIUM_DAYS)
    await db.users.update_one(
        {"id": uid},
        {
            "$set": {"plan": "premium", "plan_until": iso(new_until)},
            "$inc": {"invite_premium_redeemed": 1},
        },
    )
    await push_notif(uid, "premium", f"Tabriklaymiz! Premium {INVITE_REWARD_GIVES_PREMIUM_DAYS} kun faollashtirildi 🎉")
    return {"ok": True, "plan_until": iso(new_until)}
