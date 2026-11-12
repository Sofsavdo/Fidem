"""Guest mode (look first, register to act) and the personal-photo rules."""
from __future__ import annotations

import asyncio
import os
import sys
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
import guest  # noqa: E402
from models import SendMessageRequest, UpdateProfileRequest  # noqa: E402
from routers import auth_r, candidates_r, chat_r  # noqa: E402


def run(coro):
    return asyncio.run(coro)


def _woman(i: int, **kw) -> dict:
    d = {"id": f"w{i}", "name": f"W{i}", "gender": "female", "birth_date": "1998-01-01", "region": "Toshkent",
         "onboarded": True, "plan": "free", "photo_url": "/api/files/" + ("%024x" % (100 + i)),
         "created_at": core.iso(core.now_utc())}
    d.update(kw)
    return d


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r, candidates_r, chat_r):
        monkeypatch.setattr(mod, "db", database, raising=False)

    async def no_push(*a, **k):
        return True

    monkeypatch.setattr(chat_r, "push_notif", no_push)
    monkeypatch.setattr(candidates_r, "push_notif", no_push)
    guest._CACHE.clear()
    run(database.users.insert_many([_woman(i) for i in range(7)] + [
        {"id": "g", "name": "Guest", "gender": "male", "onboarded": False, "plan": "free", "telegram_id": "777"},
    ]))
    yield database
    guest._CACHE.clear()


def test_guest_picks_who_they_look_for_first(mdb):
    assert run(candidates_r.candidates(uid="g", limit=30)) == []
    run(auth_r.guest_start(search_gender="female", uid="g"))
    feed = run(candidates_r.candidates(uid="g", limit=30))
    assert len(feed) == 7


def test_only_four_profiles_show_photos_and_they_stay_fixed(mdb):
    run(auth_r.guest_start(search_gender="female", uid="g"))
    feed = run(candidates_r.candidates(uid="g", limit=30))
    open_ = [c for c in feed if c["photo_url"]]
    locked = [c for c in feed if c.get("guest_locked")]
    assert len(open_) == 4 and len(locked) == 3
    assert all(c["photo_url"] is None and c["photos"] == [] for c in locked)
    assert all(c["match_score"] is None for c in feed)
    first_open = {c["id"] for c in open_}
    # a new profile appearing doesn't open more photos
    run(mdb.users.insert_one(_woman(9, boost_until="2999-01-01T00:00:00+00:00")))
    feed2 = run(candidates_r.candidates(uid="g", limit=30))
    assert {c["id"] for c in feed2 if c["photo_url"]} == first_open


def test_locked_profile_detail_has_no_photo_and_leaves_no_trace(mdb):
    run(auth_r.guest_start(search_gender="female", uid="g"))
    feed = run(candidates_r.candidates(uid="g", limit=30))
    locked_id = next(c["id"] for c in feed if c.get("guest_locked"))
    open_id = next(c["id"] for c in feed if c["photo_url"])
    d = run(candidates_r.candidate_detail(locked_id, uid="g"))
    assert d["photo_url"] is None and d["guest_locked"] and d["can_message"] is False
    assert run(candidates_r.candidate_detail(open_id, uid="g"))["photo_url"]
    assert run(mdb.profile_views.count_documents({"viewer_id": "g"})) == 0


def test_guest_can_fetch_only_open_photos(mdb):
    run(auth_r.guest_start(search_gender="female", uid="g"))
    feed = run(candidates_r.candidates(uid="g", limit=30))
    open_id = next(c["id"] for c in feed if c["photo_url"])
    locked_id = next(c["id"] for c in feed if c.get("guest_locked"))
    guest.forget("g")
    may = lambda owner: run(auth_r._may_access_file("g", False, {"owner_id": owner, "storage_path": "x", "is_public": True}))
    assert may(open_id) is True
    assert may(locked_id) is False


