"""AI conversation partners: labelled, free to talk to, switchable, safe."""
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

import ai_personas  # noqa: E402
import core  # noqa: E402
import storage  # noqa: E402
from models import SendMessageRequest  # noqa: E402
from routers import candidates_r, chat_r, family_r, picks_r  # noqa: E402


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
    monkeypatch.setattr(ai_personas, "push_notif", no_push)
    monkeypatch.setattr(chat_r, "FREE_WEEKLY_INITIATIONS", 0)
    ai_personas.reset_settings_cache()
    run(ai_personas.ensure_personas())
    run(database.users.insert_one({
        "id": "me", "name": "Ali", "plan": "free", "gender": "male", "birth_date": "1995-01-01",
        "region": "Toshkent", "language": "uz", "onboarded": True, "search_gender": "female",
        "search_age_min": 18, "search_age_max": 60, "photo_url": "/api/files/" + "a" * 24,
    }))
    yield database
    ai_personas.reset_settings_cache()


def test_twenty_labelled_characters_and_the_assistant(mdb):
    rows = run(mdb.users.find({"is_ai": True}).to_list(100))
    cands = [r for r in rows if r["ai_role"] == "candidate"]
    assert len(cands) == 20
    assert sum(r["gender"] == "female" for r in cands) == 10
    ages = sorted(core.age_from_birth(r["birth_date"]) for r in cands)
    assert ages[0] <= 23 and ages[-1] >= 42
    assert all(r["photo_url"].startswith("/api/files/") for r in rows)
    assistant = next(r for r in rows if r["id"] == ai_personas.ASSISTANT_ID)
    assert assistant["hidden_profile"] is True  # not in the feed
    assert core.user_public(cands[0])["is_ai"] is True


def test_avatars_are_valid_svg_with_ai_mark():
    for p in ai_personas.PERSONAS + [ai_personas.ASSISTANT]:
        svg = ai_personas.avatar_svg(p)
        xml.dom.minidom.parseString(svg)
        if p is not ai_personas.ASSISTANT:
            assert b">AI<" in svg


def test_free_user_can_write_to_an_ai_and_gets_a_reply(mdb, monkeypatch):
    replies = []
    monkeypatch.setattr(ai_personas, "schedule_reply", lambda uid, pid, cid: replies.append((uid, pid, cid)))
    m = run(chat_r.send_message(SendMessageRequest(to_user_id="ai_madina", text="Salom Madina"), uid="me"))
    assert m["text"] == "Salom Madina"
    assert replies == [("me", "ai_madina", m["chat_id"])]


def test_reply_is_generated_in_character(mdb, monkeypatch):
    import ai_service
    prompts = []

    async def fake_ai(prompt, images, schema, **kw):
        prompts.append(prompt)
        return {"reply": "Va alaykum assalom! Qayerdansiz?"}

    async def no_sleep(_):
        return None

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", fake_ai)
    monkeypatch.setattr(ai_personas.asyncio, "sleep", no_sleep)
    cid = core.chat_id_for("me", "ai_madina") if hasattr(core, "chat_id_for") else chat_r.chat_id_for("me", "ai_madina")
    run(mdb.messages.insert_one({"id": "m1", "chat_id": cid, "from_user_id": "me", "to_user_id": "ai_madina",
                                 "text": "Salom", "kind": "text", "created_at": core.iso(core.now_utc()), "read": False}))
    run(ai_personas._reply("me", "ai_madina", cid))
    got = run(mdb.messages.find_one({"from_user_id": "ai_madina"}))
    assert got["text"].startswith("Va alaykum")
    assert "Madina" in prompts[0] and "Never claim to be human" in prompts[0]
    assert run(mdb.messages.find_one({"id": "m1"}))["read"] is True


def test_reply_with_a_contact_is_dropped(mdb, monkeypatch):
    import ai_service

    async def leaky(*a, **k):
        return {"reply": "Telegramim @madina_uz yozing"}

    async def no_sleep(_):
        return None

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", leaky)
    monkeypatch.setattr(ai_personas.asyncio, "sleep", no_sleep)
    run(ai_personas._reply("me", "ai_madina", "c1"))
    assert run(mdb.messages.count_documents({"from_user_id": "ai_madina"})) == 0


def test_no_voice_no_contacts_no_family_with_an_ai(mdb):
    with pytest.raises(HTTPException) as e:
        run(chat_r.send_message(SendMessageRequest(to_user_id="ai_madina", text="", kind="voice", voice_url="/x"), uid="me"))
    assert e.value.detail == "ai_text_only"
    run(mdb.users.update_one({"id": "me"}, {"$set": {"verified_selfie": True, "plan": "premium"}}))
    with pytest.raises(HTTPException) as e:
        run(chat_r.contact_exchange_request("ai_madina", uid="me"))
    assert e.value.detail == "ai_persona"


def test_admin_switch_removes_them_from_feed_and_chat(mdb):
    feed = run(candidates_r.candidates(uid="me", limit=50))
    assert any(c["id"].startswith("ai_") and c["is_ai"] for c in feed)
    run(mdb.settings.insert_one({"id": "ai_personas", "enabled": False}))
    ai_personas.reset_settings_cache()
    feed = run(candidates_r.candidates(uid="me", limit=50))
    assert not any(c["id"].startswith("ai_") for c in feed)
    with pytest.raises(HTTPException) as e:
        run(chat_r.send_message(SendMessageRequest(to_user_id="ai_madina", text="Salom"), uid="me"))
    assert e.value.detail == "ai_off"


def test_assistant_never_in_feed(mdb):
    feed = run(candidates_r.candidates(uid="me", limit=50))
    assert ai_personas.ASSISTANT_ID not in {c["id"] for c in feed}


def test_real_people_come_before_ai(mdb):
    run(mdb.users.insert_one({
        "id": "real_f", "name": "Real", "plan": "free", "gender": "female", "birth_date": "1998-01-01",
        "region": "Samarqand", "language": "uz", "onboarded": True, "photo_url": "/api/files/" + "c" * 24,
        "created_at": core.iso(core.now_utc()),
    }))
    feed = run(candidates_r.candidates(uid="me", limit=50))
    assert feed[0]["id"] == "real_f" and not feed[0]["is_ai"]
