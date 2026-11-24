"""Account: deletion, email + password for Telegram people, password reset, dead tokens."""
from __future__ import annotations

import asyncio
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import account  # noqa: E402
import auth  # noqa: E402
import core  # noqa: E402
import mailer  # noqa: E402
from core import RateLimiter, iso, now_utc  # noqa: E402
from models import LoginRequest, RegisterRequest  # noqa: E402
from routers import auth_r  # noqa: E402


def run(c):
    return asyncio.run(c)


REQ = SimpleNamespace(client=SimpleNamespace(host="9.9.9.9"), headers={})


@pytest.fixture
def env(monkeypatch):
    db = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r):
        monkeypatch.setattr(mod, "db", db, raising=False)
    auth._ACCOUNT_CACHE.clear()
    for name in ("send_limiter", "code_try_limiter", "delete_limiter"):
        monkeypatch.setattr(account, name, RateLimiter(max_attempts=50, window_sec=60))
    monkeypatch.setattr(auth_r, "auth_limiter", RateLimiter(max_attempts=50, window_sec=60), raising=False)
    mails: list[tuple[str, str]] = []

    async def fake_send(to, subject, text):
        mails.append((to, text))
        return True

    monkeypatch.setattr(mailer, "configured", lambda: True)
    monkeypatch.setattr(mailer, "send_email", fake_send)
    db._mails = mails
    # storage binds its own db at import (a real Mongo); never let a test reach it
    import storage
    gone: list[str] = []

    async def fake_delete(path):
        gone.append(path)
        return True

    monkeypatch.setattr(storage, "delete_object", fake_delete)
    db._gone = gone
    yield db
    auth._ACCOUNT_CACHE.clear()


def code_of(db, to):
    for addr, text in reversed(db._mails):
        if addr == to:
            return re.search(r"\b(\d{6})\b", text).group(1)
    raise AssertionError("no mail for " + to)


def pw_hash(pw="Secret#2026"):
    return core.hash_pw(pw)


def tg_user(**kw):
    d = {"id": "tg1", "name": "Ali", "telegram_id": "777", "onboarded": True, "plan": "free",
         "created_at": iso(now_utc())}
    d.update(kw)
    return d


# ---------- password rules + register ----------
def test_register_needs_a_real_password_and_starts_unverified(env):
    for bad in ("1234567", "aaaaaaaaaaaa", ""):
        with pytest.raises(HTTPException) as e:
            run(auth_r.register(RegisterRequest(email="a@x.uz", password=bad, name="A"), REQ))
        assert e.value.detail == "weak_password"
    r = run(auth_r.register(RegisterRequest(email="a@x.uz", password="Parol#2026", name="A"), REQ))
    assert r.user["email_verified"] is False and r.user["has_password"] is True


# ---------- email + password for a Telegram account ----------
def test_telegram_person_attaches_email_and_can_then_sign_in(env):
    run(env.users.insert_one(tg_user()))
    run(account.email_start(account.EmailStart(email="Ali@X.uz"), REQ, uid="tg1"))
    code = code_of(env, "ali@x.uz")
    with pytest.raises(HTTPException) as e:                       # a Telegram person has no password yet
        run(account.email_confirm(account.EmailConfirm(code=code), REQ, uid="tg1"))
    assert e.value.detail == "weak_password"
    run(account.email_confirm(account.EmailConfirm(code=code, password="Yangi#Parol1"), REQ, uid="tg1"))
    u = run(env.users.find_one({"id": "tg1"}))
    assert u["email"] == "ali@x.uz" and u["email_verified"] is True and u["telegram_id"] == "777"
    login = run(auth_r.login(LoginRequest(email="ali@x.uz", password="Yangi#Parol1"), REQ))
    assert login.user_id == "tg1"                                 # the SAME account, not a second one
    with pytest.raises(HTTPException):                            # the code is single-use
        run(account.email_confirm(account.EmailConfirm(code=code, password="Yangi#Parol1"), REQ, uid="tg1"))


def test_wrong_codes_are_limited_and_an_address_cannot_be_stolen(env):
    run(env.users.insert_many([tg_user(), tg_user(id="other", telegram_id="888", email="busy@x.uz", password_hash=pw_hash())]))
    with pytest.raises(HTTPException) as e:
        run(account.email_start(account.EmailStart(email="busy@x.uz"), REQ, uid="tg1"))
    assert e.value.detail == "email_taken"
    run(account.email_start(account.EmailStart(email="me@x.uz"), REQ, uid="tg1"))
    good = code_of(env, "me@x.uz")
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(account.MAX_CODE_ATTEMPTS):
        with pytest.raises(HTTPException):
            run(account.email_confirm(account.EmailConfirm(code=wrong, password="Yangi#Parol1"), REQ, uid="tg1"))
    with pytest.raises(HTTPException) as e:                       # five misses burn the code
        run(account.email_confirm(account.EmailConfirm(code=good, password="Yangi#Parol1"), REQ, uid="tg1"))
    assert e.value.detail == "invalid_code"
    assert not run(env.users.find_one({"id": "tg1"})).get("email")


