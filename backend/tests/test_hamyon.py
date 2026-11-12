"""Hamyon API card-transfer payments: create, signed callbacks, status check, cancel."""
from __future__ import annotations

import asyncio
import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import auth  # noqa: E402
import core  # noqa: E402
import hamyon  # noqa: E402
from routers import payments_r  # noqa: E402

SHOP_ID, SHOP_KEY = "12", "test-shop-key"


@pytest.fixture
def env(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, payments_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    monkeypatch.setattr(hamyon, "HAMYON_SHOP_ID", SHOP_ID)
    monkeypatch.setattr(hamyon, "HAMYON_SHOP_KEY", SHOP_KEY)
    monkeypatch.setattr(payments_r, "HAMYON_SHOP_ID", SHOP_ID)
    monkeypatch.setattr(payments_r, "rate_limit_payment", lambda *a, **k: None)

    calls = {"create": [], "status": "pending", "cancel": [], "deliver": 0}

    async def fake_create(order_id, amount, busy=None):
        busy = set(busy or ())
        while amount in busy:
            amount += 1
        calls["create"].append((order_id, amount))
        return {"payment_id": f"hp-{order_id}", "card": "9860 0000 0000 0001", "amount": amount,
                "expires_in": 300, "expire_at": 4102444800}

    async def fake_status(hpid):
        return {"payment_id": hpid, "shop_id": int(SHOP_ID), "status": calls["status"],
                "amount": calls.get("status_amount", 0)}

    async def fake_cancel(hpid):
        calls["cancel"].append(hpid)

    monkeypatch.setattr(payments_r, "create_hamyon_payment", fake_create)
    monkeypatch.setattr(payments_r, "hamyon_payment_status", fake_status)
    monkeypatch.setattr(payments_r, "cancel_hamyon_payment", fake_cancel)

    real_process = payments_r.process_completed_payment

    async def counting_process(*a, **kw):
        calls["deliver"] += 1
        return await real_process(*a, **kw)

    monkeypatch.setattr(payments_r, "process_completed_payment", counting_process)

    app = FastAPI()
    app.include_router(payments_r.router, prefix="/api")
    app.dependency_overrides[auth.get_current_user_id] = lambda: "u1"
    asyncio.run(database.users.insert_one({"id": "u1", "name": "U", "plan": "free", "balance": 0, "onboarded": True}))
    return TestClient(app), database, calls


def _sign(payment_id, amount):
    return hashlib.md5(f"{SHOP_ID}{payment_id}{amount}{SHOP_KEY}".encode()).hexdigest()


def _complete(client, pay, status="paid", amount=None, sign=None):
    amount = pay["pay_amount"] if amount is None else amount
    hpid = f"hp-{pay['id']}"
    return client.post("/api/payments/hamyon/complete", data={
        "payment_id": hpid, "order_id": pay["id"], "shop_id": SHOP_ID, "amount": str(amount),
        "status": status, "paid_at": "1767225431", "reason": "timeout",
        "sign": sign or _sign(hpid, amount),
    })


def _user(db, uid="u1"):
    return asyncio.run(db.users.find_one({"id": uid}))


def _pay(db, pid):
    return asyncio.run(db.payments.find_one({"id": pid}))


def test_premium_purchase_is_delivered_once(env):
    client, db, calls = env
    r = client.post("/api/payments/create", json={"purpose": "premium", "months": 1})
    assert r.status_code == 200, r.text
    pay = r.json()
    assert pay["method"] == "hamyon" and pay["card"] and pay["pay_amount"] == core.PLAN_PRICES["premium"][1]
    assert _pay(db, pay["id"])["status"] == "pending"

    # A forged callback changes nothing.
    assert _complete(client, pay, sign="0" * 32).status_code == 403
    assert _user(db)["plan"] == "free"

    assert _complete(client, pay).json() == {"result": "ok"}
    assert _user(db)["plan"] == "premium" and _pay(db, pay["id"])["status"] == "success"
    # Hamyon repeats complete until it gets 2xx - never deliver twice.
    _complete(client, pay)
    assert calls["deliver"] == 1


def test_wrong_amount_is_not_delivered(env):
    client, db, calls = env
    pay = client.post("/api/payments/create", json={"purpose": "premium"}).json()
    _complete(client, pay, amount=1000)
    assert _user(db)["plan"] == "free" and calls["deliver"] == 0


def test_busy_amount_moves_up_by_one_som(env):
    client, db, calls = env
    first = client.post("/api/payments/create", json={"purpose": "balance_topup", "amount": 50000}).json()
    second = client.post("/api/payments/create", json={"purpose": "balance_topup", "amount": 50000}).json()
    assert first["pay_amount"] == 50000 and second["pay_amount"] == 50001
    # A top-up credits what was really transferred.
    _complete(client, second)
    assert _user(db)["balance"] == 50001


def test_cancel_refunds_balance_once_and_late_payment_still_counts(env):
    client, db, calls = env
    asyncio.run(db.users.update_one({"id": "u1"}, {"$set": {"balance": 30000}}))
    pay = client.post("/api/payments/create", json={"purpose": "premium"}).json()
    assert pay["balance_used"] == 30000 and pay["pay_amount"] == core.PLAN_PRICES["premium"][1] - 30000
    assert _user(db)["balance"] == 0

    _complete(client, pay, status="cancel")
    _complete(client, pay, status="cancel")
    assert _pay(db, pay["id"])["status"] == "cancelled" and _user(db)["balance"] == 30000

    # The money arrived after all: deliver, and take the refunded part again.
    _complete(client, pay)
    assert _user(db)["plan"] == "premium" and _user(db)["balance"] == 0


def test_status_check_settles_a_lost_callback(env):
    client, db, calls = env
    pay = client.post("/api/payments/create", json={"purpose": "premium"}).json()
    assert client.get(f"/api/payments/status/{pay['id']}").json()["status"] == "pending"
    calls["status"], calls["status_amount"] = "paid", pay["pay_amount"]
    asyncio.run(db.payments.update_one({"id": pay["id"]}, {"$unset": {"hamyon_checked_at": ""}}))
    assert client.get(f"/api/payments/status/{pay['id']}").json()["status"] == "success"
    assert _user(db)["plan"] == "premium"


def test_user_cancel_closes_at_hamyon(env):
    client, db, calls = env
    pay = client.post("/api/payments/create", json={"purpose": "premium"}).json()
    assert client.post(f"/api/payments/cancel/{pay['id']}").json()["status"] == "cancelled"
    assert calls["cancel"] == [f"hp-{pay['id']}"]


def test_provider_error_refunds_and_reports(env, monkeypatch):
    client, db, calls = env
    asyncio.run(db.users.update_one({"id": "u1"}, {"$set": {"balance": 10000}}))

    async def broken(*a, **kw):
        raise hamyon.HamyonError("Do'kon topilmadi!")

    monkeypatch.setattr(payments_r, "create_hamyon_payment", broken)
    r = client.post("/api/payments/create", json={"purpose": "premium"})
    assert r.status_code == 502 and r.json()["detail"] == "payment_provider_error"
    assert _user(db)["balance"] == 10000


def test_topup_config_reports_hamyon(env):
    client, db, calls = env
    cfg = client.get("/api/payments/topup-config").json()
    assert cfg["hamyon_enabled"] is True and cfg["payments_available"] is True
    assert cfg["p2p_enabled"] is False


def test_sign_check_and_amount_bump(monkeypatch):
    monkeypatch.setattr(hamyon, "HAMYON_SHOP_ID", SHOP_ID)
    monkeypatch.setattr(hamyon, "HAMYON_SHOP_KEY", SHOP_KEY)
    form = {"shop_id": SHOP_ID, "payment_id": "p1", "amount": "50000", "sign": _sign("p1", "50000")}
    assert hamyon.verify_hamyon_sign(form)
    assert not hamyon.verify_hamyon_sign({**form, "amount": "50001"})
    assert not hamyon.verify_hamyon_sign({**form, "shop_id": "999"})

    tried = []

    async def fake_post(path, data):
        tried.append(data["amount"])
        if data["amount"] < 50002:
            raise hamyon.HamyonError("Bu summada ochiq to'lov mavjud, summani o'zgartiring")
        return {"payment_id": "x", "card": "8600", "amount": data["amount"]}

    monkeypatch.setattr(hamyon, "_post", fake_post)
    res = asyncio.run(hamyon.create_hamyon_payment("o1", 50000))
    assert res["amount"] == 50002 and tried == [50000, 50001, 50002]


def test_background_reconcile_settles_a_lost_callback(env):
    client, db, calls = env
    pay = client.post("/api/payments/create", json={"purpose": "premium"}).json()
    from datetime import timedelta
    old = core.iso(core.now_utc() - timedelta(minutes=5))
    asyncio.run(db.payments.update_one({"id": pay["id"]}, {"$set": {"created_at": old}}))
    calls["status"], calls["status_amount"] = "paid", pay["pay_amount"]
    assert asyncio.run(payments_r.reconcile_open_hamyon_payments()) == 1
    assert _user(db)["plan"] == "premium" and _pay(db, pay["id"])["status"] == "success"
    # nothing left to do on the next pass
    assert asyncio.run(payments_r.reconcile_open_hamyon_payments()) == 0


def test_premium_periods_by_days(env):
    client, db, calls = env
    cfg = client.get("/api/payments/topup-config").json()
    assert cfg["premium_periods"] == {"1": 9900, "15": 49900, "30": 79000}
    pay = client.post("/api/payments/create", json={"purpose": "premium", "days": 1}).json()
    assert pay["pay_amount"] == 9900
    _complete(client, pay)
    u = _user(db)
    left = core.parse_dt(u["plan_until"]) - core.now_utc()
    assert u["plan"] == "premium" and 0.9 < left.total_seconds() / 86400 <= 1.01
    pay15 = client.post("/api/payments/create", json={"purpose": "premium", "days": 15}).json()
    assert pay15["pay_amount"] == 49900
    _complete(client, pay15)
    left = core.parse_dt(_user(db)["plan_until"]) - core.now_utc()
    assert 15.9 < left.total_seconds() / 86400 <= 16.01   # 1 day left + 15 days


def test_referral_reward_for_a_young_inviter_once(env):
    client, db, calls = env
    from datetime import timedelta
    five_days = core.iso(core.now_utc() - timedelta(days=5))
    asyncio.run(db.users.insert_one({"id": "inv", "name": "I", "plan": "free", "referral_id": "INV1", "created_at": five_days, "onboarded": True}))
    asyncio.run(db.users.update_one({"id": "u1"}, {"$set": {"referred_by": "INV1"}}))
    pay = client.post("/api/payments/create", json={"purpose": "premium", "days": 1}).json()
    _complete(client, pay)
    inv = _user(db, "inv")
    assert inv["referral_earnings_pending"] == 4950          # 50% of 9,900
    assert _user(db)["first_paid_at"]
    # a renewal pays nothing more
    pay2 = client.post("/api/payments/create", json={"purpose": "premium", "days": 15}).json()
    _complete(client, pay2)
    assert _user(db, "inv")["referral_earnings_pending"] == 4950


def test_first_paid_is_marked_without_a_referrer(env):
    client, db, calls = env
    pay = client.post("/api/payments/create", json={"purpose": "premium", "days": 1}).json()
    _complete(client, pay)
    assert _user(db).get("first_paid_at")
