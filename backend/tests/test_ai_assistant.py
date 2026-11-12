"""FIDEM assistant: pinned helper, never a candidate, free, switchable, safe."""
from __future__ import annotations

import asyncio
import os
import sys
import xml.dom.minidom
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import ai_assistant  # noqa: E402
import core  # noqa: E402
import storage  # noqa: E402
from models import SendMessageRequest  # noqa: E402
from routers import candidates_r, chat_r, family_r, picks_r  # noqa: E402

AID = ai_assistant.ASSISTANT_ID


def run(coro):
    return asyncio.run(coro)


@pytest.fixture
def mdb(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, chat_r, candidates_r, picks_r, family_r, storage):
        monkeypatch.setattr(mod, "db", database, raising=False)

    async def fake_put(path, data, ct):
        return {"path": "b" * 24, "size": len(data)}

    async def no_push(*a, **k):
        return True

    monkeypatch.setattr(storage, "put_object", fake_put)
    monkeypatch.setattr(chat_r, "push_notif", no_push)
    monkeypatch.setattr(ai_assistant, "push_notif", no_push)
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    ai_assistant.reset_settings_cache()
    run(ai_assistant.ensure_assistant())
    run(database.users.insert_one({
        "id": "me", "name": "Ali", "plan": "free", "gender": "male", "birth_date": "1995-01-01",
        "region": "Toshkent", "language": "uz", "onboarded": True, "search_gender": "female",
        "search_age_min": 18, "search_age_max": 60, "photo_url": "/api/files/" + "a" * 24,
    }))
    yield database
    ai_assistant.reset_settings_cache()


def test_only_the_assistant_exists_and_it_is_never_a_candidate(mdb):
    rows = run(mdb.users.find({"is_ai": True}).to_list(100))
    assert [r["id"] for r in rows] == [AID]
    assert rows[0]["hidden_profile"] is True and rows[0]["ai_role"] == "assistant"
    feed = run(candidates_r.candidates(uid="me", limit=50))
    assert not any(c.get("is_ai") for c in feed)


def test_avatar_is_valid_svg():
    xml.dom.minidom.parseString(ai_assistant.avatar_svg(ai_assistant.ASSISTANT))


def test_free_user_can_ask_and_gets_a_reply_scheduled(mdb, monkeypatch):
    calls = []
    monkeypatch.setattr(ai_assistant, "schedule_reply", lambda uid, pid, cid: calls.append((uid, pid, cid)))
    m = run(chat_r.send_message(SendMessageRequest(to_user_id=AID, text="Premium qancha turadi?"), uid="me"))
    assert calls == [("me", AID, m["chat_id"])]
    acc = run(chat_r.chat_access(AID, uid="me"))
    assert acc["can_message"] and acc["is_ai"] and not acc["requires_unlock"]


def test_reply_uses_app_facts(mdb, monkeypatch):
    import ai_service
    prompts = []

    async def fake_ai(prompt, images, schema, **kw):
        prompts.append(prompt)
        return {"reply": "1 kunlik Premium 9 900 so'm."}

    async def no_sleep(_):
        return None

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", fake_ai)
    monkeypatch.setattr(ai_assistant.asyncio, "sleep", no_sleep)
    cid = core.chat_id_for("me", AID)
    run(mdb.messages.insert_one({"id": "m1", "chat_id": cid, "from_user_id": "me", "to_user_id": AID,
                                 "text": "Premium qancha?", "kind": "text", "created_at": core.iso(core.now_utc()), "read": False}))
    run(ai_assistant._reply("me", AID, cid))
    assert run(mdb.messages.find_one({"from_user_id": AID}))["text"].startswith("1 kunlik")
    assert "9,900" in prompts[0] and "@Medik005" in prompts[0]


def test_reply_with_a_contact_is_dropped(mdb, monkeypatch):
    import ai_service

    async def leaky(*a, **k):
        return {"reply": "Telegram: @someone_uz"}

    async def no_sleep(_):
        return None

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", leaky)
    monkeypatch.setattr(ai_assistant.asyncio, "sleep", no_sleep)
    run(ai_assistant._reply("me", AID, "c1"))
    assert run(mdb.messages.count_documents({"from_user_id": AID})) == 0


def test_text_only_and_no_contact_exchange_or_family(mdb):
    with pytest.raises(HTTPException) as e:
        run(chat_r.send_message(SendMessageRequest(to_user_id=AID, text="", kind="voice", voice_url="/x"), uid="me"))
    assert e.value.detail == "ai_text_only"
    run(mdb.users.update_one({"id": "me"}, {"$set": {"verified_selfie": True, "plan": "premium"}}))
    with pytest.raises(HTTPException) as e:
        run(chat_r.contact_exchange_request(AID, uid="me"))
    assert e.value.detail == "ai_persona"


def test_admin_switch_off(mdb):
    run(mdb.settings.insert_one({"id": "ai_assistant", "enabled": False}))
    ai_assistant.reset_settings_cache()
    with pytest.raises(HTTPException) as e:
        run(chat_r.send_message(SendMessageRequest(to_user_id=AID, text="Salom"), uid="me"))
    assert e.value.detail == "ai_off"
