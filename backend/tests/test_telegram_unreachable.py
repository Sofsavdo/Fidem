"""A chat that blocked the bot is flagged once and skipped afterwards."""
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
import lifecycle  # noqa: E402


def test_blocked_chat_is_flagged_and_skipped(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, lifecycle):
        monkeypatch.setattr(mod, "db", db, raising=False)
    from datetime import timedelta
    old = core.iso(core.now_utc() - timedelta(days=3))
    asyncio.run(db.bot_starts.insert_one({"telegram_id": 5, "chat_id": 5, "first_start_at": old, "nudge_stage": 0}))
    asyncio.run(db.users.insert_one({"id": "u", "telegram_id": "7", "onboarded": False, "created_at": old}))
    sent = []

    async def fake_send(chat_id, text, reply_markup=None):
        sent.append(chat_id)
        return "unreachable"

    monkeypatch.setattr(lifecycle, "send_telegram_message_status", fake_send)
    monkeypatch.setattr(lifecycle, "SEND_PACING_SECONDS", 0, raising=False)
    fn = lifecycle._onboarding_nudges
    asyncio.run(fn())
    assert asyncio.run(db.bot_starts.find_one({"chat_id": 5}))["unreachable"] is True
    assert asyncio.run(db.users.find_one({"id": "u"}))["telegram_unreachable"] is True
    # the next pass sends nothing to them
    sent.clear()
    asyncio.run(db.bot_starts.update_one({"chat_id": 5}, {"$set": {"nudge_stage": 0}}))
    asyncio.run(fn())
    assert sent == []
