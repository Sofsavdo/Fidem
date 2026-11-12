"""Bot messages go out protected (no forwarding / saving / screenshots)."""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

import services  # noqa: E402


class _R:
    status_code = 200
    text = "{}"


def test_messages_are_sent_with_protect_content(monkeypatch):
    sent = []

    async def fake_call(method, **kw):
        sent.append((method, kw.get("json")))
        return _R()

    monkeypatch.setattr(services, "_tg_call", fake_call)
    monkeypatch.setattr(services, "PROTECT_CONTENT", True)
    assert asyncio.run(services.send_telegram_message_status(1, "salom")) == "sent"
    assert sent[-1][1]["protect_content"] is True
    monkeypatch.setattr(services, "PROTECT_CONTENT", False)
    asyncio.run(services.send_telegram_message_status(1, "salom"))
    assert "protect_content" not in sent[-1][1]
