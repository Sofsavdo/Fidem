"""Family contact request: clear error codes, a free receiver can accept, admin can ask."""
from __future__ import annotations

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
from routers import family_r  # noqa: E402


@pytest.fixture
def db(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, family_r):
        monkeypatch.setattr(mod, "db", database, raising=False)

    async def no_notif(*a, **kw):
        return None

    monkeypatch.setattr(family_r, "push_notif", no_notif)
    asyncio.run(database.users.insert_many([
        {"id": "p", "name": "P", "plan": "premium"},
        {"id": "f", "name": "F", "plan": "free"},
        {"id": "adm", "name": "A", "plan": "free", "is_admin": True},
    ]))
    return database


def _err(coro):
    with pytest.raises(HTTPException) as e:
        asyncio.run(coro)
    return e.value.detail


def test_request_flow_with_codes(db):
    assert _err(family_r.request_family_share("f", "", uid="p")) == "family_contact_missing"
    asyncio.run(family_r.set_family_contacts("+998901234567", "Onam", "parent", uid="p"))
    rid = asyncio.run(family_r.request_family_share("f", "", uid="p"))["id"]
    assert _err(family_r.request_family_share("f", "", uid="p")) == "family_already_requested"
    # a free receiver can accept once their own family number is on file
    assert _err(family_r.respond_family_share(rid, True, uid="f")) == "family_contact_missing"
    asyncio.run(family_r.set_family_contacts("+998907654321", "Otam", "parent", uid="f"))
    assert asyncio.run(family_r.respond_family_share(rid, True, uid="f"))["ok"]
    got = asyncio.run(family_r.get_shared_contact("f", uid="p"))
    assert got["family_contact"]["phone"] == "+998907654321"


def test_free_user_cannot_ask_but_admin_can(db):
    assert _err(family_r.request_family_share("p", "", uid="f")) == "premium_required"
    asyncio.run(family_r.set_family_contacts("+998901112233", "", "parent", uid="adm"))
    assert asyncio.run(family_r.request_family_share("p", "", uid="adm"))["ok"]