def test_without_a_mail_provider_it_says_so(env, monkeypatch):
    monkeypatch.setattr(mailer, "configured", lambda: False)
    run(env.users.insert_one(tg_user()))
    for call in (lambda: account.email_start(account.EmailStart(email="a@x.uz"), REQ, uid="tg1"),
                 lambda: account.password_forgot(account.ForgotRequest(email="a@x.uz"), REQ)):
        with pytest.raises(HTTPException) as e:
            run(call())
        assert e.value.status_code == 503 and e.value.detail == "email_unavailable"


# ---------- forgot password ----------
def test_forgot_password_resets_it_and_ends_old_sessions(env):
    run(env.users.insert_many([
        {"id": "u1", "email": "u1@x.uz", "password_hash": pw_hash("Eski#Parol1"), "onboarded": True},
        {"id": "adm", "email": "adm@x.uz", "password_hash": pw_hash(), "is_admin": True},
    ]))
    # unknown address: same answer, nothing sent
    assert run(account.password_forgot(account.ForgotRequest(email="nobody@x.uz"), REQ)) == {"ok": True}
    assert env._mails == []
    old_token = auth.create_token("u1")
    old = auth.decode_token(old_token)
    run(auth.check_account("u1", old["iat"]))                      # fine before the reset
    run(account.password_forgot(account.ForgotRequest(email="u1@x.uz"), REQ))
    code = code_of(env, "u1@x.uz")
    with pytest.raises(HTTPException):
        run(account.password_reset(account.ResetRequest(email="u1@x.uz", code=code, password="short"), REQ))
    import time
    time.sleep(1.1)                                                # the new token must be newer than the reset's second
    out = run(account.password_reset(account.ResetRequest(email="u1@x.uz", code=code, password="Yangi#Parol2"), REQ))
    assert out["user_id"] == "u1"
    with pytest.raises(HTTPException):                             # the old password is dead
        run(auth_r.login(LoginRequest(email="u1@x.uz", password="Eski#Parol1"), REQ))
    assert run(auth_r.login(LoginRequest(email="u1@x.uz", password="Yangi#Parol2"), REQ)).user_id == "u1"
    with pytest.raises(HTTPException) as e:                        # a session from before the reset is ended
        run(auth.check_account("u1", old["iat"]))
    assert e.value.status_code == 401
    run(auth.check_account("u1", auth.decode_token(out["token"])["iat"]))   # the fresh one works
    with pytest.raises(HTTPException):                             # single use
        run(account.password_reset(account.ResetRequest(email="u1@x.uz", code=code, password="Yangi#Parol3"), REQ))
    # an admin's password can't be reset by email
    run(account.password_forgot(account.ForgotRequest(email="adm@x.uz"), REQ))
    assert all(to != "adm@x.uz" for to, _ in env._mails)


# ---------- deleting ----------
def _seed_person(db):
    run(db.users.insert_many([
        tg_user(id="me", email="me@x.uz", password_hash=pw_hash(), referral_id="ME1", balance=500,
                referral_earnings_withdrawable=3000),
        tg_user(id="you", telegram_id="888", name="Vali"),
    ]))
    run(db.files.insert_many([
        {"id": "f1", "owner_id": "me", "storage_path": "a" * 24}, {"id": "f2", "owner_id": "you", "storage_path": "b" * 24},
    ]))
    run(db.messages.insert_many([
        {"id": "m1", "from_user_id": "me", "to_user_id": "you", "text": "salom", "chat_id": "c"},
        {"id": "m2", "from_user_id": "you", "to_user_id": "me", "text": "va alaykum", "chat_id": "c"},
        {"id": "m3", "from_user_id": "you", "to_user_id": "x", "text": "boshqa", "chat_id": "d"},
    ]))
    run(db.saved.insert_many([{"owner_id": "me", "target_id": "you"}, {"owner_id": "you", "target_id": "me"},
                              {"owner_id": "you", "target_id": "x"}]))
    run(db.verifications.insert_one({"id": "v1", "user_id": "me", "kind": "selfie", "proof_url": "/api/files/" + "a" * 24}))
    run(db.notifications.insert_many([{"user_id": "me", "text": "1"}, {"user_id": "you", "text": "2"}]))
    run(db.bot_starts.insert_one({"telegram_id": "777", "chat_id": 5}))
    run(db.payments.insert_one({"id": "p1", "user_id": "me", "amount": 79000, "status": "success"}))
    run(db.withdrawals.insert_one({"id": "w1", "user_id": "me", "status": "paid", "amount": 1000,
                                   "card_number": "8600123412341234", "holder_name": "ALI VALIYEV"}))
    run(db.manual_topups.insert_one({"id": "t1", "user_id": "me", "status": "approved", "amount": 5000, "proof_url": "/api/files/x"}))
    run(db.reports.insert_many([
        {"id": "r1", "reporter_id": "me", "target_id": "you", "details": "men yozdim"},
        {"id": "r2", "reporter_id": "you", "target_id": "me", "details": "u haqorat qildi"},
    ]))


