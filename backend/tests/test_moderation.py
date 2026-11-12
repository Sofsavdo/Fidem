"""Chat moderation: whole-word rules, AI layer (fails open), strikes -> mute."""
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

import moderation  # noqa: E402

BLOCK = {
    "sen ahmoq ekansan": "insult", "Ахмоқ": "insult", "fohisha": "obscene",
    "kel yotaylik": "sexual", "ko'krak rasmingni tashla": "sexual",
    "иди нахуй": "obscene", "сука": "obscene", "fuck you": "obscene",
    "blyat": "obscene", "я тебя ебу": "obscene",
}
ALLOW = [
    "uyda yotibman, charchadim",  # the old substring list blocked this ("yotib")
    "Salom, qandaysiz?", "siz juda chiroylisiz", "seksiya mashg'ulotiga boraman",
    "sikl yakunlandi", "Ахмедов", "it is ok", "Небо красивое", "хуже не будет",
    "Oilangiz haqida aytib bering", "Namoz o'qiysizmi?",
]


@pytest.mark.parametrize("text,cat", BLOCK.items())
def test_rules_block(text, cat):
    assert moderation.rule_check(text) == cat


@pytest.mark.parametrize("text", ALLOW)
def test_rules_allow_ordinary_words(text):
    assert moderation.rule_check(text) == ""


def test_ai_failure_lets_the_message_through(monkeypatch):
    import ai_service

    async def boom(*a, **k):
        raise TimeoutError()

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", boom)
    moderation._cache.clear()
    assert asyncio.run(moderation.ai_check("bu uzunroq oddiy xabar, hammasi joyida")) == ""


def test_ai_block_and_cache(monkeypatch):
    import ai_service
    calls = []

    async def judge(prompt, *a, **k):
        calls.append(k)
        return {"verdict": "block", "category": "harassment"}

    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "x")
    monkeypatch.setattr(ai_service, "_gemini_json", judge)
    moderation._cache.clear()
    text = "agar javob bermasang uyingga boraman"
    assert asyncio.run(moderation.ai_check(text)) == "harassment"
    assert asyncio.run(moderation.ai_check(text)) == "harassment"
    assert len(calls) == 1  # second answer came from the cache
    assert calls[0]["thinking_budget"] == 0 and calls[0]["retry"] is False
    assert asyncio.run(moderation.ai_check("salom")) == ""  # too short to ask


mongomock_motor = pytest.importorskip("mongomock_motor")


@pytest.fixture
def db(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    import core
    monkeypatch.setattr(core, "db", database)
    moderation.reset_settings_cache()
    asyncio.run(database.users.insert_one({"id": "a", "name": "A"}))
    yield database
    moderation.reset_settings_cache()


def test_three_blocks_in_a_day_mute_for_24h(db):
    for i in range(2):
        assert asyncio.run(moderation.record_block("a", "b", "ahmoq", "insult", "rules")) is False
    assert not moderation.muted_now(asyncio.run(db.users.find_one({"id": "a"})))
    assert asyncio.run(moderation.record_block("a", "b", "ahmoq", "insult", "rules")) is True
    u = asyncio.run(db.users.find_one({"id": "a"}))
    assert moderation.muted_now(u) and u["moderation_strikes"] == 3
    rep = asyncio.run(db.reports.find_one({"target_id": "a", "reason": "abuse"}))
    assert rep and rep["reporter_id"] == "system"


def test_admin_switch_turns_the_ai_off(db, monkeypatch):
    async def never(*a, **k):
        raise AssertionError("AI must not be called when switched off")

    monkeypatch.setattr(moderation, "ai_check", never)
    asyncio.run(db.settings.insert_one({"id": "moderation", "ai_enabled": False}))
    assert asyncio.run(moderation.check_message("bu uzunroq oddiy xabar, hammasi joyida")) == ("", "")
    assert asyncio.run(moderation.check_message("sen ahmoq")) == ("insult", "rules")
