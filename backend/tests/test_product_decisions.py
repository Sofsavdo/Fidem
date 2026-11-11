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


def test_user_without_photo_cannot_like_or_message_and_is_hidden(mdb, monkeypatch):
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
        # browsing is not emptied server-side (the app shows the upload screen);
        # liking and messaging are what is refused
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


# ---------- gallery (extra photos) ----------
def _file(owner, fid):
    return {"id": "f" + fid[:6], "owner_id": owner, "storage_path": fid, "is_deleted": False}


def test_extra_photos_validated_capped_and_hidden_when_locked(mdb):
    from models import UpdateProfileRequest
    ids = [("%024x" % i) for i in range(1, 8)]

    async def go():
        await mdb.users.insert_one(_u("me"))
        await mdb.files.insert_many([_file("me", i) for i in ids] + [_file("other", "9" * 24)])
        r = await auth_r.update_profile(UpdateProfileRequest(photos=[f"https://old.example/api/files/{i}" for i in ids[:3]] + [f"/api/files/{ids[0]}"]), uid="me")
        me = await mdb.users.find_one({"id": "me"})
        assert me["photos"] == [f"/api/files/{i}" for i in ids[:3]]  # host stripped, de-duplicated
        with pytest.raises(HTTPException) as e:   # someone else's file
            await auth_r.update_profile(UpdateProfileRequest(photos=["/api/files/" + "9" * 24]), uid="me")
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e:   # too many
            await auth_r.update_profile(UpdateProfileRequest(photos=[f"/api/files/{i}" for i in ids[:6]]), uid="me")
        assert e.value.detail == "too_many_photos"
        # removal
        await auth_r.update_profile(UpdateProfileRequest(photos=[]), uid="me")
        assert (await mdb.users.find_one({"id": "me"}))["photos"] == []
    run(go())

    pub = core.user_public(_u("x", photos=["/api/files/" + "a" * 24, "https://img.example/x.png"]))
    assert pub["photos"] == ["/api/files/" + "a" * 24]            # only own files
    closed = core.strip_locked_photo(core.user_public(_u("y", photo_public=False, photos=["/api/files/" + "a" * 24])))
    assert closed["photos"] == [] and closed["photo_url"] is None


