"""Home-feed endpoints (/candidates, /saved/mine, /daily-picks): behaviour
pinned so batching their DB reads can't change what users see."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import core  # noqa: E402
from routers import candidates_r, picks_r  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, candidates_r, picks_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    return database


def _u(uid, **kw):
    d = {"id": uid, "name": uid.upper(), "plan": "free", "gender": "female", "birth_date": "1996-05-05",
         "region": "Toshkent", "language": "uz", "onboarded": True, "created_at": core.iso(core.now_utc()),
         "photo_public": False}  # lock semantics are about photos the owner closed
    d.update(kw)
    return d


def run(coro):
    return asyncio.run(coro)


def test_feed_excludes_self_blocked_hidden_and_marks_unlocks(mdb):
    async def go():
        await mdb.users.insert_many([
            _u("me", gender="male"), _u("x1"), _u("x2"), _u("blocked"), _u("blocker"),
            _u("hid", hidden_profile=True), _u("nb", onboarded=False),
        ])
        await mdb.blocks.insert_many([
            {"owner_id": "me", "target_id": "blocked"},
            {"owner_id": "blocker", "target_id": "me"},
        ])
        await mdb.photo_unlocks.insert_one({"requester_id": "me", "target_id": "x1", "approved": True})
        out = await candidates_r.candidates(uid="me", sort="match", limit=30)
        ids = {c["id"] for c in out}
        assert ids == {"x1", "x2"}
        by = {c["id"]: c for c in out}
        assert by["x1"]["photo_unlocked"] is True and by["x2"]["photo_unlocked"] is False
        # bookkeeping runs after the response
        await asyncio.sleep(0.05)
        assert (await mdb.users.find_one({"id": "me"})).get("last_active")
    run(go())


def test_feed_not_onboarded_returns_empty(mdb):
    async def go():
        await mdb.users.insert_many([_u("me", onboarded=False), _u("x1")])
        assert await candidates_r.candidates(uid="me") == []
    run(go())


def test_feed_distance_and_boost_impressions(mdb):
    async def go():
        future = core.iso(core.now_utc() + timedelta(days=1))
        await mdb.users.insert_many([_u("me", gender="male"), _u("near", boost_until=future), _u("far")])
        await mdb.user_locations.insert_many([
            {"user_id": "me", "geo_point": [69.24, 41.31]},
            {"user_id": "near", "geo_point": [69.28, 41.33]},
        ])
        out = await candidates_r.candidates(uid="me", sort="match", limit=30)
        by = {c["id"]: c for c in out}
        assert by["near"]["distance_bucket"] is not None and by["far"]["distance_bucket"] is None
        assert by["near"]["boosted"] is True and out[0]["id"] == "near"  # boost wins the top
        await asyncio.sleep(0.05)
        assert (await mdb.users.find_one({"id": "near"}))["impressions_total"] == 1
        assert not (await mdb.users.find_one({"id": "far"})).get("impressions_total")
    run(go())


def test_saved_mine_hides_hidden_and_marks_unlocks(mdb):
    async def go():
        await mdb.users.insert_many([_u("me", gender="male"), _u("a"), _u("b"), _u("h", hidden_profile=True)])
        now = core.now_utc()
        await mdb.saved.insert_many([
            {"owner_id": "me", "target_id": "a", "at": core.iso(now)},
            {"owner_id": "me", "target_id": "b", "at": core.iso(now + timedelta(seconds=1))},
            {"owner_id": "me", "target_id": "h", "at": core.iso(now + timedelta(seconds=2))},
        ])
        await mdb.photo_unlocks.insert_one({"requester_id": "me", "target_id": "b", "approved": True})
        out = await candidates_r.saved_mine(uid="me")
        assert [c["id"] for c in out] == ["b", "a"]          # newest first, hidden dropped
        assert out[0]["photo_unlocked"] is True and out[1]["photo_unlocked"] is False
    run(go())


def test_daily_picks_compute_cache_and_exclude_saved(mdb):
    async def go():
        me = _u("me", gender="male")
        await mdb.users.insert_many([me, _u("p1"), _u("p2"), _u("p3"), _u("p4"), _u("saved1")])
        await mdb.saved.insert_one({"owner_id": "me", "target_id": "saved1"})
        await mdb.photo_unlocks.insert_one({"requester_id": "me", "target_id": "p1", "approved": True})
        first = await picks_r.compute_daily_picks(me)
        assert len(first) == 3 and "saved1" not in {c["id"] for c in first}
        stored = await mdb.daily_picks.find_one({"user_id": "me"})
        assert stored and len(stored["candidate_ids"]) == 3
        # second call is served from the cache, same people, same order
        second = await picks_r.compute_daily_picks(me)
        assert [c["id"] for c in second] == [c["id"] for c in first]
        for c in first:
            assert c["photo_unlocked"] == (c["id"] == "p1")
    run(go())


def test_daily_picks_empty_pool(mdb):
    async def go():
        me = _u("me", gender="male")
        await mdb.users.insert_one(me)
        assert await picks_r.compute_daily_picks(me) == []
    run(go())
