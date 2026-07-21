"""Pydantic models for FIDEM."""
from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, EmailStr


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


# ---------- Auth ----------
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class TelegramAuthRequest(BaseModel):
    init_data: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    is_admin: bool = False
    onboarded: bool = False
    user: dict | None = None
    """Full profile (same shape as GET /auth/me), included so the client can
    render immediately instead of round-tripping to /auth/me right after
    login/register/telegram-auth. Optional for backward compatibility."""


# ---------- User / Profile ----------
GenderType = Literal["male", "female"]
MaritalType = Literal["single", "divorced", "widowed"]


class OnboardingProfile(BaseModel):
    gender: GenderType
    birth_date: str  # ISO YYYY-MM-DD
    country: str
    region: str = ""
    district: str = ""
    marital_status: MaritalType
    has_children: bool
    children_count: int = 0
    height_cm: int
    weight_kg: int
    education: str = ""
    profession: str = ""
    religion: str = ""
    looking_for: str = ""  # description text
    search_gender: GenderType
    search_age_min: int = 18
    search_age_max: int = 60
    search_country: str = ""
    search_region: str = ""
    photo_url: Optional[str] = None
    bio: Optional[str] = ""
    name: str
    smoking: Literal["no", "sometimes", "yes"] = "no"
    alcohol: Literal["no", "sometimes", "yes"] = "no"
    relocation: bool = False
    # Signup consent: terms of use + privacy policy + serious-intent pledge,
    # all confirmed with checkboxes before the wizard. Required for FIRST
    # onboarding (auth_r enforces); ignored on the edit/complete flow.
    terms_accepted: bool = False
    # Optional "who invited you?" - a referral id or username entered on the
    # consent screen. Only honored on first onboarding when the account has
    # no referred_by yet (Telegram deep-link attribution always wins).
    referral_code: Optional[str] = None


class UserPublic(BaseModel):
    id: str
    name: str
    gender: GenderType
    age: int
    country: Optional[str] = ""
    region: str = ""
    district: str = ""
    marital_status: MaritalType
    has_children: bool
    children_count: int
    height_cm: int
    weight_kg: int
    education: str = ""
    profession: str = ""
    religion: str = ""
    bio: str = ""
    photo_url: Optional[str] = None
    verified_identity: bool = False
    verified_selfie: bool = False
    verified_financial: bool = False
    last_active: datetime
    completeness: int = 0
    avg_response_min: Optional[int] = None
    online: bool = False
    plan: Literal["free", "premium", "vip"] = "free"
    balance: int = 0


class CandidateCard(UserPublic):
    match_score: int = 0
    match_reasons: List[str] = []
    photo_unlocked: bool = False
    can_message: bool = True


class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    education: Optional[str] = None
    profession: Optional[str] = None
    religion: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None
    district: Optional[str] = None
    looking_for: Optional[str] = None
    search_country: Optional[str] = None
    search_region: Optional[str] = None
    search_age_min: Optional[int] = None
    search_age_max: Optional[int] = None
    search_gender: Optional[GenderType] = None
    photo_url: Optional[str] = None
    # write-once fields included only if owner is forcing change (will require re-verify)
    height_cm: Optional[int] = None
    weight_kg: Optional[int] = None
    marital_status: Optional[MaritalType] = None
    has_children: Optional[bool] = None
    children_count: Optional[int] = None
    smoking: Optional[Literal["no", "sometimes", "yes"]] = None
    alcohol: Optional[Literal["no", "sometimes", "yes"]] = None
    relocation: Optional[bool] = None
    # Owner's shareable contact details (Sozlamalar > aloqa ma'lumotlari).
    # PRIVATE: never in user_public - only surfaced back to the owner via
    # /auth/me and sent into a chat when the owner explicitly shares them.
    contact_phone: Optional[str] = None
    contact_telegram: Optional[str] = None
    contact_instagram: Optional[str] = None
    # 15-second video intro (VIP perk; auth_r enforces the plan gate).
    # Empty string clears it; shown publicly on the profile detail page.
    video_intro_url: Optional[str] = None


class MessageFilters(BaseModel):
    """Who can message me filters."""
    age_min: int = 18
    age_max: int = 60
    region: Optional[str] = None
    marital_status: Optional[MaritalType] = None
    has_children: Optional[bool] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    weight_min: Optional[int] = None
    weight_max: Optional[int] = None
    require_verified: bool = False
    require_financial: bool = False