def test_admin_without_photo_is_exempt_from_the_photo_gate(mdb, monkeypatch):
    from routers import candidates_r
    from models import SaveRequest
    monkeypatch.setattr(candidates_r, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_many([_u("adm", is_admin=True, photo_url=None), _u("t", gender="female")])
        r = await candidates_r.save_user(SaveRequest(user_id="t"), uid="adm")
        assert r  # no photo_required for admins
    run(go())


# ---------- file access ----------
def test_file_access_private_proofs_and_closed_photos(mdb):
    auth_r._OWNER_PHOTO_CACHE.clear()
    main, extra, proof = "a" * 24, "b" * 24, "c" * 24

    async def go():
        await mdb.users.insert_many([
            _u("owner", photo_public=False, photo_url=f"/api/files/{main}", photos=[f"/api/files/{extra}"]),
            _u("open", photo_url="/api/files/" + "d" * 24),
        ])
        recs = {
            main: {"owner_id": "owner", "storage_path": main, "is_public": True},
            extra: {"owner_id": "owner", "storage_path": extra, "is_public": True},
            proof: {"owner_id": "owner", "storage_path": proof, "is_public": False},
            "d" * 24: {"owner_id": "open", "storage_path": "d" * 24, "is_public": True},
        }
        may = lambda uid, key, admin=False: auth_r._may_access_file(uid, admin, recs[key])
        # closed profile photos (main + gallery): owner and admin yes, strangers no
        assert await may("owner", main) and await may("adm", main, True)
        assert not await may("stranger", main) and not await may("stranger", extra)
        # an approved unlock opens them
        await mdb.photo_unlocks.insert_one({"requester_id": "friend", "target_id": "owner", "approved": True})
        assert await may("friend", main) and await may("friend", extra)
        # private proofs: owner/admin only - not strangers, and not even someone with a photo unlock
        assert await may("owner", proof) and await may("adm", proof, True)
        assert not await may("stranger", proof) and not await may("friend", proof)
        # open profile photos stay open to every signed-in user
        assert await may("stranger", "d" * 24)
    run(go())
    auth_r._OWNER_PHOTO_CACHE.clear()


def test_existing_proofs_and_receipts_are_made_private(mdb, monkeypatch):
    import server
    monkeypatch.setattr(server, "db", mdb, raising=False)

    async def go():
        await mdb.files.insert_many([
            {"storage_path": "p1", "owner_id": "u", "is_public": True},
            {"storage_path": "p2", "owner_id": "u", "is_public": True},
            {"storage_path": "photo", "owner_id": "u", "is_public": True},
        ])
        await mdb.verifications.insert_one({"proof_url": "https://x.example/api/files/p1"})
        await mdb.manual_topups.insert_one({"proof_url": "/api/files/p2?auth=abc"})
        await server.privatize_existing_proofs()
        got = {f["storage_path"]: f["is_public"] async for f in mdb.files.find({})}
        assert got == {"p1": False, "p2": False, "photo": True}
    run(go())


# ---------- invented seed stories are never shown ----------
def test_seeded_fake_stories_are_hidden_but_real_ones_stay(mdb, monkeypatch):
    from routers import stories_r
    monkeypatch.setattr(stories_r, "db", mdb, raising=False)

    async def go():
        stock = "https://images.unsplash.com/photo-1519741497674-611481863552?w=800"
        await mdb.success_stories.insert_many([
            {"id": "s1", "couple_names": "Aziza & Bobur", "photo_url": stock, "published": True, "created_at": "2026-01-01"},
            {"id": "s2", "couple_names": "Dilnoza & Sardor", "photo_url": stock, "published": True, "created_at": "2026-01-02"},
            {"id": "r1", "couple_names": "Aziza & Bobur", "photo_url": "/api/files/" + "a" * 24, "published": True, "created_at": "2026-01-03"},
            {"id": "r2", "couple_names": "Real Couple", "photo_url": stock, "published": True, "created_at": "2026-01-04"},
        ])
        ids = {x["id"] for x in await stories_r.list_stories()}
        assert ids == {"r1", "r2"}
        with pytest.raises(HTTPException):
            await stories_r.get_story("s1")
    run(go())


# ---------- "who liked/viewed me" opens while nothing can be bought ----------
def test_interest_lists_unlock_only_while_payments_are_unavailable(mdb, monkeypatch):
    from routers import candidates_r
    monkeypatch.setattr(candidates_r, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_many([_u("me"), _u("fan", name="Madina")])
        await mdb.saved.insert_one({"owner_id": "fan", "target_id": "me", "at": "2026-01-01"})

        async def avail():
            return False
        monkeypatch.setattr(candidates_r, "payments_available", avail)
        out = await candidates_r.saved_by_others(uid="me")
        assert out[0]["name"] == "Madina" and not out[0].get("locked")      # nothing to buy -> open

        async def avail2():
            return True
        monkeypatch.setattr(candidates_r, "payments_available", avail2)
        out = await candidates_r.saved_by_others(uid="me")
        assert out[0].get("locked") is True and out[0]["name"] != "Madina"  # paywall is back
    run(go())


# ---------- reply reminders ----------
def test_reply_reminder_once_per_waiting_message(mdb, monkeypatch):
    import lifecycle
    from datetime import timedelta
    monkeypatch.setattr(lifecycle, "db", mdb, raising=False)
    monkeypatch.setattr(lifecycle, "SEND_PACING_SECONDS", 0)
    sent = []

    async def fake_push(uid, kind, text, link=None, marketing=False):
        sent.append((uid, kind, link, marketing))
    monkeypatch.setattr(lifecycle, "push_notif", fake_push)

    def ago(h):
        return core.iso(core.now_utc() - timedelta(hours=h))

    async def go():
        await mdb.users.insert_many([_u("a", name="Aziza"), _u("b"), _u("c"), _u("d")])
        await mdb.messages.insert_many([
            {"id": "m1", "chat_id": "a_b", "from_user_id": "a", "to_user_id": "b", "text": "salom", "created_at": ago(30)},   # waiting 30h
            {"id": "m2", "chat_id": "a_c", "from_user_id": "a", "to_user_id": "c", "text": "salom", "created_at": ago(40)},
            {"id": "m3", "chat_id": "a_c", "from_user_id": "c", "to_user_id": "a", "text": "javob", "created_at": ago(3)},    # answered recently
            {"id": "m4", "chat_id": "a_d", "from_user_id": "a", "to_user_id": "d", "text": "salom", "created_at": ago(2)},    # too fresh
        ])
        await lifecycle._reply_reminders()
        assert sent == [("b", "message", "/chat/a", True)]
        await lifecycle._reply_reminders()
        assert len(sent) == 1  # no repeat for the same waiting message
    run(go())


# ---------- admin rights are checked against the account, not only the token ----------
def test_revoked_admin_token_is_refused(mdb, monkeypatch):
    import auth
    monkeypatch.setattr(core, "db", mdb, raising=False)

    async def go():
        await mdb.users.insert_one(_u("adm", is_admin=True))
        tok = auth.create_token("adm", is_admin=True) if hasattr(auth, "create_token") else None
        if tok is None:
            pytest.skip("no token factory")
        assert await auth.get_current_admin(f"Bearer {tok}") == "adm"
        await mdb.users.update_one({"id": "adm"}, {"$set": {"is_admin": False}})
        with pytest.raises(HTTPException) as e:
            await auth.get_current_admin(f"Bearer {tok}")
        assert e.value.status_code == 403
    run(go())


# ---------- AI plumbing ----------
def test_gemini_answer_parsing_and_self_check(monkeypatch):
    import ai_service

    class R:
        def __init__(self, payload, status=200, text=""):
            self.payload = payload; self.status_code = status; self.text = text
        def raise_for_status(self): pass
        def json(self): return self.payload

    class C:
        def __init__(self, payload, reject_thinking=False):
            self.payload = payload; self.body = None; self.calls = 0; self.reject_thinking = reject_thinking
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, params=None, json=None):
            self.calls += 1
            if self.reject_thinking and "thinkingConfig" in json["generationConfig"]:
                return R({}, 400, "Unknown name thinkingConfig")
            self.body = json
            return R(self.payload)

    ok_payload = {"candidates": [{"content": {"parts": [{"text": "thinking...", "thought": True}, {"text": '{"ok": true}'}]}}]}
    monkeypatch.setattr(ai_service, "_THINKING_SUPPORTED", True)
    cl = C(ok_payload)
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", lambda **kw: cl)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "k")
    st = asyncio.run(ai_service.ai_self_check())
    assert st["ok"] is True and st["provider"] == "gemini"
    assert cl.body["generationConfig"]["maxOutputTokens"] == 256
    # A small thinking budget is sent so answers come back well inside the timeout.
    assert cl.body["generationConfig"]["thinkingConfig"]["thinkingBudget"] == ai_service.GEMINI_THINKING_BUDGET

    # A model that rejects thinkingConfig gets one retry without it, then never again.
    cl = C(ok_payload, reject_thinking=True)
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", lambda **kw: cl)
    st = asyncio.run(ai_service.ai_self_check())
    assert st["ok"] is True and cl.calls == 2 and "thinkingConfig" not in cl.body["generationConfig"]
    assert ai_service._THINKING_SUPPORTED is False

    cut = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {}}]}
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", lambda **kw: C(cut))
    st = asyncio.run(ai_service.ai_self_check())
    assert st["ok"] is False and "chala" in st["error"]

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "")
    st = asyncio.run(ai_service.ai_self_check())
    assert st["ok"] is False and "GEMINI_API_KEY" in st["error"]


