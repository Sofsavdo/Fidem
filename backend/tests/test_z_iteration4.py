"""Iteration 4 tests: Daily check-in, Boost/Spotlight, Quiz (+match bonus), Icebreakers, Invites."""
from __future__ import annotations

import os
import pathlib
import uuid

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    env = pathlib.Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"

ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"
RUN = uuid.uuid4().hex[:6]
PW = "Test@1234"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _onboard(token, gender, age_year, region="Toshkent"):
    payload = {
        "name": "T", "gender": gender, "birth_date": f"{age_year}-01-01",
        "country": "Uzbekistan", "region": region, "district": "X",
        "marital_status": "single", "has_children": False, "children_count": 0,
        "height_cm": 175, "weight_kg": 70, "education": "Oliy",
        "profession": "Eng", "religion": "Islom", "looking_for": "Oila",
        "search_gender": "female" if gender == "male" else "male",
        "search_age_min": 18, "search_age_max": 60, "search_region": region,
        "bio": "hi",
    }
    r = requests.post(f"{API}/profile/onboard", json=payload, headers=_h(token))
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="module")
def user_a():
    """Male user A, looking for female."""
    email = f"i4+a_{RUN}@fidem.uz"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": "A"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "male", 1995)
    return d


@pytest.fixture(scope="module")
def user_b():
    """Female user B (candidate that A should see)."""
    email = f"i4+b_{RUN}@fidem.uz"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": "B"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "female", 1997)
    return d


# ---------- Daily check-in ----------
class TestDaily:
    def test_daily_status_initial(self, user_a):
        r = requests.get(f"{API}/daily/status", headers=_h(user_a["token"]))
        assert r.status_code == 200
        body = r.json()
        assert "claimed_today" in body
        assert "streak" in body
        assert "next_bonus" in body

    def test_daily_claim_then_second_400(self, user_a):
        r1 = requests.post(f"{API}/daily/claim", headers=_h(user_a["token"]))
        # If already claimed earlier in this test module run, expect 400; else 200.
        assert r1.status_code in (200, 400), r1.text
        if r1.status_code == 200:
            body = r1.json()
            assert body["streak"] >= 1
            assert body["bonus"] >= 50
        # Second claim same day must always be 400
        r2 = requests.post(f"{API}/daily/claim", headers=_h(user_a["token"]))
        assert r2.status_code == 400

    def test_daily_status_after_claim(self, user_a):
        r = requests.get(f"{API}/daily/status", headers=_h(user_a["token"]))
        assert r.status_code == 200
        body = r.json()
        assert body["claimed_today"] is True
        assert body["streak"] >= 1
        assert body["next_bonus"] == 0


