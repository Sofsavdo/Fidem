"""Compatibility card: same score as the candidate card, a real AI report per
pair (cached), and an honest fallback built from the pair's matching points."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import ai_service  # noqa: E402
import core  # noqa: E402
from routers import personality_r  # noqa: E402


def _u(uid, **kw):
    d = {"id": uid, "name": uid.upper(), "plan": "premium", "gender": "male", "search_gender": "female",
         "birth_date": "1994-03-01", "region": "Toshkent", "marital_status": "single", "has_children": False,
         "religion": "Islom", "looking_for": "oila qurish", "language": "uz"}
    d.update(kw)
    return d


@pytest.fixture
def db(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, personality_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    me = _u("me")
    a = _u("a", gender="female", search_gender="male", birth_date="1997-05-01")
    b = _u("b", gender="female", search_gender="male", birth_date="1980-05-01", region="Xorazm",
           marital_status="divorced", has_children=True, religion="")
    asyncio.run(database.users.insert_many([me, a, b]))
    return database


def test_score_matches_the_card_and_is_not_zero_without_test(db, monkeypatch):
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "")
    me = asyncio.run(db.users.find_one({"id": "me"}))
    a = asyncio.run(db.users.find_one({"id": "a"}))
    res = asyncio.run(personality_r.compatibility("a", "uz", uid="me"))
    from routers.candidates_r import compute_ai_match
    assert res["score"] == compute_ai_match(me, a, "uz")[0] and res["score"] > 0
    assert res["personality_score"] is None


def test_reports_differ_per_pair_and_use_ai(db, monkeypatch):
    seen = []

    async def fake_gemini(prompt, images, schema, max_tokens=0, timeout=0):
        seen.append(prompt)
        tag = "Xorazm" if "Xorazm" in prompt else "Toshkent"
        return {"summary": f"Tahlil {tag}", "strengths": ["s"], "watch_outs": ["w"],
                "conversation_starters": ["q1", "q2", "q3"]}

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(ai_service, "_gemini_json", fake_gemini)
    ra = asyncio.run(personality_r.compatibility("a", "uz", uid="me"))
    rb = asyncio.run(personality_r.compatibility("b", "uz", uid="me"))
    assert ra["report"]["ai_generated"] and rb["report"]["ai_generated"]
    assert ra["report"]["summary"] != rb["report"]["summary"]
    assert ra["score"] != rb["score"]
    # the model never gets names or contacts
    assert all("ME" not in p.split("DATA:")[1] and '"name"' not in p for p in seen)
    # second open is served from the cache
    asyncio.run(personality_r.compatibility("a", "uz", uid="me"))
    assert len(seen) == 2


def test_fallback_uses_the_pairs_real_points(db, monkeypatch):
    async def broken(*a, **kw):
        raise ValueError("empty AI answer")

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "k")
    monkeypatch.setattr(ai_service, "_gemini_json", broken)
    res = asyncio.run(personality_r.compatibility("b", "uz", uid="me"))
    rep = res["report"]
    assert rep["ai_generated"] is False
    assert "Hududiy yaqinlik" not in rep["strengths"]          # no invented closeness
    assert str(res["score"]) in rep["summary"]
    # failures are not cached: the next open asks the AI again
    assert asyncio.run(db.compat_reports.count_documents({})) == 0


def test_free_user_sees_the_score_locked(db, monkeypatch):
    asyncio.run(db.users.update_one({"id": "me"}, {"$set": {"plan": "free"}}))
    res = asyncio.run(personality_r.compatibility("a", "uz", uid="me"))
    assert res["locked"] is True and res["score"] > 0 and "report" not in res