# ---------- Messages ----------
class SendMessageRequest(BaseModel):
    to_user_id: str
    text: str
    kind: Literal["text", "voice", "video"] = "text"
    voice_url: Optional[str] = None
    voice_duration: Optional[int] = None  # seconds
    video_url: Optional[str] = None
    video_duration: Optional[int] = None  # seconds
    video_thumbnail: Optional[str] = None


class MessageOut(BaseModel):
    id: str
    chat_id: str
    from_user_id: str
    to_user_id: str
    text: str
    created_at: datetime
    kind: Literal["text", "gift", "photo_request", "photo_grant", "voice", "video"] = "text"
    meta: dict = {}


class ChatOut(BaseModel):
    chat_id: str
    other: UserPublic
    last_message: Optional[MessageOut] = None
    unread: int = 0
    status: Literal["chat", "application", "match"] = "chat"


# ---------- Saved / Likes ----------
class SaveRequest(BaseModel):
    user_id: str


# ---------- Verification ----------
class VerificationRequest(BaseModel):
    kind: Literal["identity", "selfie", "financial"]
    note: Optional[str] = None
    proof_url: Optional[str] = None


# ---------- Payments ----------
PlanType = Literal["premium", "vip"]


class CreatePaymentRequest(BaseModel):
    purpose: Literal["premium", "vip", "standard", "chat_unlock", "balance_topup", "gift", "concierge", "rank_boost", "boost"]
    amount: Optional[int] = None  # for balance / gift
    target_user_id: Optional[str] = None  # for gift
    gift_kind: Optional[str] = None
    order_id: Optional[str] = None  # for concierge orders
    # Subscription purchases only (premium/standard/vip): 1/3/12-month plans,
    # 3 and 12 months priced at a discount vs. months * the 1-month rate.
    months: Literal[1, 3, 12] = 1


class PaymentOut(BaseModel):
    id: str
    user_id: str
    amount: int
    purpose: str
    status: Literal["pending", "success", "failed"]
    payment_link: Optional[str] = None
    created_at: datetime


# ---------- Gifts ----------
class SendGiftRequest(BaseModel):
    to_user_id: str
    # Not a Literal of the old 4 legacy kinds - that silently 422'd 10 of the
    # 12 real catalog gifts (only "diamond"/"crown" happened to overlap with
    # the legacy names). send_gift() below validates against GIFT_PRICES /
    # LEGACY_GIFT_MAP itself and 400s on anything actually invalid.
    gift_kind: str


class GiftPurchaseRequest(BaseModel):
    gift_kind: str
    # Omitted/None: buy it into your own inventory to give away later.
    # Set: buy and deliver immediately to that recipient (no inventory hold).
    to_user_id: Optional[str] = None


class GiftRedeemRequest(BaseModel):
    to_user_id: str


GIFT_PRICES = {
    # 10 ta pulli sovg'a (2000 so'm dan 499000 so'm gacha) - hech biri bepul
    # emas: har bir sovg'a haqiqiy pul qiymatiga ega bo'lishi kerak.
    "heart":       {"price": 2000,    "emoji": "❤️", "label_uz": "Yurak",            "label_ru": "Сердце",             "label_en": "Heart",            "tier": "care"},
    "chocolate":   {"price": 5000,    "emoji": "🍫", "label_uz": "Shokolad",         "label_ru": "Шоколад",            "label_en": "Chocolate",        "tier": "care"},
    "coffee":      {"price": 10000,   "emoji": "☕", "label_uz": "Qahva",            "label_ru": "Кофе",               "label_en": "Coffee",           "tier": "care"},
    "bouquet":     {"price": 25000,   "emoji": "💐", "label_uz": "Gulchambar",       "label_ru": "Букет",              "label_en": "Bouquet",          "tier": "love"},
    "star":        {"price": 50000,   "emoji": "🌟", "label_uz": "Yulduz",           "label_ru": "Звезда",             "label_en": "Star",             "tier": "love"},
    "ring":        {"price": 100000,  "emoji": "💍", "label_uz": "Uzuk",             "label_ru": "Кольцо",             "label_en": "Ring",             "tier": "love"},
    "diamond":     {"price": 199000,  "emoji": "💎", "label_uz": "Olmos",            "label_ru": "Бриллиант",          "label_en": "Diamond",          "tier": "luxury"},
    "trophy":      {"price": 299000,  "emoji": "🏆", "label_uz": "Kubok",            "label_ru": "Кубок",              "label_en": "Trophy",           "tier": "luxury"},
    "crown":       {"price": 399000,  "emoji": "👑", "label_uz": "Toj",              "label_ru": "Корона",             "label_en": "Crown",            "tier": "luxury"},
    "rocket":      {"price": 499000,  "emoji": "🚀", "label_uz": "Raketa",           "label_ru": "Ракета",             "label_en": "Rocket",           "tier": "luxury"},
}

