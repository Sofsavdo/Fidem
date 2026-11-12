"""Launch promo: women get Premium free; the stored plan and public badge stay real."""
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

import core  # noqa: E402
from routers import admin_r, auth_r  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, admin_r, auth_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    core.reset_promo_cache()
    asyncio.run(database.users.insert_many([
        {"id": "w", "name": "W", "gender": "female", "plan": "free", "onboarded": True, "verified_selfie": True},
        {"id": "u", "name": "U", "gender": "female", "plan": "free", "onboarded": True},
        {"id": "m", "name": "M", "gender": "male", "plan": "free", "onboarded": True},
    ]))
    yield database
    core.reset_promo_cache()


def test_women_get_premium_men_do_not(db):
    w = asyncio.run(core.get_user("w"))
    m = asyncio.run(core.get_user("m"))
    assert w["plan"] == "premium" and w["plan_source"] == "women_free"
    assert m["plan"] == "free"
    # stored plan untouched; others see her real plan on cards
    assert asyncio.run(db.users.find_one({"id": "w"}))["plan"] == "free"
    assert core.user_public(w)["plan"] == "free"
    assert core.user_public(w, include_private=True)["plan"] == "premium"
    assert auth_r._build_me_payload(w)["plan_source"] == "women_free"


def test_admin_can_switch_it_off(db):
    asyncio.run(admin_r.admin_set_promo(women_free=False, admin_uid="adm"))
    assert asyncio.run(core.get_user("w"))["plan"] == "free"
    assert asyncio.run(admin_r.admin_get_promo(_="adm"))["women_free"] is False
    asyncio.run(admin_r.admin_set_promo(women_free=True, admin_uid="adm"))
    assert asyncio.run(core.get_user("w"))["plan"] == "premium"


def test_paid_woman_keeps_her_own_plan(db):
    asyncio.run(db.users.update_one({"id": "w"}, {"$set": {"plan": "premium", "plan_until": "2099-01-01T00:00:00+00:00"}}))
    w = asyncio.run(core.get_user("w"))
    assert w["plan"] == "premium" and "plan_source" not in w


def test_unverified_woman_must_pass_selfie_first(db):
    u = asyncio.run(core.get_user("u"))
    assert u["plan"] == "free" and u["women_promo"] == "needs_selfie"
    assert core.selfie_required_to_write(u) is True
    assert auth_r._build_me_payload(u)["women_promo"] == "needs_selfie"
    w = asyncio.run(core.get_user("w"))
    assert core.selfie_required_to_write(w) is False