def test_guest_actions_need_a_finished_profile(mdb):
    with pytest.raises(HTTPException) as e:
        run(guest.require_onboarded(uid="g"))
    assert e.value.detail == "onboarding_required"
    assert run(guest.require_onboarded(uid="w1")) == "w1"
    with pytest.raises(HTTPException) as e:
        run(chat_r.send_message(SendMessageRequest(to_user_id="w1", text="Salom"), uid="g"))
    assert e.value.detail == "onboarding_required"


def test_guest_can_ask_the_assistant(mdb, monkeypatch):
    import ai_assistant
    run(mdb.users.insert_one({"id": ai_assistant.ASSISTANT_ID, "name": "FIDEM yordamchisi", "is_ai": True,
                              "ai_role": "assistant", "onboarded": True, "hidden_profile": True}))
    monkeypatch.setattr(ai_assistant, "schedule_reply", lambda *a: None)
    m = run(chat_r.send_message(SendMessageRequest(to_user_id=ai_assistant.ASSISTANT_ID, text="Qanday ishlaydi?"), uid="g"))
    assert m["text"] == "Qanday ishlaydi?"


# ---------- personal photos only ----------
def _files(mdb, owner, ids):
    run(mdb.files.insert_many([{"id": "f" + i[:6], "owner_id": owner, "storage_path": i, "is_deleted": False} for i in ids]))


def test_gallery_photo_without_the_person_is_refused(mdb, monkeypatch):
    calls = []

    async def judge(ref, new, kind="gallery"):
        calls.append(kind)
        return {"valid": False, "code": "no_person", "reason": "Tabiat rasmi"}

    monkeypatch.setattr(ai_service, "verify_same_person_photo", judge)
    pid = "%024x" % 999
    _files(mdb, "w1", [pid])
    with pytest.raises(HTTPException) as e:
        run(auth_r.update_profile(UpdateProfileRequest(photos=[f"/api/files/{pid}"]), uid="w1"))
    assert e.value.detail == "photo_invalid:no_person" and calls == ["gallery"]


def test_gallery_photo_of_the_same_person_is_kept(mdb, monkeypatch):
    async def ok(ref, new, kind="gallery"):
        return {"valid": True, "code": "ok", "reason": ""}

    monkeypatch.setattr(ai_service, "verify_same_person_photo", ok)
    pid = "%024x" % 998
    _files(mdb, "w1", [pid])
    run(auth_r.update_profile(UpdateProfileRequest(photos=[f"/api/files/{pid}"]), uid="w1"))
    assert run(mdb.users.find_one({"id": "w1"}))["photos"] == [f"/api/files/{pid}"]


def test_swapping_main_photo_to_someone_else_drops_the_selfie_badge(mdb, monkeypatch):
    async def other_person(ref, new, kind="gallery"):
        return {"valid": False, "code": "different_person", "reason": ""}

    async def face_ok(image_url="", image_base64=""):
        return {"valid": True, "code": "ok"}

    async def no_push(*a, **k):
        return True

    monkeypatch.setattr(ai_service, "verify_same_person_photo", other_person)
    monkeypatch.setattr(ai_service, "verify_face_photo", face_ok)
    monkeypatch.setattr(auth_r, "push_notif", no_push)
    run(mdb.users.update_one({"id": "w2"}, {"$set": {"verified_selfie": True}}))
    run(mdb.verifications.insert_one({"user_id": "w2", "kind": "selfie", "status": "approved",
                                      "proof_url": "/api/files/" + "e" * 24, "created_at": core.iso(core.now_utc())}))
    pid = "%024x" % 997
    _files(mdb, "w2", [pid])
    run(auth_r.update_profile(UpdateProfileRequest(photo_url=f"/api/files/{pid}"), uid="w2"))
    u = run(mdb.users.find_one({"id": "w2"}))
    assert u["photo_url"].endswith(pid) and u["verified_selfie"] is False
