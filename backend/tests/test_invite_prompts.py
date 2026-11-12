"""Invite-a-friend: the Premium-day bonus and the anti-spam rules for its prompt."""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "test_db")
os.environ.setdefault("JWT_SECRET", "test-secret-for-local-testing")

mongomock_motor = pytest.importorskip("mongomock_motor")

import core  # noqa: E402
import invite_prompts as ip  # noqa: E402
import lifecycle  # noqa: E402
from core import iso, now_utc  # noqa: E402


def run(c):
    return asyncio.run(c)


@pytest.fixture
def db(monkeypatch):
    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, lifecycle):
        monkeypatch.setattr(mod, "db", database, raising=False)
    sent = []

    async def fake_push(uid, kind, text, link=None, marketing=False, payload=None):
        sent.append((uid, kind, text, link, marketing))
        return True

    monkeypatch.setattr(core, "push_notif", fake_push)
    monkeypatch.setattr(lifecycle, "push_notif", fake_push)
    database._sent = sent
    return database


def _user(**kw):
    d = {"id": "u1", "onboarded": True, "created_at": iso(now_utc() - timedelta(days=10)),
         "last_active": iso(now_utc())}
    d.update(kw)
    return d


# ---------- the bonus ----------
def test_friend_bonus_adds_premium_days_up_to_a_cap(db):
    run(db.users.insert_one(_user()))
    assert run(ip.grant_friend_bonus("u1")) == ("premium", ip.BONUS_DAYS_PER_FRIEND)
    u = run(db.users.find_one({"id": "u1"}))
    assert u["plan"] == "premium" and u["invite_bonus_days"] == ip.BONUS_DAYS_PER_FRIEND
    for _ in range(20):
        run(ip.grant_friend_bonus("u1"))
    assert run(db.users.find_one({"id": "u1"}))["invite_bonus_days"] == ip.BONUS_DAYS_CAP
    assert run(ip.grant_friend_bonus("u1")) == ("premium", 0)


def test_bonus_extends_an_active_plan_instead_of_replacing_it(db):
    until = now_utc() + timedelta(days=20)
    run(db.users.insert_one(_user(plan="vip", plan_until=iso(until))))
    run(ip.grant_friend_bonus("u1"))
    u = run(db.users.find_one({"id": "u1"}))
    assert u["plan"] == "vip"
    assert core.parse_dt(u["plan_until"]) == until + timedelta(days=ip.BONUS_DAYS_PER_FRIEND)


def test_lapsed_plan_restarts_as_premium_from_now(db):
    run(db.users.insert_one(_user(plan="premium", plan_until=iso(now_utc() - timedelta(days=5)))))
    run(ip.grant_friend_bonus("u1"))
    u = run(db.users.find_one({"id": "u1"}))
    assert core.parse_dt(u["plan_until"]) > now_utc()


# ---------- the prompt: never spams ----------
def test_prompt_is_sent_once_then_waits_two_weeks(db):
    run(db.users.insert_one(_user()))
    assert run(ip.maybe_prompt("u1", "match")) is True
    assert run(ip.maybe_prompt("u1", "match")) is False            # same day
    run(db.users.update_one({"id": "u1"}, {"$set": {"invite_prompt_at": iso(now_utc() - timedelta(days=15))}}))
    assert run(ip.maybe_prompt("u1", "match")) is True              # a fortnight later
    assert len(db._sent) == 2
    uid, kind, text, link, marketing = db._sent[0]
    assert kind == "referral" and link == "/referral" and marketing is True
    assert f"+{ip.BONUS_DAYS_PER_FRIEND} kun Premium" in text


def test_prompt_stops_for_good_after_three(db):
    run(db.users.insert_one(_user()))
    for _ in range(6):
        run(db.users.update_one({"id": "u1"}, {"$set": {"invite_prompt_at": iso(now_utc() - timedelta(days=30))}}))
        run(ip.maybe_prompt("u1", "lifecycle"))
    assert len(db._sent) == ip.MAX_PROMPTS


def test_old_awareness_push_counts_as_a_recent_prompt(db):
    run(db.users.insert_one(_user(referral_awareness_sent_at=iso(now_utc() - timedelta(days=2)))))
    assert run(ip.maybe_prompt("u1", "match")) is False