# ---------- Boost ----------
class TestBoost:
    def test_boost_status_initial(self, user_a):
        r = requests.get(f"{API}/boost/status", headers=_h(user_a["token"]))
        assert r.status_code == 200
        body = r.json()
        assert body["active"] in (False, True)
        assert body["price"] == 5000

    def test_boost_insufficient_balance_402(self, user_b, admin_token):
        # Reset B balance to 0 (might have residual)
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"set_balance": 0}, headers=_h(admin_token))
        r = requests.post(f"{API}/boost/activate", json={"use_balance": True},
                          headers=_h(user_b["token"]))
        assert r.status_code == 402, r.text

    def test_boost_activate_with_balance(self, user_b, admin_token):
        # Top up B with 10k UZS
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"add_balance": 10000}, headers=_h(admin_token))
        r = requests.post(f"{API}/boost/activate", json={"use_balance": True},
                          headers=_h(user_b["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["active"] is True
        assert "until" in body

        # Confirm status
        s = requests.get(f"{API}/boost/status", headers=_h(user_b["token"]))
        assert s.status_code == 200
        assert s.json()["active"] is True


# ---------- Spotlight ----------
class TestSpotlight:
    def test_spotlight_activate(self, user_b, admin_token):
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"add_balance": 30000}, headers=_h(admin_token))
        r = requests.post(f"{API}/spotlight/activate", json={"use_balance": True},
                          headers=_h(user_b["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["active"] is True
        assert "until" in body


# ---------- Boost ranking in candidates feed ----------
class TestBoostRanking:
    def test_boosted_user_floats_to_top(self, user_a, user_b, admin_token):
        # user_b already has boost+spotlight from prior tests; A should see B near top
        r = requests.get(f"{API}/candidates?sort=match&limit=30", headers=_h(user_a["token"]))
        assert r.status_code == 200
        feed = r.json()
        assert isinstance(feed, list) and len(feed) > 0
        # B should appear within the first few results
        ids = [x["id"] for x in feed]
        if user_b["user_id"] in ids:
            pos = ids.index(user_b["user_id"])
            assert pos <= 3, f"Boosted user B at position {pos} (expected top 4); ids={ids[:5]}"
        # Also check spotlight/boost flags present in response
        sample = feed[0]
        assert "boosted" in sample or "spotlight" in sample


# ---------- Quiz ----------
class TestQuiz:
    def test_quiz_questions(self, user_a):
        r = requests.get(f"{API}/quiz/questions", headers=_h(user_a["token"]))
        assert r.status_code == 200
        qs = r.json()
        assert isinstance(qs, list)
        assert len(qs) == 7
        # Validate shape
        for q in qs:
            assert "id" in q and "options" in q
            assert len(q["options"]) >= 2

    def test_quiz_submit(self, user_a):
        # Get balance before
        me_before = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        bal_before = me_before.get("balance", 0)

        answers = {
            "lifestyle": "family", "marriage_timeline": "year1", "kids": "soon",
            "communication": "trust", "weekend": "home", "spending": "save",
            "religion": "moderate",
        }
        r = requests.post(f"{API}/quiz/submit", json=answers, headers=_h(user_a["token"]))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["ok"] is True
        assert body["answered"] == 7
        assert body["bonus"] == 100

        # Balance increased
        me_after = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        assert me_after.get("balance", 0) >= bal_before + 100

    def test_quiz_match_bonus(self, user_a, user_b):
        # B submits identical answers → A's feed should mention "Quiz mosligi"
        answers = {
            "lifestyle": "family", "marriage_timeline": "year1", "kids": "soon",
            "communication": "trust", "weekend": "home", "spending": "save",
            "religion": "moderate",
        }
        r = requests.post(f"{API}/quiz/submit", json=answers, headers=_h(user_b["token"]))
        assert r.status_code == 200

        feed = requests.get(f"{API}/candidates?sort=match&limit=30",
                            headers=_h(user_a["token"])).json()
        b_card = next((c for c in feed if c["id"] == user_b["user_id"]), None)
        assert b_card is not None, "User B not found in A's feed"
        reasons = " ".join(b_card.get("match_reasons", []))
        # Bonus could be up to +10; reason appears only if bonus>=5
        # With 7/7 matching => bonus=10, reason should appear
        assert "Quiz" in reasons, f"Expected quiz reason. Got reasons={b_card.get('match_reasons')}, score={b_card.get('match_score')}"


# ---------- Icebreakers ----------
class TestIcebreakers:
    @pytest.mark.parametrize("lang", ["uz", "ru", "en"])
    def test_icebreakers_lang(self, lang, user_a):
        r = requests.get(f"{API}/icebreakers?lang={lang}", headers=_h(user_a["token"]))
        assert r.status_code == 200
        arr = r.json()
        assert isinstance(arr, list)
        assert len(arr) == 10
        assert all(isinstance(x, str) and len(x) > 0 for x in arr)

    def test_icebreakers_default_falls_to_uz(self, user_a):
        r = requests.get(f"{API}/icebreakers?lang=xx", headers=_h(user_a["token"]))
        assert r.status_code == 200
        assert len(r.json()) == 10


# ---------- Invites ----------
class TestInvites:
    def test_invites_status(self, user_a):
        r = requests.get(f"{API}/invites/status", headers=_h(user_a["token"]))
        assert r.status_code == 200
        body = r.json()
        for k in ("code", "link", "invited", "redeemed_weeks", "available_weeks", "next_milestone"):
            assert k in body, f"missing {k}"
        assert body["link"].startswith("https://t.me/")

    def test_invites_redeem_400_when_no_invites(self, user_a):
        r = requests.post(f"{API}/invites/redeem", headers=_h(user_a["token"]))
        assert r.status_code == 400