# Obuna tariflarini/oylik to'plamlarni sovg'a qilish - alohida katalog
# (gift_shop_r.py'dagi /gifts/plan-catalog), har doim darhol bir kishiga
# yetkaziladi (inventarga saqlab bo'lmaydi - o'zi uchun sotib olish oddiy
# /payments/create orqali bo'ladi, bu yerda faqat "sovg'a qilish" bor).
PLAN_GIFTS = {
    "gift_standard_1m": {"price": 34900,  "plan": "standard", "months": 1, "emoji": "⭐", "label_uz": "Standard — 1 oy", "label_ru": "Стандарт — 1 месяц",  "label_en": "Standard — 1 month"},
    "gift_standard_3m": {"price": 89000,  "plan": "standard", "months": 3, "emoji": "⭐", "label_uz": "Standard — 3 oy", "label_ru": "Стандарт — 3 месяца", "label_en": "Standard — 3 months"},
    "gift_premium_1m":  {"price": 79000,  "plan": "premium",  "months": 1, "emoji": "💎", "label_uz": "Premium — 1 oy",  "label_ru": "Премиум — 1 месяц",   "label_en": "Premium — 1 month"},
    "gift_premium_3m":  {"price": 199000, "plan": "premium",  "months": 3, "emoji": "💎", "label_uz": "Premium — 3 oy",  "label_ru": "Премиум — 3 месяца",  "label_en": "Premium — 3 months"},
    "gift_vip_1m":       {"price": 199000, "plan": "vip",      "months": 1, "emoji": "👑", "label_uz": "VIP — 1 oy",      "label_ru": "VIP — 1 месяц",       "label_en": "VIP — 1 month"},
    "gift_vip_3m":       {"price": 499000, "plan": "vip",      "months": 3, "emoji": "👑", "label_uz": "VIP — 3 oy",      "label_ru": "VIP — 3 месяца",      "label_en": "VIP — 3 months"},
}

# Backwards compatibility helper
GIFT_EMOJI = {k: v["emoji"] for k, v in GIFT_PRICES.items()}
GIFT_LABEL_UZ = {k: v["label_uz"] for k, v in GIFT_PRICES.items()}
# Backwards compat: legacy gift kinds (rose/box/diamond/crown) map to new equivalents
LEGACY_GIFT_MAP = {"rose": "heart", "box": "bouquet", "diamond": "diamond", "crown": "crown"}


# ---------- Notifications ----------
class NotificationOut(BaseModel):
    id: str
    user_id: str
    kind: str
    text: str
    created_at: datetime
    read: bool = False
    link: Optional[str] = None


# ---------- Admin ----------
class AdminUpdateUserRequest(BaseModel):
    verified_identity: Optional[bool] = None
    verified_selfie: Optional[bool] = None
    verified_financial: Optional[bool] = None
    plan: Optional[Literal["free", "standard", "premium", "vip"]] = None
    balance: Optional[int] = None
    blocked: Optional[bool] = None
    add_balance: Optional[int] = None


# ---------- Notification Preferences ----------
class NotificationPreferencesRequest(BaseModel):
    disable_general: bool = False
    disable_match: bool = False
    disable_message: bool = False
    disable_premium: bool = False
    disable_community: bool = False
    disable_referral: bool = False
    disable_balance: bool = False


# ---------- Privacy settings ----------
class PrivacySettingsRequest(BaseModel):
    # None = leave unchanged, so each toggle can be flipped independently.
    photo_public: Optional[bool] = None
    hidden_profile: Optional[bool] = None


# ---------- Reports / blocks ----------
class ReportRequest(BaseModel):
    user_id: str
    reason: str


class PhotoUnlockRequest(BaseModel):
    target_user_id: str


class PhotoUnlockDecision(BaseModel):
    request_id: str
    approve: bool


# ---------- Filter / Search ----------
class CandidateFilter(BaseModel):
    age_min: Optional[int] = None
    age_max: Optional[int] = None
    region: Optional[str] = None
    marital_status: Optional[MaritalType] = None
    has_children: Optional[bool] = None
    height_min: Optional[int] = None
    height_max: Optional[int] = None
    weight_min: Optional[int] = None
    weight_max: Optional[int] = None
    verified_only: bool = False
    financial_only: bool = False
    sort: Literal["match", "active", "new"] = "match"