def test_prompt_skips_people_it_does_not_fit(db):
    run(db.users.insert_many([
        _user(id="guest", onboarded=False),
        _user(id="bot", is_ai=True),
        _user(id="banned", blocked=True),
        _user(id="already", referral_earnings=[{"id": "e1"}]),            # already invites friends
        _user(id="capped", invite_bonus_days=ip.BONUS_DAYS_CAP),         # nothing left to offer
    ]))
    for uid in ("guest", "bot", "banned", "already", "capped", "nobody"):
        assert run(ip.maybe_prompt(uid, "lifecycle")) is False
    assert db._sent == []


def test_a_capped_push_gives_the_slot_back(db, monkeypatch):
    async def capped(*a, **k):
        return False

    monkeypatch.setattr(core, "push_notif", capped)
    run(db.users.insert_one(_user()))
    assert run(ip.maybe_prompt("u1", "match")) is False
    u = run(db.users.find_one({"id": "u1"}))
    assert not u.get("invite_prompt_at") and u["invite_prompt_count"] == 0


# ---------- the timed push ----------
def _at_hour(monkeypatch, local_hour):
    fixed = now_utc().replace(hour=(local_hour - 5) % 24, minute=0)
    monkeypatch.setattr(lifecycle, "now_utc", lambda: fixed)


def test_timed_push_only_in_daytime_and_only_for_active_people(db, monkeypatch):
    monkeypatch.setattr(lifecycle, "SEND_PACING_SECONDS", 0)
    run(db.users.insert_many([
        _user(id="active"),
        _user(id="new", created_at=iso(now_utc() - timedelta(hours=5))),
        _user(id="gone", last_active=iso(now_utc() - timedelta(days=60))),
    ]))
    _at_hour(monkeypatch, 3)                                         # 3 am in Tashkent
    run(lifecycle._referral_awareness_nudge())
    assert db._sent == []
    _at_hour(monkeypatch, 14)
    run(lifecycle._referral_awareness_nudge())
    assert [s[0] for s in db._sent] == ["active"]
    run(lifecycle._referral_awareness_nudge())                       # next pass: nothing again
    assert len(db._sent) == 1


def test_a_match_prompts_both_people_after_a_delay(db):
    run(db.users.insert_many([_user(id="a"), _user(id="b")]))

    async def go():
        ip.prompt_after_match("a", "b", delay=0.01)
        await asyncio.sleep(0.2)

    run(go())
    assert sorted(s[0] for s in db._sent) == ["a", "b"]


# ---------- the real onboarding path ----------
def test_friend_finishing_the_profile_pays_the_inviter(monkeypatch):
    import ai_service
    from models import OnboardingProfile
    from routers import auth_r

    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    pushed = []

    async def fake_push(uid, kind, text, link=None, **k):
        pushed.append((uid, text))
        return True

    async def ok(image_url="", image_base64=""):
        return {"valid": True, "code": "ok"}

    async def nothing(*a, **k):
        return None

    monkeypatch.setattr(auth_r, "push_notif", fake_push)
    monkeypatch.setattr(ai_service, "verify_face_photo", ok)
    monkeypatch.setattr(auth_r, "notify_new_profile_to_relevant_users", nothing)

    async def go():
        week_ago = iso(now_utc() - timedelta(days=7))
        await database.users.insert_one({"id": "inv", "name": "I", "plan": "free", "referral_id": "INV1",
                                         "created_at": week_ago, "onboarded": True})
        await database.users.insert_one({"id": "n1", "onboarded": False, "plan": "free", "balance": 0,
                                         "referred_by": "INV1", "created_at": iso(now_utc())})
        await database.files.insert_one({"storage_path": "b" * 24, "owner_id": "n1", "is_deleted": False})
        req = OnboardingProfile(
            gender="female", birth_date="1998-03-04", country="Uzbekistan", region="Toshkent", marital_status="single",
            has_children=False, search_gender="male", search_age_min=20, search_age_max=36, name="Madina",
            photo_url="http://h/api/files/" + "b" * 24, terms_accepted=True,
        )
        await auth_r.onboard(req, uid="n1")
        inv = await database.users.find_one({"id": "inv"})
        assert inv["plan"] == "premium" and inv["invite_bonus_days"] == ip.BONUS_DAYS_PER_FRIEND
        assert inv["balance"] == 100
        assert any(u == "inv" and f"+{ip.BONUS_DAYS_PER_FRIEND} kun Premium" in t for u, t in pushed)
        # the same friend can never pay twice
        await auth_r.onboard(req, uid="n1")
        assert (await database.users.find_one({"id": "inv"}))["invite_bonus_days"] == ip.BONUS_DAYS_PER_FRIEND

    run(go())


# ---------- women: Boost instead of Premium days ----------
def _woman(**kw):
    return _user(id="w1", gender="female", verified_selfie=True, **kw)


