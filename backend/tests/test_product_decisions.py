"""Product decisions: open photos by default, short signup, payments-off state."""
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
from models import OnboardingProfile, UpdateProfileRequest  # noqa: E402
from routers import auth_r, payments_r, settings_r  # noqa: E402
from services import compute_match  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r, payments_r, settings_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    return database


def run(coro):
    return asyncio.run(coro)


def _u(uid, **kw):
    d = {"id": uid, "name": uid.upper(), "plan": "free", "gender": "male", "birth_date": "1995-01-01",
         "region": "Toshkent", "language": "uz", "onboarded": True, "photo_url": "/api/files/" + "a" * 24}
    d.update(kw)
    return d


# ---------- photos: open by default, opt-out ----------
def test_photo_open_unless_owner_closed_it():
    assert core.photo_is_public({}) is True
    assert core.photo_is_public({"photo_public": True}) is True
    assert core.photo_is_public({"photo_public": False}) is False
    # what the candidate/profile payloads do with it
    opened = core.strip_locked_photo(core.user_public(_u("a")))
    assert opened["photo_url"] and opened["photo_unlocked"] is True
    closed = core.strip_locked_photo(core.user_public(_u("b", photo_public=False)))
    assert closed["photo_url"] is None and closed["photo_unlocked"] is False
    # an approved unlock still opens a closed photo
    pub = core.user_public(_u("b", photo_public=False)); pub["photo_unlocked"] = True
    assert core.strip_locked_photo(pub)["photo_url"]


def test_privacy_settings_report_open_by_default(mdb):
    async def go():
        await mdb.users.insert_one(_u("a"))
        assert (await settings_r.get_privacy_settings(uid="a"))["photo_public"] is True
        await mdb.users.insert_one(_u("b", photo_public=False))
        assert (await settings_r.get_privacy_settings(uid="b"))["photo_public"] is False
    run(go())


def test_existing_account_gets_the_open_photo_notice_exactly_once(mdb):
    async def go():
        await mdb.users.insert_many([_u("old"), _u("chose", photo_public=False)])
        await auth_r.me(uid="old")
        await auth_r.me(uid="old")          # second open: no second notice
        await auth_r.me(uid="chose")        # explicit choice: never told
        await asyncio.sleep(0.05)
        assert await mdb.notifications.count_documents({"user_id": "old", "kind": "privacy"}) == 1
        assert await mdb.notifications.count_documents({"user_id": "chose", "kind": "privacy"}) == 0
        assert (await mdb.users.find_one({"id": "old"}))["photo_notice_sent"] is True
    run(go())


# ---------- short signup ----------
def _onboard_payload(**kw):
    base = dict(
        gender="female", birth_date="1998-03-04", country="Uzbekistan", region="Toshkent",
        marital_status="single", has_children=False, search_gender="male", search_age_min=20,
        search_age_max=36, name="Madina", photo_url="http://h/api/files/" + "b" * 24, terms_accepted=True,
    )
    base.update(kw)
    return OnboardingProfile(**base)


def _prep_signup(mdb, monkeypatch, uid="n1"):
    async def ok(image_url="", image_base64=""):
        return {"valid": True, "code": "ok"}

    monkeypatch.setattr(ai_service, "verify_face_photo", ok)

    async def seed():
        await mdb.users.insert_one({"id": uid, "email": f"{uid}@x.uz", "onboarded": False, "plan": "free", "balance": 0,
                                    "created_at": core.iso(core.now_utc())})
        await mdb.files.insert_one({"storage_path": "b" * 24, "owner_id": uid, "is_deleted": False})
    return seed


def test_minimal_signup_is_accepted_and_invents_no_facts(mdb, monkeypatch):
    async def go():
        await _prep_signup(mdb, monkeypatch)()
        await auth_r.onboard(_onboard_payload(), uid="n1")
        u = await mdb.users.find_one({"id": "n1"})
        assert u["onboarded"] is True and u["photo_public"] is True and u["photo_notice_sent"] is True
        assert u["height_cm"] == 0 and u["weight_kg"] == 0 and u["smoking"] == "" and u["relocation"] is None
        pub = core.user_public(u)
        assert pub["height_cm"] == 0 and pub["smoking"] == "" and pub["relocation"] is None
        assert 40 <= u["completeness"] < 80      # complete-profile nudge stays meaningful
    run(go())


@pytest.mark.parametrize("birth", ["2015-01-01", "", "not-a-date", "1900-01-01"])
def test_signup_requires_an_adult_birth_date(mdb, monkeypatch, birth):
    async def go():
        await _prep_signup(mdb, monkeypatch)()
        with pytest.raises(HTTPException) as e:
            await auth_r.onboard(_onboard_payload(birth_date=birth), uid="n1")
        assert e.value.status_code == 400 and e.value.detail == "age_restricted"
    run(go())


def test_completing_the_profile_later_does_not_unverify(mdb, monkeypatch):
    async def go():
        await mdb.users.insert_one(_u("a", height_cm=0, weight_kg=0, verified_selfie=True))
        await auth_r.update_profile(UpdateProfileRequest(height_cm=172, weight_kg=64), uid="a")
        u = await mdb.users.find_one({"id": "a"})
        assert u["height_cm"] == 172 and u["verified_selfie"] is True and not u.get("pending_admin_review")
        # changing a fact that was already given still re-opens review
        await auth_r.update_profile(UpdateProfileRequest(height_cm=185), uid="a")
        u = await mdb.users.find_one({"id": "a"})
        assert u["verified_selfie"] is False and u["pending_admin_review"] is True
    run(go())


