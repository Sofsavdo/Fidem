"""Behaviour of /chat/access and /candidates/{id} - pinned so the query
batching (fewer sequential DB round trips) can't change what they return."""
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

import core  # noqa: E402
from routers import candidates_r, chat_r  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, chat_r, candidates_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    return database


def _user(uid, **kw):
    base = {"id": uid, "name": uid.upper(), "plan": "free", "gender": "male",
            "birth_date": "1995-01-01", "region": "Toshkent", "language": "uz"}
    base.update(kw)
    return base


def run(coro):
    return asyncio.run(coro)


# ---------- /chat/access ----------
def test_access_free_user_needs_unlock(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("b")])
        r = await chat_r.chat_access("b", uid="a")
        assert r["can_message"] is False and r["requires_unlock"] is True
        assert r["is_reply"] is False and r["unlocked"] is False
        assert r["price_uzs"] == chat_r.PRICE_CHAT_UNLOCK
    run(go())


def test_access_reply_unlock_match_and_plan_open_the_composer(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("b"), _user("c"), _user("d"), _user("e")])
        # b wrote to a first -> a may reply
        await mdb.messages.insert_one({"id": "m1", "chat_id": "a_b", "from_user_id": "b", "to_user_id": "a",
                                       "text": "hi", "created_at": core.iso(core.now_utc())})
        r = await chat_r.chat_access("b", uid="a")
        assert r["can_message"] is True and r["is_reply"] is True
        # explicit unlock for c
        await mdb.chat_unlocks.insert_one({"user_id": "a", "target_id": "c", "source": "one_time",
                                           "guarantee_refunded": True})
        r = await chat_r.chat_access("c", uid="a")
        assert r["can_message"] is True and r["unlocked"] is True and r["is_reply"] is False
        # mutual save (match) with d
        await mdb.saved.insert_many([{"owner_id": "a", "target_id": "d"}, {"owner_id": "d", "target_id": "a"}])
        r = await chat_r.chat_access("d", uid="a")
        assert r["can_message"] is True and r["unlocked"] is False
        # one-sided save does NOT open it
        await mdb.saved.insert_one({"owner_id": "a", "target_id": "e"})
        r = await chat_r.chat_access("e", uid="a")
        assert r["can_message"] is False
        # an active paid plan opens everything
        await mdb.users.update_one({"id": "a"}, {"$set": {
            "plan": "premium", "plan_until": core.iso(core.now_utc() + timedelta(days=5))}})
        r = await chat_r.chat_access("e", uid="a")
        assert r["can_message"] is True and r["plan_active"] is True
    run(go())


def test_access_blocked_and_self(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("b")])
        await mdb.blocks.insert_one({"owner_id": "b", "target_id": "a"})
        r = await chat_r.chat_access("b", uid="a")
        assert r["blocked"] is True and r["can_message"] is False
        with pytest.raises(HTTPException) as e:
            await chat_r.chat_access("a", uid="a")
        assert e.value.status_code == 400
    run(go())


# ---------- /candidates/{id} ----------
def test_detail_basic_records_view_and_counts(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("b", views_total=0)])
        out = await candidates_r.candidate_detail("b", uid="a")
        assert out["id"] == "b" and "match_score" in out
        assert out["photo_unlocked"] is False and out["photo_unlock_status"] == "none"
        await asyncio.sleep(0.05)  # background bookkeeping
        assert await mdb.profile_views.find_one({"viewer_id": "a", "target_id": "b"}) is not None
        assert (await mdb.users.find_one({"id": "b"}))["views_total"] == 1
    run(go())


def test_detail_incognito_leaves_no_trace_and_unknown_target_404(mdb):
    async def go():
        await mdb.users.insert_many([
            _user("a", plan="premium", hidden_profile=True,
                  plan_until=core.iso(core.now_utc() + timedelta(days=5))),
            _user("b"),
        ])
        await candidates_r.candidate_detail("b", uid="a")
        await asyncio.sleep(0.05)
        assert await mdb.profile_views.count_documents({}) == 0
        assert (await mdb.users.find_one({"id": "b"})).get("views_total", 0) == 0
        with pytest.raises(HTTPException) as e:
            await candidates_r.candidate_detail("nope", uid="a")
        assert e.value.status_code == 404
    run(go())


def test_detail_hidden_profile_gate_and_photo_unlock(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("h", hidden_profile=True), _user("p")])
        with pytest.raises(HTTPException) as e:
            await candidates_r.candidate_detail("h", uid="a")
        assert e.value.status_code == 404
        # an existing chat lets the viewer through
        await mdb.messages.insert_one({"id": "m", "chat_id": "a_h", "from_user_id": "h", "to_user_id": "a",
                                       "text": "x", "created_at": core.iso(core.now_utc())})
        assert (await candidates_r.candidate_detail("h", uid="a"))["id"] == "h"
        # approved photo unlock is reflected
        await mdb.photo_unlocks.insert_one({"requester_id": "a", "target_id": "p", "approved": True, "status": "approved"})
        out = await candidates_r.candidate_detail("p", uid="a")
        assert out["photo_unlocked"] is True and out["photo_unlock_status"] == "approved"
    run(go())


def test_detail_distance_bucket_needs_both_locations(mdb):
    async def go():
        await mdb.users.insert_many([_user("a"), _user("b")])
        assert (await candidates_r.candidate_detail("b", uid="a"))["distance_bucket"] is None
        await mdb.user_locations.insert_many([
            {"user_id": "a", "geo_point": [69.24, 41.31]},
            {"user_id": "b", "geo_point": [69.28, 41.33]},
        ])
        assert (await candidates_r.candidate_detail("b", uid="a"))["distance_bucket"] is not None
    run(go())
