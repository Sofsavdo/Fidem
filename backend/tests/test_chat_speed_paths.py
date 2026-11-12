"""Chat hot-path behaviour after the latency work: concurrent pre-checks in
send_message, cursor pagination in chat_history, grouped unread counts."""
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
from models import SendMessageRequest  # noqa: E402
from routers import chat_r  # noqa: E402


@pytest.fixture
def mdb(monkeypatch):
    client = mongomock_motor.AsyncMongoMockClient()
    database = client["t"]
    for mod in (core, chat_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    # Production runs with the weekly free initiation switched off.
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    return database


async def _seed(database):
    for uid in ("a", "b"):
        await database.users.insert_one({"id": uid, "name": uid.upper(), "plan": "free", "onboarded": True, "photo_url": "/api/files/" + "a" * 24})


def test_free_sender_without_unlock_gets_402_and_unknown_target_404(mdb):
    async def go():
        await _seed(mdb)
        with pytest.raises(HTTPException) as e:
            await chat_r.send_message(SendMessageRequest(to_user_id="b", text="salom"), uid="a")
        assert e.value.status_code == 402
        with pytest.raises(HTTPException) as e:
            await chat_r.send_message(SendMessageRequest(to_user_id="zzz", text="salom"), uid="a")
        assert e.value.status_code == 404
    asyncio.run(go())


def test_block_wins_and_mutual_save_allows(mdb):
    async def go():
        await _seed(mdb)
        await mdb.blocks.insert_one({"owner_id": "b", "target_id": "a"})
        with pytest.raises(HTTPException) as e:
            await chat_r.send_message(SendMessageRequest(to_user_id="b", text="hi"), uid="a")
        assert e.value.status_code == 403
        await mdb.blocks.delete_many({})
        await mdb.saved.insert_one({"owner_id": "a", "target_id": "b"})
        await mdb.saved.insert_one({"owner_id": "b", "target_id": "a"})
        msg = await chat_r.send_message(SendMessageRequest(to_user_id="b", text="salom"), uid="a")
        assert msg["chat_id"] == "a_b" and msg["text"] == "salom"
        await asyncio.sleep(0)  # let background tasks run
    asyncio.run(go())


def test_history_cursor_pages_back_without_repeating_and_unread_group(mdb):
    async def go():
        await _seed(mdb)
        base = core.now_utc()
        for i in range(7):
            await mdb.messages.insert_one({
                "id": f"m{i}", "chat_id": "a_b", "from_user_id": "b", "to_user_id": "a",
                "text": str(i), "kind": "text", "read": False, "status": "chat",
                "created_at": core.iso(base + timedelta(seconds=i)),
            })
        first = await chat_r.chat_history("a_b", uid="a", limit=3, before=None)
        assert [m["id"] for m in first] == ["m4", "m5", "m6"]
        # opening the chat marks the messages read
        assert await mdb.messages.count_documents({"to_user_id": "a", "read": False}) == 0
        cursor = first[0]["created_at"].isoformat().replace("+00:00", "Z")  # as the client echoes it
        second = await chat_r.chat_history("a_b", uid="a", limit=3, before=cursor)
        assert [m["id"] for m in second] == ["m1", "m2", "m3"]
        third = await chat_r.chat_history("a_b", uid="a", limit=3,
                                          before=second[0]["created_at"].isoformat())
        assert [m["id"] for m in third] == ["m0"]
    asyncio.run(go())


def test_list_chats_unread_counts(mdb):
    async def go():
        await _seed(mdb)
        for i, read in enumerate([False, False, True]):
            await mdb.messages.insert_one({
                "id": f"x{i}", "chat_id": "a_b", "from_user_id": "b", "to_user_id": "a",
                "text": "t", "kind": "text", "read": read, "status": "chat",
                "created_at": core.iso(core.now_utc() + timedelta(seconds=i)),
            })
        chats = await chat_r.list_chats(uid="a", limit=20)
        assert len(chats) == 1 and chats[0]["unread"] == 2
    asyncio.run(go())
