"""Regressions found by the full-product QA pass."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import ai_service  # noqa: E402
import core  # noqa: E402
from models import CreatePaymentRequest, PrivacySettingsRequest, SendMessageRequest, UpdateProfileRequest  # noqa: E402
from routers import admin_r, auth_r, chat_r, payments_r, settings_r  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r, chat_r, payments_r, settings_r, admin_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    return database


def run(coro):
    return asyncio.run(coro)


def _u(uid, **kw):
    d = {"id": uid, "name": uid.upper(), "plan": "free", "gender": "male", "birth_date": "1995-01-01",
         "region": "Toshkent", "language": "uz", "onboarded": True, "balance": 0,
         "photo_url": "/api/files/" + "a" * 24}
    d.update(kw)
    return d


def _future(days=30):
    return core.iso(core.now_utc() + timedelta(days=days))


# ---- admin broadcast helper used an undefined `log`
def test_admin_module_defines_log():
    assert hasattr(admin_r, "log")


# ---- Premium/VIP bundled boost must not lock hidden mode
def test_premium_user_can_enable_hidden_mode_and_gets_boost_back(mdb):
    async def go():
        until = _future()
        await mdb.users.insert_one(_u("a", plan="premium", plan_until=until, boost_until=until))
        r = await settings_r.update_privacy_settings(PrivacySettingsRequest(hidden_profile=True), uid="a")
        assert r["hidden_profile"] is True
        assert not (await mdb.users.find_one({"id": "a"})).get("boost_until")
        await settings_r.update_privacy_settings(PrivacySettingsRequest(hidden_profile=False), uid="a")
        assert (await mdb.users.find_one({"id": "a"}))["boost_until"] == until
    run(go())


def test_separately_bought_boost_still_blocks_hidden_mode(mdb):
    async def go():
        await mdb.users.insert_one(_u("a", plan="premium", plan_until=_future(30), boost_until=_future(1)))
        with pytest.raises(HTTPException) as e:
            await settings_r.update_privacy_settings(PrivacySettingsRequest(hidden_profile=True), uid="a")
        assert e.value.status_code == 400 and e.value.detail == "privacy_boost_active"
    run(go())


def test_free_user_cannot_hide(mdb):
    async def go():
        await mdb.users.insert_one(_u("a"))
        with pytest.raises(HTTPException) as e:
            await settings_r.update_privacy_settings(PrivacySettingsRequest(hidden_profile=True), uid="a")
        assert e.value.status_code == 403
    run(go())


# ---- CLICK not configured: refuse before touching the balance
def test_click_not_configured_refuses_and_keeps_balance(mdb, monkeypatch):
    async def go():
        monkeypatch.setattr(payments_r, "CLICK_SECRET_KEY", "")
        await mdb.users.insert_one(_u("a", balance=10000))
        req = CreatePaymentRequest(purpose="premium", months=1, amount=79000)
        with pytest.raises(HTTPException) as e:
            await payments_r.create_payment(req, _FakeRequest(), uid="a")
        assert e.value.status_code == 400 and e.value.detail == "click_disabled"
        assert (await mdb.users.find_one({"id": "a"}))["balance"] == 10000  # nothing deducted
        assert await mdb.payments.count_documents({}) == 0
    run(go())


class _FakeRequest:
    headers: dict = {}
    client = None


# ---- chat message sanity
@pytest.mark.parametrize("text,code", [("   ", "empty_message"), ("<b></b>", "empty_message"), ("x" * 2001, "message_too_long")])
def test_empty_and_oversize_messages_rejected(mdb, text, code):
    async def go():
        await mdb.users.insert_many([_u("a", plan="premium", plan_until=_future()), _u("b")])
        with pytest.raises(HTTPException) as e:
            await chat_r.send_message(SendMessageRequest(to_user_id="b", text=text), uid="a")
        assert e.value.status_code == 400 and e.value.detail == code
    run(go())


def test_normal_and_max_length_messages_still_ok(mdb):
    async def go():
        await mdb.users.insert_many([_u("a", plan="premium", plan_until=_future()), _u("b")])
        for text in ("salom", "x" * 2000):
            m = await chat_r.send_message(SendMessageRequest(to_user_id="b", text=text), uid="a")
            assert m["text"] == text
    run(go())


# ---- profile edits after onboarding
def test_name_cannot_be_changed_after_onboarding(mdb):
    async def go():
        await mdb.users.insert_one(_u("a", name="Aziz"))
        await auth_r.update_profile(UpdateProfileRequest(name="Hacker", bio="yangi bio"), uid="a")
        u = await mdb.users.find_one({"id": "a"})
        assert u["name"] == "Aziz" and u["bio"] == "yangi bio"
    run(go())


def test_external_photo_url_rejected_and_unchanged(mdb):
    async def go():
        await mdb.users.insert_one(_u("a", photo_url="/api/files/aaaaaaaaaaaaaaaaaaaaaaaa", photo_verified=True))
        for bad in ("http://evil.example/x.jpg", "http://169.254.169.254/latest/meta-data", "https://x.y/api/files/zzz"):
            with pytest.raises(HTTPException) as e:
                await auth_r.update_profile(UpdateProfileRequest(photo_url=bad), uid="a")
            assert e.value.status_code == 400 and e.value.detail.startswith("photo_invalid")
        assert (await mdb.users.find_one({"id": "a"}))["photo_url"] == "/api/files/aaaaaaaaaaaaaaaaaaaaaaaa"
    run(go())


def test_own_photo_is_verified_and_saved_others_rejected(mdb, monkeypatch):
    async def go():
        calls = []

        async def fake_verify(image_url="", image_base64=""):
            calls.append(image_url)
            return {"valid": True, "code": "ok"}

        monkeypatch.setattr(ai_service, "verify_face_photo", fake_verify)
        mine, theirs = "b" * 24, "c" * 24
        await mdb.users.insert_one(_u("a", photo_verified=True))
        await mdb.files.insert_many([
            {"storage_path": mine, "owner_id": "a", "is_deleted": False},
            {"storage_path": theirs, "owner_id": "someone-else", "is_deleted": False},
        ])
        with pytest.raises(HTTPException):
            await auth_r.update_profile(UpdateProfileRequest(photo_url=f"https://h/api/files/{theirs}"), uid="a")
        await auth_r.update_profile(UpdateProfileRequest(photo_url=f"https://h/api/files/{mine}"), uid="a")
        assert (await mdb.users.find_one({"id": "a"}))["photo_url"].endswith(mine) and len(calls) == 1
    run(go())


def test_rejected_face_blocks_photo_change(mdb, monkeypatch):
    async def go():
        async def fake_verify(image_url="", image_base64=""):
            return {"valid": False, "code": "no_face"}

        monkeypatch.setattr(ai_service, "verify_face_photo", fake_verify)
        mine = "d" * 24
        await mdb.users.insert_one(_u("a", photo_url="/api/files/" + "a" * 24))
        await mdb.files.insert_one({"storage_path": mine, "owner_id": "a", "is_deleted": False})
        with pytest.raises(HTTPException) as e:
            await auth_r.update_profile(UpdateProfileRequest(photo_url=f"/api/files/{mine}"), uid="a")
        assert e.value.detail == "photo_invalid:no_face"
        assert (await mdb.users.find_one({"id": "a"}))["photo_url"] == "/api/files/" + "a" * 24
    run(go())


# ---- verification image loader must not fetch arbitrary URLs (SSRF)
@pytest.mark.parametrize("url", ["http://127.0.0.1:8080/", "http://169.254.169.254/latest/meta-data/",
                                 "http://fidem-backend.railway.internal:8080/api/", "https://evil.example/a.jpg"])
def test_image_loader_refuses_external_urls(url):
    with pytest.raises(ValueError):
        run(ai_service._load_image_b64(url, ""))


# ---- family mode must be reachable on the plan that is actually sold
def test_family_mode_available_to_premium_and_vip_not_free_or_standard():
    from routers import family_r
    assert family_r._is_vip({"plan": "premium"}) and family_r._is_vip({"plan": "vip"})
    assert not family_r._is_vip({"plan": "free"}) and not family_r._is_vip({"plan": "standard"})
