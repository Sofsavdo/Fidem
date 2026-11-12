"""Profile share link: built from the bot's username and opens that profile."""
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
from routers import candidates_r, telegram_r  # noqa: E402


@pytest.fixture
def env(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, telegram_r, candidates_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    sent = []

    async def fake_send(chat_id, text, reply_markup=None):
        sent.append((text, reply_markup))
        return True

    monkeypatch.setattr(telegram_r, "send_telegram_message", fake_send)
    monkeypatch.setattr(telegram_r, "get_webapp_url", lambda: "https://app.example")
    asyncio.run(database.users.insert_many([
        {"id": "f1", "name": "Madina", "gender": "female", "birth_date": "1999-01-01", "region": "Toshkent", "onboarded": True},
        {"id": "hid", "name": "H", "gender": "female", "birth_date": "1999-01-01", "region": "Toshkent", "onboarded": True, "hidden_profile": True},
        {"id": "me", "name": "Ali", "gender": "male", "birth_date": "1995-01-01", "region": "Toshkent", "onboarded": True, "language": "uz"},
    ]))
    return database, sent


def test_share_start_opens_the_profile_and_is_not_a_referral(env):
    database, sent = env
    asyncio.run(telegram_r._handle_start(1, "555", "/start share_f1"))
    text, kb = sent[-1]
    assert kb["inline_keyboard"][0][0]["web_app"]["url"] == "https://app.example/candidate/f1"
    assert "Madina" in text
    assert not asyncio.run(database.pending_refs.find_one({"telegram_id": "555"}))


def test_hidden_profile_is_not_opened_by_a_share_link(env):
    _, sent = env
    asyncio.run(telegram_r._handle_start(1, "556", "/start share_hid"))
    assert sent[-1][1]["inline_keyboard"][0][0]["web_app"]["url"] == "https://app.example"


def test_profile_payload_carries_a_bot_share_link(env):
    pub = asyncio.run(candidates_r.candidate_detail("f1", uid="me"))
    assert pub["share_url"] == f"https://t.me/{core.TELEGRAM_BOT_USERNAME}?start=share_f1"
