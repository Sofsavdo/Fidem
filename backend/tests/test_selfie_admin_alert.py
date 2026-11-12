"""Unclear selfies go to the admin bot with buttons; a tap decides them."""
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

import admin_bot  # noqa: E402
import core  # noqa: E402
from routers import payments_r  # noqa: E402


@pytest.fixture
def env(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, admin_bot, payments_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    sent, answers, edits = [], [], []

    async def fake_alert(chat_id, text, reply_markup=None):
        sent.append((chat_id, text, reply_markup))
        return True

    async def fake_answer(cb_id, text):
        answers.append(text)

    async def fake_edit(chat_id, message_id, caption):
        edits.append(caption)

    async def fake_admins():
        return [111]

    async def no_push(*a, **k):
        return True

    monkeypatch.setattr(admin_bot, "send_admin_alert", fake_alert)
    monkeypatch.setattr(admin_bot, "answer_admin_alert_callback", fake_answer)
    monkeypatch.setattr(admin_bot, "edit_admin_alert_caption", fake_edit)
    monkeypatch.setattr(admin_bot, "get_admin_chat_ids", fake_admins)
    monkeypatch.setattr(payments_r, "push_notif", no_push)
    asyncio.run(database.users.insert_one({"id": "w", "name": "Madina", "gender": "female"}))
    doc = {"id": "v1", "user_id": "w", "kind": "selfie", "status": "pending", "proof_url": "", "gesture_text": "👍"}
    asyncio.run(database.verifications.insert_one(dict(doc)))
    return database, doc, sent, answers, edits


def test_unclear_selfie_alerts_admin_and_button_approves(env):
    database, doc, sent, answers, _ = env
    asyncio.run(admin_bot.notify_admins_verification(doc, {"verdict": "unsure", "confidence": 55, "reason": "dark"}))
    assert len(sent) == 1
    chat_id, text, kb = sent[0]
    assert "👍" in text and "unsure" in text
    approve = kb["inline_keyboard"][0][0]["callback_data"]
    assert approve == "vrf:a:v1"

    cb = {"id": "c1", "from": {"id": 111}, "data": approve, "message": {"chat": {"id": 111}, "message_id": 5, "caption": text}}
    asyncio.run(admin_bot.handle_admin_callback(cb))
    assert asyncio.run(database.users.find_one({"id": "w"}))["verified_selfie"] is True
    assert asyncio.run(database.verifications.find_one({"id": "v1"}))["status"] == "approved"
    assert "TASDIQLANDI" in answers[-1]

    # a second tap (another admin) does not decide it again
    asyncio.run(admin_bot.handle_admin_callback({**cb, "id": "c2", "data": "vrf:r:v1"}))
    assert "Allaqachon" in answers[-1]
    assert asyncio.run(database.verifications.find_one({"id": "v1"}))["status"] == "approved"


def test_non_admin_cannot_decide(env):
    database, _, _, answers, _ = env
    cb = {"id": "c1", "from": {"id": 999}, "data": "vrf:a:v1", "message": {}}
    asyncio.run(admin_bot.handle_admin_callback(cb))
    assert answers[-1] == "Ruxsat yo'q"
    assert asyncio.run(database.verifications.find_one({"id": "v1"}))["status"] == "pending"