def test_failed_ai_insights_are_not_cached(mdb, monkeypatch):
    from routers import admin_r
    import ai_service
    monkeypatch.setattr(admin_r, "db", mdb, raising=False)
    calls = []

    async def fake_insights(data):
        calls.append(1)
        return {"ai_generated": False, "error": "x"}
    monkeypatch.setattr(ai_service, "generate_growth_insights", fake_insights)

    async def fake_data():
        return "d"
    monkeypatch.setattr(admin_r, "_build_insights_data", fake_data)

    async def go():
        await admin_r.admin_ai_insights(force=False, _="adm")
        await admin_r.admin_ai_insights(force=False, _="adm")
        assert len(calls) == 2  # a failure is retried, not served from cache
        assert await mdb.ai_insights_cache.count_documents({}) == 0
    run(go())


def test_insights_report_the_gemini_reason_without_anthropic(monkeypatch):
    import ai_service
    import httpx

    async def boom(*a, **kw):
        raise httpx.ReadTimeout("slow")

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "k")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(ai_service, "_gemini_json", boom)
    res = asyncio.run(ai_service.generate_growth_insights("users: 10"))
    assert res["ai_generated"] is False and "timeout" in res["error"]


def test_gemini_retries_a_temporary_503(monkeypatch):
    import ai_service

    class R:
        def __init__(self, status, payload):
            self.status_code = status; self.payload = payload; self.text = ""
        def raise_for_status(self):
            if self.status_code >= 400:
                raise RuntimeError(self.status_code)
        def json(self): return self.payload

    ok = {"candidates": [{"content": {"parts": [{"text": '{"ok": true}'}]}}]}

    class C:
        def __init__(self): self.calls = 0
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, url, params=None, json=None):
            self.calls += 1
            return R(503, {}) if self.calls == 1 else R(200, ok)

    cl = C()
    monkeypatch.setattr(ai_service.httpx, "AsyncClient", lambda **kw: cl)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(ai_service, "_GEMINI_RETRY_DELAYS", (0, 0))
    st = asyncio.run(ai_service.ai_self_check())
    assert st["ok"] is True and cl.calls == 2
