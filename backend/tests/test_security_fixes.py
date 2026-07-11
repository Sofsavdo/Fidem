"""Unit tests for the security/correctness fixes made during the Phase 1 audit.

Most of these test pure logic (PII redaction, payment signature verification,
JWT, Telegram initData validation) without a live MongoDB. The can_initiate_chat
tests monkeypatch a fake db object instead. Run with:
pytest backend/tests/test_security_fixes.py
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlencode

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

import core  # noqa: E402
import auth  # noqa: E402
import services  # noqa: E402
from routers import auth_r  # noqa: E402
from routers import chat_r  # noqa: E402


# ---------- user_public() PII redaction ----------
FULL_USER = {
    "id": "u1",
    "name": "Test User",
    "gender": "male",
    "birth_date": "1995-01-01",
    "region": "Tashkent",
    "email": "secret@example.com",
    "phone": "+998901234567",
    "telegram_id": "123456",
    "telegram_username": "secretuser",
    "ip_address": "1.2.3.4",
    "user_agent": "Mozilla/5.0",
    "created_at": "2024-01-01T00:00:00Z",
    "fraud_score": 42,
    "fraud_reasons": ["multi_account"],
    "flagged_as_bot": True,
}

PRIVATE_FIELDS = [
    "email", "phone", "telegram_id", "telegram_username",
    "ip_address", "user_agent", "created_at",
    "fraud_score", "fraud_reasons", "flagged_as_bot",
]


def test_user_public_default_excludes_pii():
    out = core.user_public(FULL_USER)
    for field in PRIVATE_FIELDS:
        assert field not in out, f"{field} leaked into default (other-user-facing) user_public() output"


def test_user_public_include_private_true_includes_pii():
    out = core.user_public(FULL_USER, include_private=True)
    for field in PRIVATE_FIELDS:
        assert field in out, f"{field} missing from include_private=True output"
    assert out["email"] == "secret@example.com"
    assert out["fraud_score"] == 42


def test_user_public_always_includes_safe_fields():
    out = core.user_public(FULL_USER)
    assert out["id"] == "u1"
    assert out["name"] == "Test User"
    assert out["region"] == "Tashkent"


def test_user_public_never_leaks_raw_coordinates():
    """Map M1: even if a stray geo_point ends up on the user doc, user_public
    (an allow-list) must never surface raw coordinates — only the boolean
    location_verified badge is public."""
    user_with_geo = {**FULL_USER, "geo_point": [69.28, 41.31], "location_verified": True}
    for out in (core.user_public(user_with_geo), core.user_public(user_with_geo, include_private=True), core.user_public_minimal(user_with_geo)):
        assert "geo_point" not in out
        assert out.get("location_verified") is True


# ---------- geo.py — Map M1 location verification ----------
def test_geo_region_from_coords_matches_known_cities():
    import geo
    assert geo.region_from_coords(41.31, 69.28) == "Toshkent shahri"
    assert geo.region_from_coords(39.65, 66.96) == "Samarqand"
    assert geo.region_from_coords(51.5, -0.12) is None  # London — outside UZ


def test_geo_coords_match_region():
    import geo
    assert geo.coords_match_region(41.31, 69.28, "Toshkent shahri") is True
    assert geo.coords_match_region(41.31, 69.28, "Buxoro") is False
    assert geo.coords_match_region(41.31, 69.28, "") is False


def test_geo_distance_bucket_is_coarse():
    import geo
    # never a precise figure — always rounded to 5km or a "50+"/"under 1" band
    assert geo.distance_bucket(4.8) == "~5 km"
    assert geo.distance_bucket(12.0) == "~10 km"
    assert geo.distance_bucket(0.4).startswith("1 km") or "under" in geo.distance_bucket(0.4)
    assert geo.distance_bucket(80) == "50+ km"


def test_geo_valid_coords():
    import geo
    assert geo.valid_coords(41.3, 69.2) is True
    assert geo.valid_coords(999, 0) is False
    assert geo.valid_coords("abc", None) is False


# ---------- CLICK payment signature verification ----------
def _click_md5(*parts) -> str:
    return hashlib.md5("".join(str(p) for p in parts).encode()).hexdigest()


@pytest.fixture(autouse=True)
def click_secret(monkeypatch):
    monkeypatch.setattr(services, "CLICK_SECRET_KEY", "test-click-secret")
    monkeypatch.setattr(services, "CLICK_SERVICE_ID", "12345")
    yield


def test_verify_click_sign_prepare_valid():
    form = {
        "click_trans_id": "1", "merchant_trans_id": "order1",
        "amount": "10000", "sign_time": "2026-01-01 00:00:00",
    }
    action = "0"
    form["sign_string"] = _click_md5(
        form["click_trans_id"], services.CLICK_SERVICE_ID, services.CLICK_SECRET_KEY,
        form["merchant_trans_id"], form["amount"], action, form["sign_time"],
    )
    assert services.verify_click_sign(form, action) is True


def test_verify_click_sign_prepare_rejects_tampered_amount():
    form = {
        "click_trans_id": "1", "merchant_trans_id": "order1",
        "amount": "10000", "sign_time": "2026-01-01 00:00:00",
    }
    action = "0"
    form["sign_string"] = _click_md5(
        form["click_trans_id"], services.CLICK_SERVICE_ID, services.CLICK_SECRET_KEY,
        form["merchant_trans_id"], form["amount"], action, form["sign_time"],
    )
    form["amount"] = "999999"  # attacker inflates the amount after signing
    assert services.verify_click_sign(form, action) is False


def test_verify_click_sign_complete_valid():
    form = {
        "click_trans_id": "1", "merchant_trans_id": "order1",
        "merchant_prepare_id": "77", "amount": "10000",
        "sign_time": "2026-01-01 00:00:00",
    }
    action = "1"
    form["sign_string"] = _click_md5(
        form["click_trans_id"], services.CLICK_SERVICE_ID, services.CLICK_SECRET_KEY,
        form["merchant_trans_id"], form["merchant_prepare_id"], form["amount"], action, form["sign_time"],
    )
    assert services.verify_click_sign(form, action) is True


def test_verify_click_sign_rejects_missing_signature():
    form = {"click_trans_id": "1", "merchant_trans_id": "order1", "amount": "10000", "sign_time": "x"}
    assert services.verify_click_sign(form, "0") is False


# ---------- JWT auth ----------
def test_create_and_decode_token_roundtrip():
    token = auth.create_token("user-42", is_admin=False)
    data = auth.decode_token(token)
    assert data["sub"] == "user-42"
    assert data["is_admin"] is False


def test_decode_token_rejects_garbage():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        auth.decode_token("not-a-real-jwt")
    assert exc_info.value.status_code == 401


def test_decode_token_rejects_wrong_secret():
    import jwt as pyjwt
    from fastapi import HTTPException
    bad_token = pyjwt.encode({"sub": "u1"}, "wrong-secret", algorithm="HS256")
    with pytest.raises(HTTPException):
        auth.decode_token(bad_token)


# ---------- Telegram WebApp initData validation ----------
def _build_valid_init_data(bot_token: str, user_json: str) -> str:
    params = {"auth_date": str(int(time.time())), "user": user_json}
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    params["hash"] = calc_hash
    return urlencode(params)


def test_validate_telegram_init_data_accepts_correctly_signed_payload():
    bot_token = "123456:FAKE-BOT-TOKEN-FOR-TESTS"
    user_json = '{"id": 555, "first_name": "Test"}'
    init_data = _build_valid_init_data(bot_token, user_json)
    user = auth.validate_telegram_init_data(init_data, bot_token)
    assert user["id"] == 555


def test_validate_telegram_init_data_rejects_tampered_hash():
    from fastapi import HTTPException
    bot_token = "123456:FAKE-BOT-TOKEN-FOR-TESTS"
    user_json = '{"id": 555, "first_name": "Test"}'
    init_data = _build_valid_init_data(bot_token, user_json)
    tampered = init_data.replace("Test", "Hacker")
    with pytest.raises(HTTPException) as exc_info:
        auth.validate_telegram_init_data(tampered, bot_token)
    assert exc_info.value.status_code == 403


def test_validate_telegram_init_data_rejects_wrong_bot_token():
    from fastapi import HTTPException
    bot_token = "123456:FAKE-BOT-TOKEN-FOR-TESTS"
    user_json = '{"id": 555, "first_name": "Test"}'
    init_data = _build_valid_init_data(bot_token, user_json)
    with pytest.raises(HTTPException):
        auth.validate_telegram_init_data(init_data, "different-bot-token")


# ---------- password hashing ----------
def test_hash_pw_and_check_pw_roundtrip():
    hashed = core.hash_pw("correct horse battery staple")
    assert core.check_pw("correct horse battery staple", hashed) is True
    assert core.check_pw("wrong password", hashed) is False


def test_check_pw_handles_malformed_hash_gracefully():
    assert core.check_pw("anything", "not-a-bcrypt-hash") is False


# ---------- _build_me_payload() — embedded in login/register/telegram-auth
# responses so the client can skip the follow-up /auth/me round-trip ----------
def test_build_me_payload_matches_auth_me_shape():
    payload = auth_r._build_me_payload(FULL_USER)
    # Same public fields as user_public(include_private=True)...
    for field in PRIVATE_FIELDS:
        assert field in payload
    # ...plus the /auth/me-specific extras.
    for extra in ["onboarded", "is_admin", "message_filters", "language"]:
        assert extra in payload


def test_build_me_payload_defaults_missing_fields_safely():
    minimal_user = {"id": "u2", "name": "Minimal"}
    payload = auth_r._build_me_payload(minimal_user)
    assert payload["id"] == "u2"
    assert payload["onboarded"] is False
    assert payload["is_admin"] is False
    assert payload["language"] == "uz"


# ---------- can_initiate_chat() — the chat monetization gate ----------
class _FakeCollection:
    def __init__(self, count_result=0, find_one_result=None):
        self._count_result = count_result
        self._find_one_result = find_one_result

    async def count_documents(self, *_a, **_kw):
        return self._count_result

    async def find_one(self, *_a, **_kw):
        return self._find_one_result


def _patch_db(monkeypatch, messages_count=0, unlock=None, saved_find_one_results=None):
    fake_db = type("FakeDb", (), {})()
    fake_db.messages = _FakeCollection(count_result=messages_count)
    fake_db.chat_unlocks = _FakeCollection(find_one_result=unlock)
    saved_results = iter(saved_find_one_results or [None, None])
    fake_saved = type("FakeSaved", (), {})()
    fake_saved.find_one = lambda *_a, **_kw: _next_result(saved_results)
    fake_db.saved = fake_saved
    monkeypatch.setattr(chat_r, "db", fake_db)


async def _next_result(it):
    return next(it)


def test_can_initiate_chat_paid_plan_always_allowed(monkeypatch):
    _patch_db(monkeypatch)
    sender = {"id": "u1", "plan": "premium"}
    assert asyncio.run(chat_r.can_initiate_chat(sender, "u2")) is True


def test_can_initiate_chat_free_plan_blocked_by_default(monkeypatch):
    _patch_db(monkeypatch, messages_count=0, unlock=None, saved_find_one_results=[None, None])
    sender = {"id": "u1", "plan": "free"}
    assert asyncio.run(chat_r.can_initiate_chat(sender, "u2")) is False


def test_can_initiate_chat_free_plan_allowed_if_target_messaged_first(monkeypatch):
    _patch_db(monkeypatch, messages_count=1)
    sender = {"id": "u1", "plan": "free"}
    assert asyncio.run(chat_r.can_initiate_chat(sender, "u2")) is True


def test_can_initiate_chat_free_plan_allowed_with_paid_unlock(monkeypatch):
    _patch_db(monkeypatch, messages_count=0, unlock={"user_id": "u1", "target_id": "u2"})
    sender = {"id": "u1", "plan": "free"}
    assert asyncio.run(chat_r.can_initiate_chat(sender, "u2")) is True


def test_can_initiate_chat_free_plan_allowed_on_mutual_match(monkeypatch):
    _patch_db(monkeypatch, messages_count=0, unlock=None, saved_find_one_results=[{"owner_id": "u1"}, {"owner_id": "u2"}])
    sender = {"id": "u1", "plan": "free"}
    assert asyncio.run(chat_r.can_initiate_chat(sender, "u2")) is True


# ---------- free_weekly_left() — the freemium initiation allowance ----------
def test_free_weekly_left_fresh_free_user(monkeypatch):
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 1)
    # no free_init_week set -> full allowance
    assert chat_r.free_weekly_left({"plan": "free"}) == 1


def test_free_weekly_left_spent_this_week(monkeypatch):
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 1)
    user = {"plan": "free", "free_init_week": chat_r._week_id(), "free_init_used": 1}
    assert chat_r.free_weekly_left(user) == 0


def test_free_weekly_left_resets_next_week(monkeypatch):
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 1)
    # a stale week id means the counter is treated as reset
    user = {"plan": "free", "free_init_week": "2000-W01", "free_init_used": 5}
    assert chat_r.free_weekly_left(user) == 1


def test_free_weekly_left_zero_for_paid_and_when_disabled(monkeypatch):
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 1)
    assert chat_r.free_weekly_left({"plan": "premium"}) == 0
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    assert chat_r.free_weekly_left({"plan": "free"}) == 0


# ---------- rate limiter: X-Forwarded-For spoofing + memory leak (audit fix) ----------
class _FakeClient:
    host = "10.0.0.1"  # the actual TCP peer - always our own edge proxy


class _FakeRequest:
    def __init__(self, headers: dict):
        self.client = _FakeClient()
        self.headers = headers


def test_client_ip_uses_rightmost_xff_entry_not_leftmost():
    """The leftmost X-Forwarded-For entry is whatever the caller claims and
    can be forged fresh on every request; only the rightmost hop (appended
    by our own trusted edge proxy) can't be spoofed by the client. Trusting
    the leftmost entry let anyone bypass rate limiting for free."""
    spoofed = _FakeRequest({"x-forwarded-for": "1.2.3.4, 10.0.0.1"})
    assert core._client_ip(spoofed) == "10.0.0.1"


def test_client_ip_falls_back_to_tcp_peer_without_header():
    req = _FakeRequest({})
    assert core._client_ip(req) == "10.0.0.1"


def test_rate_limiter_blocks_after_max_attempts_from_same_key():
    limiter = core.RateLimiter(max_attempts=3, window_sec=60)
    for _ in range(3):
        limiter.check("k")
    with pytest.raises(Exception):
        limiter.check("k")


def test_rate_limiter_spoofed_xff_no_longer_bypasses_limit():
    """Regression for the fix above: rotating a fake X-Forwarded-For per
    request used to mint a fresh rate-limit bucket every time."""
    limiter = core.RateLimiter(max_attempts=2, window_sec=60)
    for i in range(2):
        req = _FakeRequest({"x-forwarded-for": f"{i}.{i}.{i}.{i}, 10.0.0.1"})
        limiter.check(f"auth:{core._client_ip(req)}")
    req = _FakeRequest({"x-forwarded-for": "9.9.9.9, 10.0.0.1"})
    with pytest.raises(Exception):
        limiter.check(f"auth:{core._client_ip(req)}")


def test_rate_limiter_gc_drops_only_stale_buckets():
    limiter = core.RateLimiter(max_attempts=5, window_sec=1)
    limiter.check("stale")
    limiter.check("fresh")
    time.sleep(1.1)
    limiter.check("fresh")  # keeps "fresh" alive past the window
    limiter.gc()
    assert "stale" not in limiter.hits
    assert "fresh" in limiter.hits


# ---------- telegram webhook: referral bonus must not pay on a bare /start ----------
class _FakeUsersCollection:
    def __init__(self):
        self.inc_calls = []

    async def find_one(self, query, *_a, **_kw):
        if query.get("telegram_id") == "999":
            return None  # not yet a real account
        if query.get("referral_id") == "ABC123":
            return {"id": "owner-1", "telegram_id": "owner-tg"}
        return None

    async def update_one(self, query, update):
        if "$inc" in update:
            self.inc_calls.append((query, update["$inc"]))
        return type("Res", (), {"modified_count": 1})()


class _FakePendingRefs:
    def __init__(self):
        self.upserts = []

    async def update_one(self, query, update, upsert=False):
        self.upserts.append((query, update))
        return type("Res", (), {"modified_count": 1})()


class _FakeWebhookRequest:
    def __init__(self, body: dict):
        self._body = body

    async def json(self):
        return self._body


def test_telegram_start_with_referral_does_not_credit_balance(monkeypatch):
    """A bare bot '/start CODE' message requires no real account and no
    verified Telegram WebApp session - scripting throwaway accounts to send
    it used to farm free non-withdrawable balance. Attribution should still
    be recorded (for the real reward paid at actual signup), but no balance
    may move here."""
    from routers import telegram_r

    fake_users = _FakeUsersCollection()
    fake_pending = _FakePendingRefs()
    fake_db = type("FakeDb", (), {})()
    fake_db.users = fake_users
    fake_db.pending_refs = fake_pending
    monkeypatch.setattr(telegram_r, "db", fake_db)
    monkeypatch.setattr(telegram_r, "TELEGRAM_WEBHOOK_SECRET", "test-secret")

    async def _noop_send(*_a, **_kw):
        return None
    monkeypatch.setattr(telegram_r, "send_telegram_message", _noop_send)

    body = {"message": {"text": "/start ABC123", "chat": {"id": 1}, "from": {"id": 999}}}
    req = _FakeWebhookRequest(body)
    asyncio.run(telegram_r.telegram_webhook(req, secret="test-secret"))

    assert fake_users.inc_calls == [], "balance/ref_count must not be credited on a bare /start"
    assert len(fake_pending.upserts) == 1, "attribution should still be recorded for later real-signup payout"