def test_deleting_removes_the_person_and_what_they_left_but_keeps_ledgers_clean(env):
    gone = env._gone
    _seed_person(env)
    run(account.delete_account(account.DeleteRequest(confirm="delete", password="Secret#2026"), REQ, uid="me"))
    assert run(env.users.find_one({"id": "me"})) is None
    assert run(env.users.find_one({"id": "you"})) is not None                       # other people stay
    assert gone == ["a" * 24]                                                        # the stored bytes went, only theirs
    assert run(env.files.count_documents({"owner_id": "me"})) == 0
    assert run(env.files.count_documents({"owner_id": "you"})) == 1
    assert [m["id"] for m in run(env.messages.find({}).to_list(10))] == ["m3"]    # both sides of the chat are gone
    assert [s["owner_id"] for s in run(env.saved.find({}).to_list(10))] == ["you"]
    assert run(env.verifications.count_documents({})) == 0                          # the selfie record too
    assert [n["user_id"] for n in run(env.notifications.find({}).to_list(10))] == ["you"]
    assert run(env.bot_starts.count_documents({"telegram_id": "777"})) == 0          # the bot stops writing to them
    assert run(env.payments.count_documents({"user_id": "me"})) == 1                 # accounting stays
    w = run(env.withdrawals.find_one({"id": "w1"}))
    assert w["card_number"] == "************1234" and w["holder_name"] == ""
    assert run(env.manual_topups.find_one({"id": "t1"}))["proof_url"] == ""
    assert run(env.reports.count_documents({"reporter_id": "me"})) == 0              # what they filed goes
    assert run(env.reports.find_one({"id": "r2"}))["details"] == ""                  # what was filed about them stays, without text
    assert run(env.banned_identities.count_documents({})) == 0                       # not banned: nothing kept


def test_a_deleted_accounts_token_stops_working(env):
    _seed_person(env)
    token = auth.decode_token(auth.create_token("me"))
    run(auth.check_account("me", token["iat"]))
    run(account.delete_account(account.DeleteRequest(confirm="DELETE", password="Secret#2026"), REQ, uid="me"))
    with pytest.raises(HTTPException) as e:
        run(auth.check_account("me", token["iat"]))
    assert e.value.status_code == 401


def test_deleting_needs_the_word_and_the_password_and_no_money_in_flight(env):
    _seed_person(env)
    for req, code in ((account.DeleteRequest(confirm="", password="Secret#2026"), 400),
                      (account.DeleteRequest(confirm="DELETE", password="wrong"), 403),
                      (account.DeleteRequest(confirm="DELETE"), 403)):
        with pytest.raises(HTTPException) as e:
            run(account.delete_account(req, REQ, uid="me"))
        assert e.value.status_code == code
    run(env.withdrawals.insert_one({"id": "w2", "user_id": "me", "status": "pending", "amount": 2000, "card_number": "8600"}))
    with pytest.raises(HTTPException) as e:
        run(account.delete_account(account.DeleteRequest(confirm="DELETE", password="Secret#2026"), REQ, uid="me"))
    assert e.value.status_code == 409 and e.value.detail == "pending_money"
    info = run(account.delete_info(uid="me"))
    assert info["blockers"] == ["pending_withdrawal"] and info["balance"] == 500 and info["earnings"] == 3000
    assert run(env.users.find_one({"id": "me"})) is not None                         # nothing was deleted


def test_a_telegram_only_person_deletes_with_the_word_alone_and_an_admin_cannot(env):
    run(env.users.insert_many([tg_user(), tg_user(id="adm", telegram_id="1", is_admin=True)]))
    run(account.delete_account(account.DeleteRequest(confirm="DELETE"), REQ, uid="tg1"))
    assert run(env.users.find_one({"id": "tg1"})) is None
    with pytest.raises(HTTPException) as e:
        run(account.delete_account(account.DeleteRequest(confirm="DELETE"), REQ, uid="adm"))
    assert e.value.detail == "admin_account"


def test_deleting_does_not_lift_a_ban(env):
    run(env.users.insert_one(tg_user(blocked=True, email="bad@x.uz", password_hash=pw_hash())))
    run(account.delete_account(account.DeleteRequest(confirm="DELETE", password="Secret#2026"), REQ, uid="tg1"))
    stored = run(env.banned_identities.find({}).to_list(10))
    assert len(stored) == 2 and all("bad@x.uz" not in str(s) and "777" not in str(s) for s in stored)   # hashes only
    with pytest.raises(HTTPException) as e:
        run(auth_r.register(RegisterRequest(email="Bad@X.uz", password="Parol#2026"), REQ))
    assert e.value.status_code == 403
    assert run(account.is_banned("tg", "777")) is True and run(account.is_banned("tg", "999")) is False
