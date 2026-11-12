"""Nomzodlar feed: pages, and the pool that is ranked."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest
from starlette.responses import Response

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import core  # noqa: E402
from core import iso, now_utc  # noqa: E402
from routers import candidates_r  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, candidates_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    return database


def _u(uid, **kw):
    d = {"id": uid, "name": uid.upper(), "plan": "free", "gender": "female", "birth_date": "1996-05-05",
         "region": "Toshkent", "language": "uz", "onboarded": True, "created_at": iso(now_utc()),
         "photo_url": "/api/files/" + "a" * 24, "last_active": iso(now_utc())}
    d.update(kw)
    return d


def run(c):
    return asyncio.run(c)


def _seed(mdb, n):
    run(mdb.users.insert_many([_u("me", gender="male")] + [_u(f"w{i:03d}") for i in range(n)]))


def test_pages_cover_everyone_once_not_just_the_first_30(mdb):
    _seed(mdb, 75)
    pages = [run(candidates_r.candidates(uid="me", limit=30, offset=o)) for o in (0, 30, 60, 90)]
    assert [len(p) for p in pages] == [30, 30, 15, 0]
    ids = [c["id"] for p in pages for c in p]
    assert len(ids) == len(set(ids)) == 75


def test_total_is_sent_in_a_header(mdb):
    _seed(mdb, 40)
    resp = Response()
    run(candidates_r.candidates(uid="me", limit=30, response=resp))
    assert resp.headers["X-Total-Count"] == "40"


def test_page_size_is_capped_and_never_below_one(mdb):
    _seed(mdb, 100)
    assert len(run(candidates_r.candidates(uid="me", limit=500))) == candidates_r.MAX_PAGE
    assert len(run(candidates_r.candidates(uid="me", limit=0))) == 1
    assert len(run(candidates_r.candidates(uid="me", limit=10, offset=-5))) == 10


def test_a_boosted_profile_is_ranked_even_when_more_people_match_than_the_pool_holds(mdb, monkeypatch):
    monkeypatch.setattr(candidates_r, "FEED_POOL", 5)
    run(mdb.users.insert_one(_u("me", gender="male")))
    old = iso(now_utc() - timedelta(days=3))
    run(mdb.users.insert_many([_u(f"w{i}", last_active=old) for i in range(10)]))
    run(mdb.users.insert_one(_u("boosted", last_active=old, boost_until=iso(now_utc() + timedelta(days=1)))))
    resp = Response()
    out = run(candidates_r.candidates(uid="me", limit=30, response=resp))
    assert out[0]["id"] == "boosted"            # the last one in database order still reaches the top
    assert len(out) == 5 and resp.headers["X-Total-Count"] == "5+"


def test_the_most_recently_active_make_the_pool(mdb, monkeypatch):
    monkeypatch.setattr(candidates_r, "FEED_POOL", 3)
    run(mdb.users.insert_one(_u("me", gender="male")))
    run(mdb.users.insert_many([
        _u("stale", last_active=iso(now_utc() - timedelta(days=30))),
        _u("a", last_active=iso(now_utc() - timedelta(hours=1))),
        _u("b", last_active=iso(now_utc() - timedelta(hours=2))),
        _u("c", last_active=iso(now_utc() - timedelta(hours=3))),
    ]))
    ids = {c["id"] for c in run(candidates_r.candidates(uid="me", limit=30))}
    assert ids == {"a", "b", "c"}