def test_woman_is_paid_in_boost_not_premium_days(db):
    run(db.users.insert_one(_woman()))
    assert run(ip.grant_friend_bonus("w1")) == ("boost", ip.BOOST_DAYS_PER_FRIEND)
    u = run(db.users.find_one({"id": "w1"}))
    assert core.parse_dt(u["boost_until"]) > now_utc() + timedelta(days=ip.BOOST_DAYS_PER_FRIEND - 1)
    assert u["invite_boost_days"] == ip.BOOST_DAYS_PER_FRIEND
    assert not u.get("plan_until") and not u.get("invite_bonus_days")      # Premium untouched


def test_boost_days_add_to_a_running_boost_and_stop_at_the_cap(db):
    until = now_utc() + timedelta(days=5)
    run(db.users.insert_one(_woman(boost_until=iso(until))))
    run(ip.grant_friend_bonus("w1"))
    u = run(db.users.find_one({"id": "w1"}))
    assert core.parse_dt(u["boost_until"]) == until + timedelta(days=ip.BOOST_DAYS_PER_FRIEND)
    for _ in range(20):
        run(ip.grant_friend_bonus("w1"))
    assert run(db.users.find_one({"id": "w1"}))["invite_boost_days"] == ip.BOOST_DAYS_CAP
    assert run(ip.grant_friend_bonus("w1")) == ("boost", 0)


def test_boost_goes_only_to_verified_women_with_a_visible_profile(db):
    run(db.users.insert_many([
        _user(id="unverified", gender="female"),
        _user(id="hidden", gender="female", verified_selfie=True, hidden_profile=True),
    ]))
    assert run(ip.grant_friend_bonus("unverified")) == ("boost", 0)
    assert run(ip.grant_friend_bonus("hidden")) == ("boost", 0)
    assert not run(db.users.find_one({"id": "unverified"})).get("boost_until")


def test_womens_prompt_offers_boost_and_skips_those_who_cannot_get_it(db):
    run(db.users.insert_many([_woman(), _user(id="unverified", gender="female")]))
    assert run(ip.maybe_prompt("w1", "match")) is True
    assert run(ip.maybe_prompt("unverified", "match")) is False
    text = db._sent[0][2]
    assert "Boost" in text and "Premium" not in text.split("Boost")[0]
    assert f"+{ip.BOOST_DAYS_PER_FRIEND} kun" in text


def test_woman_inviter_gets_boost_through_the_real_onboarding(monkeypatch):
    import ai_service
    from models import OnboardingProfile
    from routers import auth_r

    database = mongomock_motor.AsyncMongoMockClient()["t"]
    for mod in (core, auth_r):
        monkeypatch.setattr(mod, "db", database, raising=False)
    pushed = []

    async def fake_push(uid, kind, text, link=None, **k):
        pushed.append((uid, text))
        return True

    async def ok(image_url="", image_base64=""):
        return {"valid": True, "code": "ok"}

    async def nothing(*a, **k):
        return None

    monkeypatch.setattr(auth_r, "push_notif", fake_push)
    monkeypatch.setattr(ai_service, "verify_face_photo", ok)
    monkeypatch.setattr(auth_r, "notify_new_profile_to_relevant_users", nothing)

    async def go():
        await database.users.insert_one({"id": "inv", "name": "I", "gender": "female", "verified_selfie": True,
                                         "plan": "free", "referral_id": "INV1", "onboarded": True,
                                         "created_at": iso(now_utc() - timedelta(days=7))})
        await database.users.insert_one({"id": "n1", "onboarded": False, "plan": "free", "balance": 0,
                                         "referred_by": "INV1", "created_at": iso(now_utc())})
        await database.files.insert_one({"storage_path": "b" * 24, "owner_id": "n1", "is_deleted": False})
        await auth_r.onboard(OnboardingProfile(
            gender="male", birth_date="1996-03-04", country="Uzbekistan", region="Toshkent", marital_status="single",
            has_children=False, search_gender="female", search_age_min=20, search_age_max=36, name="Ali",
            photo_url="http://h/api/files/" + "b" * 24, terms_accepted=True), uid="n1")
        inv = await database.users.find_one({"id": "inv"})
        assert inv["invite_boost_days"] == ip.BOOST_DAYS_PER_FRIEND and core.parse_dt(inv["boost_until"]) > now_utc()
        assert inv["plan"] == "free" and inv["balance"] == 100
        assert any(u == "inv" and f"+{ip.BOOST_DAYS_PER_FRIEND} kun Boost" in t for u, t in pushed)

    run(go())