def test_unknown_height_is_neutral_in_matching():
    me = {"gender": "male", "birth_date": "1995-01-01", "height_cm": 0, "search_gender": "female"}
    her = {"gender": "female", "birth_date": "1998-01-01", "height_cm": 0}
    score, _ = compute_match(me, her, lang="uz")
    same, _ = compute_match({**me, "height_cm": 170}, {**her, "height_cm": 170}, lang="uz")
    assert score == same      # 0 behaves like the neutral 170, not like a 170 cm gap


# ---------- payments availability ----------
def test_topup_config_reports_whether_anything_can_be_paid_with(mdb, monkeypatch):
    async def go():
        import services
        monkeypatch.setattr(payments_r, "CLICK_SECRET_KEY", "")
        r = await payments_r.topup_config(uid="a")
        assert r["payments_available"] is False and r["click_enabled"] is False and r["p2p_enabled"] is False
        await mdb.settings.insert_one({"id": "topup_config", "p2p_enabled": True, "card_number": "8600"})
        assert (await payments_r.topup_config(uid="a"))["payments_available"] is True
        await mdb.settings.delete_many({})
        monkeypatch.setattr(payments_r, "CLICK_SECRET_KEY", "s3cret")
        monkeypatch.setattr(services, "CLICK_MERCHANT_ID", "1")
        monkeypatch.setattr(services, "CLICK_SERVICE_ID", "2")
        r = await payments_r.topup_config(uid="a")
        assert r["click_enabled"] is True and r["payments_available"] is True
    run(go())


def test_gift_recipients_endpoint_honours_open_photo_default(mdb, monkeypatch):
    from routers import gift_shop_r
    monkeypatch.setattr(gift_shop_r, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_many([
            _u("me", gender="male"),
            _u("open", gender="female", onboarded=True),
            _u("closed", gender="female", onboarded=True, photo_public=False),
        ])
        res = await gift_shop_r.gift_recipients(q="", limit=20, uid="me")
        by = {r["id"]: r for r in res}
        assert by["open"]["photo_url"] and by["closed"]["photo_url"] is None
    run(go())


# ---------- no demo data ----------
def test_only_own_hosted_photos_are_ever_returned():
    assert core.own_photo_url({"photo_url": "https://images.unsplash.com/photo-1?w=800"}) is None
    assert core.own_photo_url({}) is None
    assert core.own_photo_url({"photo_url": "/api/files/" + "b" * 24}) == "/api/files/" + "b" * 24
    assert core.own_photo_url({"photo_url": "https://x.up.railway.app/api/files/" + "b" * 24})
    stock = _u("s", photo_url="https://images.unsplash.com/photo-1?w=800")
    assert core.user_public(stock)["photo_url"] is None
    assert core.user_public_minimal(stock)["photo_url"] is None


def test_demo_profiles_stay_out_of_the_feed(mdb, monkeypatch):
    from routers import candidates_r, picks_r
    for mod in (candidates_r, picks_r):
        monkeypatch.setattr(mod, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_many([
            _u("me", gender="male", search_gender="female"),
            _u("real", gender="female"),
            _u("demo", gender="female", is_demo=True),
        ])
        out = await candidates_r.candidates(uid="me", sort="match", limit=30)
        ids = {c["id"] for c in out}
        assert "real" in ids and "demo" not in ids
    run(go())


def test_standard_and_vip_can_no_longer_be_bought(mdb):
    from models import CreatePaymentRequest
    from starlette.requests import Request
    scope = {"type": "http", "method": "POST", "path": "/", "headers": [], "client": ("1.2.3.4", 1)}

    async def go():
        for plan in ("standard", "vip"):
            with pytest.raises(HTTPException) as e:
                await payments_r.create_payment(CreatePaymentRequest(purpose=plan), Request(scope), uid="a")
            assert e.value.status_code == 400 and e.value.detail == "plan_unavailable"
    run(go())


# ---------- photo is mandatory ----------
def test_stored_absolute_urls_are_normalised_to_a_host_independent_path():
    fid = "c" * 24
    old = _u("o", photo_url=f"https://old-backend.up.railway.app/api/files/{fid}")
    assert core.own_photo_url(old) == f"/api/files/{fid}"
    assert core.user_public(old)["photo_url"] == f"/api/files/{fid}"


def test_user_without_photo_cannot_browse_like_or_message(mdb, monkeypatch):
    from routers import candidates_r, chat_r, picks_r
    from models import SaveRequest, SendMessageRequest
    for mod in (candidates_r, picks_r, chat_r):
        monkeypatch.setattr(mod, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_many([
            _u("nophoto", gender="male", search_gender="female", photo_url=None),
            _u("withphoto", gender="female"),
            _u("hasphoto2", gender="male", search_gender="female"),
        ])
        assert await candidates_r.candidates(uid="nophoto", sort="match", limit=30) == []
        assert await picks_r.daily_picks(uid="nophoto") == []
        with pytest.raises(HTTPException) as e:
            await candidates_r.save_user(SaveRequest(user_id="withphoto"), uid="nophoto")
        assert e.value.status_code == 403 and e.value.detail == "photo_required"
        with pytest.raises(HTTPException) as e:
            await chat_r.send_message(SendMessageRequest(to_user_id="withphoto", text="salom"), uid="nophoto")
        assert e.value.status_code == 403 and e.value.detail == "photo_required"
        # and they are invisible to others
        out = await candidates_r.candidates(uid="hasphoto2", sort="match", limit=30)
        ids = {c["id"] for c in out}
        assert "withphoto" in ids and "nophoto" not in ids
    run(go())
