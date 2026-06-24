"""FIDEM backend integration tests via public URL."""
from __future__ import annotations
import os
import time
import uuid
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    # fallback read from frontend/.env
    import pathlib
    env = pathlib.Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"

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
    }
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


# ---------- Admin payment confirm (premium grant) ----------
def test_admin_confirm_payment(session, user_creds, admin_token):
    # create payment
    r = session.post(f"{API}/payments/create", json={"purpose": "premium"},
                     headers=_auth_header(user_creds["token"]))
    pid = r.json()["id"]
    r2 = session.post(f"{API}/payments/admin-confirm/{pid}", headers=_auth_header(admin_token))
    assert r2.status_code == 200
    me = session.get(f"{API}/auth/me", headers=_auth_header(user_creds["token"])).json()
    assert me["plan"] == "premium"
