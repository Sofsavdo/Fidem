"""Ad tracking links: t.me/<bot>?start=ad_<code> tags the people a placement brings."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import ad_links  # noqa: E402
import core  # noqa: E402
from models import TelegramAuthRequest  # noqa: E402
from routers import admin_r, auth_r, telegram_r  # noqa: E402


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, telegram_r, auth_r, admin_r):
        monkeypatch.setattr(mod, "db", database, raising=False)

    async def fake_send(*a, **k):
        return True

    async def no_log(*a, **k):
        return None

    monkeypatch.setattr(telegram_r, "send_telegram_message", fake_send)
    monkeypatch.setattr(telegram_r, "get_webapp_url", lambda: "https://app.example")
    monkeypatch.setattr(admin_r, "log_admin_action", no_log)
    monkeypatch.setattr(auth_r, "TELEGRAM_BOT_TOKEN", "x")
    return database


def _login(monkeypatch, tg_id: str, start_param: str = ""):
    monkeypatch.setattr(auth_r, "validate_telegram_init_data", lambda data, tok: {"id": tg_id, "first_name": "T" + tg_id})
    req = SimpleNamespace(client=SimpleNamespace(host="10.0.0." + tg_id[-1]), headers={})
    init = "user=%7B%7D" + (f"&start_param={start_param}" if start_param else "")
    return run(auth_r.auth_telegram(TelegramAuthRequest(init_data=init), req))


def test_admin_creates_a_link_with_a_readable_code(env):
    doc = run(admin_r.admin_create_ad_link(name="Toshkent oilaviy kanal", code="", cost_uzs=300000, note="", admin_uid="a"))
    assert doc["code"] == "toshkent_oilaviy_kanal"
    assert doc["link"] == f"https://t.me/{core.TELEGRAM_BOT_USERNAME}?start=ad_toshkent_oilaviy_kanal"
    again = run(admin_r.admin_create_ad_link(name="Toshkent oilaviy kanal", code="", cost_uzs=0, note="", admin_uid="a"))
    assert again["code"] == "toshkent_oilaviy_kanal_2"


def test_bad_code_is_refused(env):
    from fastapi import HTTPException
    with pytest.raises(HTTPException):
        run(admin_r.admin_create_ad_link(name="X", code="Bad code!", cost_uzs=0, note="", admin_uid="a"))


def test_click_signup_and_payment_are_counted_per_link(env, monkeypatch):
    run(ad_links.create("Kanal A", "kanal_a", cost_uzs=200000))
    run(ad_links.create("Kanal B", "kanal_b"))
    # two new people press START through link A, one through B
    run(telegram_r._handle_start(1, "1001", "/start ad_kanal_a"))
    run(telegram_r._handle_start(2, "1002", "/start ad_kanal_a"))
    run(telegram_r._handle_start(3, "1003", "/start ad_kanal_b"))
    # the same person clicking link B later stays with A (first touch)
    run(telegram_r._handle_start(1, "1001", "/start ad_kanal_b"))
    a = _login(monkeypatch, "1001")
    _login(monkeypatch, "1002")
    u = run(env.users.find_one({"id": a.user_id}))
    assert u["ad_source"] == "kanal_a" and not u.get("referred_by")
    run(env.users.update_one({"id": a.user_id}, {"$set": {"gender": "male", "onboarded": True}}))
    run(env.payments.insert_one({"id": "p1", "user_id": a.user_id, "status": "success", "amount": 79000, "balance_used": 0}))
    run(env.payments.insert_one({"id": "p2", "user_id": a.user_id, "status": "paid", "method": "balance", "amount": 9900}))
    rows = {r["code"]: r for r in run(admin_r.admin_ad_links(_="a"))}
    s = rows["kanal_a"]["stats"]
    assert (s["clicks"], s["signups"], s["men"], s["onboarded"], s["payers"], s["revenue_uzs"]) == (2, 2, 1, 1, 1, 79000)
    assert s["cost_per_signup"] == 100000 and s["cost_per_payer"] == 200000
    assert rows["kanal_b"]["stats"]["clicks"] == 1 and rows["kanal_b"]["stats"]["signups"] == 0


def test_existing_users_and_unknown_codes_are_not_counted(env, monkeypatch):
    run(ad_links.create("Kanal A", "kanal_a"))
    _login(monkeypatch, "2001")                       # already has an account
    run(telegram_r._handle_start(1, "2001", "/start ad_kanal_a"))
    run(telegram_r._handle_start(2, "2002", "/start ad_nope"))
    assert run(env.bot_starts.count_documents({"ad_source": {"$exists": True}})) == 0
    assert not run(env.pending_refs.find_one({"telegram_id": "2002", "ref_code": {"$exists": True}}))


def test_mini_app_link_is_attributed_too(env, monkeypatch):
    run(ad_links.create("Blogger", "blogger1"))
    r = _login(monkeypatch, "3001", start_param="ad_blogger1")
    assert run(env.users.find_one({"id": r.user_id}))["ad_source"] == "blogger1"
    assert run(ad_links.stats("blogger1"))["clicks"] == 1


def test_paused_link_stops_counting(env):
    run(ad_links.create("Kanal A", "kanal_a"))
    run(admin_r.admin_update_ad_link("kanal_a", {"active": False}, admin_uid="a"))
    run(telegram_r._handle_start(1, "4001", "/start ad_kanal_a"))
    assert run(ad_links.stats("kanal_a"))["clicks"] == 0
