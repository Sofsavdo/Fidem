"""FIDEM backend integration tests via public URL."""
from __future__ import annotations
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback read from frontend/.env, if present
    import pathlib
    env_path = pathlib.Path(__file__).resolve().parents[2] / "frontend" / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"

if not BASE_URL:
    pytest.skip(
        "REACT_APP_BACKEND_URL not set — this suite hits a live deployed backend "
        "and needs a real URL to run against; skipping in environments without one.",
        allow_module_level=True,
    )

ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Unique suffix per run so re-runs don't collide
RUN = uuid.uuid4().hex[:6]
USER_EMAIL = f"test+e2e_{RUN}@fidem.uz"
USER_PASSWORD = "Test@1234"
TARGET_EMAIL = f"test+target_{RUN}@fidem.uz"


@pytest.fixture(scope="session")
def session():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


def _auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------- Health ----------
def test_health(session):
    r = session.get(f"{API}/")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"


# ---------- Auth: register + login + me ----------
@pytest.fixture(scope="session")
def user_creds(session):
    r = session.post(f"{API}/auth/register", json={
        "email": USER_EMAIL, "password": USER_PASSWORD, "name": "E2E User",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "token" in data and data.get("onboarded") is False
    return data


def test_login_user(session, user_creds):
    r = session.post(f"{API}/auth/login", json={"email": USER_EMAIL, "password": USER_PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user_creds["user_id"]


def test_login_invalid(session):
    r = session.post(f"{API}/auth/login", json={"email": USER_EMAIL, "password": "wrong"})
    assert r.status_code == 401


def test_me_pre_onboard(session, user_creds):
    r = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["onboarded"] is False
    assert body["email"] == USER_EMAIL


# ---------- Onboarding ----------
@pytest.fixture(scope="session")
def onboarded(session, user_creds):
    payload = {
        "name": "E2E User",
        "gender": "male",
        "birth_date": "1995-06-15",
        "country": "Uzbekistan",
        "region": "Toshkent",
        "district": "Yunusobod",
        "marital_status": "single",
        "has_children": False,
        "children_count": 0,
        "height_cm": 180,
        "weight_kg": 75,
        "education": "Oliy",
        "profession": "Engineer",
        "religion": "Islom",
        "looking_for": "Oila qurish",
        "search_gender": "female",
        "search_age_min": 20,
        "search_age_max": 35,
        "search_region": "Toshkent",
        "photo_url": "https://example.com/p.jpg",
        "bio": "Hello",
        "terms_accepted": True,
    }
    # First onboarding without consent must be refused (legal gate)
    no_consent = {**payload, "terms_accepted": False}
    r = session.post(f"{API}/profile/onboard", json=no_consent, headers=_auth_header(user_creds["token"]))
    assert r.status_code == 400 and r.json()["detail"] == "terms_required"
    r = session.post(f"{API}/profile/onboard", json=payload, headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert isinstance(body["completeness"], int) and body["completeness"] > 0
    return body


def test_me_post_onboard(session, user_creds, onboarded):
    r = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert r.json()["onboarded"] is True


def test_update_profile(session, user_creds, onboarded):
    r = session.patch(f"{API}/profile",
                      json={"bio": "Updated bio", "profession": "Senior Engineer"},
                      headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    me = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"])).json()
    assert me["bio"] == "Updated bio"


def test_update_language(session, user_creds, onboarded):
    for lang in ["ru", "en", "uz"]:
        r = session.patch(f"{API}/profile/language", json={"language": lang},
                          headers=_auth_header(user_creds["token"]))
        assert r.status_code == 200
    r2 = session.patch(f"{API}/profile/language", json={"language": "fr"},
                       headers=_auth_header(user_creds["token"]))
    assert r2.status_code == 400


# ---------- Candidates ----------
@pytest.fixture(scope="session")
def candidate_list(session, user_creds, onboarded):
    r = session.get(f"{API}/candidates", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    arr = r.json()
    assert isinstance(arr, list) and len(arr) >= 5  # seed has 8 female
    for c in arr[:3]:
        assert "match_score" in c and "match_reasons" in c
        assert c["gender"] == "female"
    return arr


def test_candidate_detail(session, user_creds, candidate_list):
    target = candidate_list[0]
    r = session.get(f"{API}/candidates/{target['id']}", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == target["id"]
    assert "match_score" in body


# ---------- Photo unlock ----------
def test_photo_unlock_request(session, user_creds, candidate_list):
    target = candidate_list[0]
    r = session.post(f"{API}/photo-unlock/request",
                     json={"target_user_id": target["id"]},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert r.json()["status"] in ("pending", "approved")


# ---------- Save flow ----------
def test_save_unsave(session, user_creds, candidate_list):
    target = candidate_list[1]
    r = session.post(f"{API}/saved", json={"user_id": target["id"]},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    r = session.get(f"{API}/saved/mine", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert any(s["id"] == target["id"] for s in r.json())
    # sub-lists work
    for path in ["by-others", "viewers", "interested"]:
        rr = session.get(f"{API}/saved/{path}", headers=_auth_header(user_creds["token"]))
        assert rr.status_code == 200
        assert isinstance(rr.json(), list)
    # delete
    r = session.delete(f"{API}/saved/{target['id']}", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200


# ---------- Messages / Applications ----------
def test_message_flow(session, user_creds, candidate_list):
    target = candidate_list[2]
    r = session.post(f"{API}/messages/send",
                     json={"to_user_id": target["id"], "text": "Salom!", "is_super": False},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200, r.text
    msg = r.json()
    assert msg["status"] == "application"
    chat_id = msg["chat_id"]
    # list chats
    r = session.get(f"{API}/messages/chats", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert any(c["chat_id"] == chat_id for c in r.json())
    # history
    r = session.get(f"{API}/messages/{chat_id}", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert len(r.json()) >= 1


# ---------- Verification ----------
def test_verification_request(session, user_creds):
    r = session.post(f"{API}/verification/request",
                     json={"kind": "selfie", "note": "please verify"},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert "id" in r.json()


# ---------- Payments ----------
def test_create_payment_premium(session, user_creds):
    r = session.post(f"{API}/payments/create", json={"purpose": "premium"},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending" and body["amount"] == 79000
    assert "payment_link" in body


def test_create_payment_topup(session, user_creds):
    r = session.post(f"{API}/payments/create",
                     json={"purpose": "balance_topup", "amount": 50000},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert r.json()["amount"] == 50000


def test_payment_topup_too_small(session, user_creds):
    r = session.post(f"{API}/payments/create",
                     json={"purpose": "balance_topup", "amount": 100},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 400


def test_click_callback_unknown_order(session):
    r = session.post(f"{API}/payments/click/callback",
                     data={"action": "0", "merchant_trans_id": "nonexistent-id"},
                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 200
    body = r.json()
    # CLICK callback returns error: -1 (sign failed) or -5 (order not found)
    assert body.get("error") in (-1, -5)


# ---------- Referral ----------
def test_referral(session, user_creds):
    r = session.get(f"{API}/referral/mine", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    body = r.json()
    assert "code" in body and "link" in body
    assert "t.me/" in body["link"]


# ---------- Notifications ----------
def test_notifications(session, user_creds):
    r = session.get(f"{API}/notifications", headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    r2 = session.post(f"{API}/notifications/read-all", headers=_auth_header(user_creds["token"]))
    assert r2.status_code == 200


# ---------- Admin ----------
@pytest.fixture(scope="session")
def admin_token(session):
    r = session.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["is_admin"] is True
    return body["token"]


def test_admin_stats(session, admin_token):
    r = session.get(f"{API}/admin/stats", headers=_auth_header(admin_token))
    assert r.status_code == 200
    body = r.json()
    assert "total_users" in body and body["total_users"] >= 10


def test_admin_users_search(session, admin_token):
    r = session.get(f"{API}/admin/users?q=Madina", headers=_auth_header(admin_token))
    assert r.status_code == 200
    arr = r.json()
    assert any("Madina" in u.get("name", "") for u in arr)


def test_admin_add_balance(session, admin_token, user_creds):
    r = session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                      json={"add_balance": 10000},
                      headers=_auth_header(admin_token))
    assert r.status_code == 200
    # verify
    me = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"])).json()
    assert me["balance"] >= 10000


def test_admin_payments_list(session, admin_token):
    r = session.get(f"{API}/admin/payments", headers=_auth_header(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_verifications_list(session, admin_token):
    r = session.get(f"{API}/admin/verifications", headers=_auth_header(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


# ---------- Gift flow (after balance topup) ----------
def test_gift_send(session, user_creds, admin_token, candidate_list):
    # ensure balance
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"add_balance": 1000}, headers=_auth_header(admin_token))
    target = candidate_list[0]
    r = session.post(f"{API}/gifts/send",
                     json={"to_user_id": target["id"], "gift_kind": "rose"},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200, r.text
    assert "balance" in r.json()


# ---------- Leaderboard ----------
def test_leaderboard(session):
    for p in ["all", "day", "week", "month"]:
        r = session.get(f"{API}/leaderboard?period={p}")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------- Payments auto-confirm (no admin approval) ----------
def test_balance_funded_payment_auto_completes(session, user_creds, admin_token):
    """A payment fully covered by balance completes instantly - no admin
    confirmation step. (CLICK payments are likewise auto-confirmed by the
    CLICK callback; admin only approves referral WITHDRAWALS.)"""
    # Fund the balance so the premium plan is fully covered.
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"add_balance": 200000}, headers=_auth_header(admin_token))
    r = session.post(f"{API}/payments/create", json={"purpose": "premium"},
                     headers=_auth_header(user_creds["token"]))
    assert r.status_code == 200
    assert r.json()["status"] == "paid"  # completed immediately, not "pending"
    me = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"])).json()
    assert me["plan"] == "premium"


def test_no_admin_confirm_payment_endpoint(session, admin_token):
    """The admin-confirm-payment endpoint was removed on purpose - admins do
    not confirm CLICK payments or top-ups."""
    r = session.post(f"{API}/payments/admin-confirm/anything", headers=_auth_header(admin_token))
    assert r.status_code == 404


# ---------- Privacy: open photo / hidden profile / boost conflict ----------
def test_privacy_settings_roundtrip(session, user_creds):
    tok = user_creds["token"]
    r = session.post(f"{API}/settings/privacy", json={"photo_public": True},
                     headers=_auth_header(tok))
    assert r.status_code == 200 and r.json()["photo_public"] is True
    r = session.get(f"{API}/settings/privacy", headers=_auth_header(tok))
    assert r.status_code == 200 and r.json()["photo_public"] is True
    # /auth/me carries the flags so the frontend toggles render from `user`
    me = session.get(f"{API}/auth/me", headers=_auth_header(tok)).json()
    assert me.get("photo_public") is True
    assert me.get("hidden_profile") is False
    # partial update: flipping one flag must not touch the other
    r = session.post(f"{API}/settings/privacy", json={"photo_public": False},
                     headers=_auth_header(tok))
    assert r.json()["photo_public"] is False and r.json()["hidden_profile"] is False


def test_privacy_hidden_requires_paid_plan(session, user_creds, admin_token):
    """Hidden mode is a paid feature: free plan gets a 403 upsell, any paid
    plan can enable it."""
    tok = user_creds["token"]
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"plan": "free"}, headers=_auth_header(admin_token))
    r = session.post(f"{API}/settings/privacy", json={"hidden_profile": True},
                     headers=_auth_header(tok))
    assert r.status_code == 403 and r.json()["detail"] == "privacy_requires_plan"
    # photo_public stays free
    r = session.post(f"{API}/settings/privacy", json={"photo_public": True},
                     headers=_auth_header(tok))
    assert r.status_code == 200
    session.post(f"{API}/settings/privacy", json={"photo_public": False},
                 headers=_auth_header(tok))
    # smallest paid tier unlocks it
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"plan": "standard"}, headers=_auth_header(admin_token))
    r = session.post(f"{API}/settings/privacy", json={"hidden_profile": True},
                     headers=_auth_header(tok))
    assert r.status_code == 200 and r.json()["hidden_profile"] is True
    session.post(f"{API}/settings/privacy", json={"hidden_profile": False},
                 headers=_auth_header(tok))


def test_vip_photo_peek_gated(session, user_creds, admin_token):
    """/photo-peek requires vip plan AND hidden mode on."""
    tok = user_creds["token"]
    # standard plan, hidden off -> refused
    r = session.post(f"{API}/photo-peek/some-user-id", headers=_auth_header(tok))
    assert r.status_code == 403 and r.json()["detail"] == "peek_requires_vip"


def test_hidden_profile_blocks_boost(session, user_creds, admin_token):
    """Boost sells visibility; a hidden profile has none - both boost paths
    must refuse instead of taking money."""
    tok = user_creds["token"]
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"plan": "standard"}, headers=_auth_header(admin_token))
    r = session.post(f"{API}/settings/privacy", json={"hidden_profile": True},
                     headers=_auth_header(tok))
    assert r.status_code == 200 and r.json()["hidden_profile"] is True

    r = session.post(f"{API}/boost/activate", json={"use_balance": True},
                     headers=_auth_header(tok))
    assert r.status_code == 400 and r.json()["detail"] == "boost_hidden"

    r = session.post(f"{API}/payments/create", json={"purpose": "boost"},
                     headers=_auth_header(tok))
    assert r.status_code == 400 and r.json()["detail"] == "boost_hidden"

    r = session.post(f"{API}/settings/privacy", json={"hidden_profile": False},
                     headers=_auth_header(tok))
    assert r.status_code == 200 and r.json()["hidden_profile"] is False


def test_boost_active_blocks_hiding(session, user_creds, admin_token):
    """The mirror rule: while a paid boost is running, hiding the profile is
    refused (it would waste the boost the user just paid for)."""
    tok = user_creds["token"]
    session.patch(f"{API}/admin/users/{user_creds['user_id']}",
                  json={"add_balance": 10000, "plan": "standard"}, headers=_auth_header(admin_token))
    r = session.post(f"{API}/boost/activate", json={"use_balance": True},
                     headers=_auth_header(tok))
    assert r.status_code == 200, r.text

    r = session.post(f"{API}/settings/privacy", json={"hidden_profile": True},
                     headers=_auth_header(tok))
    assert r.status_code == 400 and r.json()["detail"] == "privacy_boost_active"
    # photo_public alone stays allowed while boosted
    r = session.post(f"{API}/settings/privacy", json={"photo_public": False},
                     headers=_auth_header(tok))
    assert r.status_code == 200
