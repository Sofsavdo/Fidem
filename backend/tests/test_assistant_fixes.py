"""Assistant chat: membership check with "_" in ids; Gemini retries without
the thinking setting and never puts the key in the URL."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

import ai_service  # noqa: E402
import core  # noqa: E402


def test_in_chat_handles_ids_with_underscores():
    uid = "b9de5c1d-174a-4efc-a159-ff98f75b269a"
    cid = core.chat_id_for(uid, "ai_assistant")
    assert core.in_chat(cid, uid) and core.in_chat(cid, "ai_assistant")
    assert not core.in_chat(cid, "ai") and not core.in_chat(cid, "assistant_" + uid)
    assert core.in_chat(core.chat_id_for("a", "b"), "a") and not core.in_chat("a_b", "c")


class _Resp:
    def __init__(self, code, data=None, text=""):
        self.status_code, self._data, self.text = code, data or {}, text

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def test_gemini_retries_without_thinking_and_keeps_key_out_of_url(monkeypatch):
    calls = []
    ok = _Resp(200, {"candidates": [{"content": {"parts": [{"text": '{"reply": "Salom"}'}]}}]})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None, params=None):
            calls.append({"url": url, "params": params, "headers": headers,
                          "thinking": "thinkingConfig" in json["generationConfig"]})
            return _Resp(400, text="Budget 0 is invalid") if calls[-1]["thinking"] else ok

    monkeypatch.setattr(ai_service.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(ai_service, "GEMINI_API_KEY", "secret-key")
    monkeypatch.setattr(ai_service, "_ZERO_BUDGET_REJECTED", [False])
    res = asyncio.run(ai_service._gemini_json("hi", [], {"type": "OBJECT"}, thinking_budget=0))
    assert res == {"reply": "Salom"}
    assert [c["thinking"] for c in calls] == [True, False]
    assert all("secret-key" not in c["url"] and not c["params"] for c in calls)
    assert calls[0]["headers"]["x-goog-api-key"] == "secret-key"
    # the next zero-budget call skips the refused setting right away
    calls.clear()
    asyncio.run(ai_service._gemini_json("hi", [], {"type": "OBJECT"}, thinking_budget=0))
    assert [c["thinking"] for c in calls] == [False]
