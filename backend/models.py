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
    is_super: bool = False
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
    kind: Literal["text", "gift", "photo_request", "photo_grant", "super", "rose", "voice", "video"] = "text"
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
    purpose: Literal["premium", "vip", "standard", "chat_unlock", "balance_topup", "super_application", "gift", "concierge"]
    amount: Optional[int] = None  # for balance / gift / super
    target_user_id: Optional[str] = None  # for super application or gift
    gift_kind: Optional[str] = None
    order_id: Optional[str] = None  # for concierge orders


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
    gift_kind: Literal["rose", "box", "diamond", "crown"]


GIFT_PRICES = {
    # 2 ta haftalik bepul gift (price=0)
    "rose_free":   {"price": 0,       "emoji": "🌹", "label_uz": "Atirgul (bepul)",  "label_ru": "Роза (бесплатно)",   "label_en": "Rose (free)",      "tier": "free", "free_per_week": 1},
    "heart_free":  {"price": 0,       "emoji": "💗", "label_uz": "Yurakcha (bepul)", "label_ru": "Сердечко (бесплатно)","label_en": "Heart (free)",     "tier": "free", "free_per_week": 1},
    # 10 ta pulli gift (2000 so'm dan 499000 so'm gacha)
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

# Weekly free gift quota per plan (rose_free, heart_free uchun)
FREE_GIFTS_BY_PLAN = {"free": 1, "premium": 2, "vip": 3}
# Backwards compatibility helper
GIFT_EMOJI = {k: v["emoji"] for k, v in GIFT_PRICES.items()}
GIFT_LABEL_UZ = {k: v["label_uz"] for k, v in GIFT_PRICES.items()}
# Backwards compat: legacy gift kinds (rose/box/diamond/crown) map to new equivalents
LEGACY_GIFT_MAP = {"rose": "rose_free", "box": "bouquet", "diamond": "diamond", "crown": "crown"}


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
    plan: Optional[Literal["free", "premium", "vip"]] = None
    balance: Optional[int] = None
    blocked: Optional[bool] = None
    add_balance: Optional[int] = None


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
