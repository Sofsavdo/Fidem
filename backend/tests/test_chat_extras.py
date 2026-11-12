"""Chat extras: reply quotes, reactions, typing indicator."""
import asyncio
import os
import sys
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


def run(c):
    return asyncio.run(c)


@pytest.fixture
def env(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, chat_r):
        monkeypatch.setattr(mod, "db", db, raising=False)
    sent = []

    async def fake_send(uid, msg):
        sent.append((uid, msg))

    async def fake_bcast(uids, msg):
        for u in uids:
            sent.append((u, msg))

    async def no_push(*a, **k):
        return True

    monkeypatch.setattr(chat_r.manager, "send_to_user", fake_send)
    monkeypatch.setattr(chat_r.manager, "broadcast_chat", fake_bcast)
    monkeypatch.setattr(chat_r, "push_notif", no_push)
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    chat_r._TYPING_LAST.clear()
    for u in ("a", "b"):
        run(db.users.insert_one({"id": u, "name": u.upper(), "plan": "premium", "plan_until": "2999-01-01T00:00:00+00:00",
                                 "onboarded": True, "verified_selfie": True, "gender": "male" if u == "a" else "female", "photo_url": "/api/files/" + "a" * 24}))
    return db, sent


def test_reply_quotes_the_original(env):
    db, _ = env
    first = run(chat_r.send_message(SendMessageRequest(to_user_id="b", text="Qaysi shahardansiz?"), uid="a"))
    ans = run(chat_r.send_message(SendMessageRequest(to_user_id="a", text="Samarqanddan", reply_to=first["id"]), uid="b"))
    assert ans["reply_to"]["id"] == first["id"] and ans["reply_to"]["text"] == "Qaysi shahardansiz?"
    other = run(chat_r.send_message(SendMessageRequest(to_user_id="a", text="x", reply_to="not-in-this-chat"), uid="b"))
    assert "reply_to" not in other


def test_reactions_toggle_and_are_broadcast(env):
    db, sent = env
    m = run(chat_r.send_message(SendMessageRequest(to_user_id="b", text="Salom"), uid="a"))
    r = run(chat_r.react_to_message(m["id"], emoji="❤️", uid="b"))
    assert r["reactions"] == {"b": "❤️"}
    assert run(chat_r.react_to_message(m["id"], emoji="❤️", uid="b"))["reactions"] == {}
    with pytest.raises(HTTPException):
        run(chat_r.react_to_message(m["id"], emoji="🍺", uid="b"))
    run(db.users.insert_one({"id": "c", "onboarded": True}))
    with pytest.raises(HTTPException):
        run(chat_r.react_to_message(m["id"], emoji="👍", uid="c"))


def test_typing_is_forwarded_and_throttled(env):
    _, sent = env
    run(chat_r._ws_client_event("a", '{"type": "typing", "to": "b"}'))
    run(chat_r._ws_client_event("a", '{"type": "typing", "to": "b"}'))
    typing = [s for s in sent if s[1].get("type") == "typing"]
    assert typing == [("b", {"type": "typing", "data": {"from": "a"}})]
    run(chat_r._ws_client_event("a", "not json"))
