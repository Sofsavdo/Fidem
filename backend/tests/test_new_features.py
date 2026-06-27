"""New feature tests for FIDEM iteration 2 — upload, expiry, filters, broadcast, webhook, gifts, response time, block/report."""
from __future__ import annotations
import io
import os
import time
import uuid
import pathlib

import pytest
import requests
from motor.motor_asyncio import AsyncIOMotorClient
import asyncio

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
A_EMAIL = f"new+a_{RUN}@fidem.uz"
B_EMAIL = f"new+b_{RUN}@fidem.uz"
PW = "Test@1234"

# Tiny 1x1 PNG
PNG_1x1 = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xfc\xff"
    b"\xff?\x03\x00\x06\x05\x02\xfe\xd2\xed\xc5\x9b\x00\x00\x00\x00IEND\xaeB`\x82"
)


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def admin_token():
    r = requests.post(f"{API}/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert r.status_code == 200
    return r.json()["token"]


def _onboard(token, gender, age_year, region="Toshkent", height=175):
    payload = {
        "name": "T", "gender": gender, "birth_date": f"{age_year}-01-01",
        "country": "Uzbekistan", "region": region, "district": "X",
        "marital_status": "single", "has_children": False, "children_count": 0,
        "height_cm": height, "weight_kg": 70, "education": "Oliy",
        "profession": "Eng", "religion": "Islom", "looking_for": "Oila",
        "search_gender": "female" if gender == "male" else "male",
        "search_age_min": 18, "search_age_max": 60, "search_region": region,
        "bio": "hello",
    }
    r = requests.post(f"{API}/profile/onboard", json=payload, headers=_h(token))
    assert r.status_code == 200, r.text


@pytest.fixture(scope="module")
def user_a():
    r = requests.post(f"{API}/auth/register", json={"email": A_EMAIL, "password": PW, "name": "A"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "female", 1985)  # age ~41, female
    return d


@pytest.fixture(scope="module")
def user_b():
    r = requests.post(f"{API}/auth/register", json={"email": B_EMAIL, "password": PW, "name": "B"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "male", 2000)  # age ~26, male
    return d


# -------- File upload --------
class TestFileUpload:
    def test_upload_image_success(self, user_a):
        files = {"file": ("p.png", io.BytesIO(PNG_1x1), "image/png")}
        r = requests.post(f"{API}/files/upload", files=files, headers=_h(user_a["token"]))
        assert r.status_code == 200, r.text
        b = r.json()
        assert "path" in b and b["url"].startswith("/api/files/")
        # Serve with auth query
        url = f"{BASE_URL}{b['url']}?auth={user_a['token']}"
        r2 = requests.get(url)
        assert r2.status_code == 200
        assert r2.headers.get("content-type", "").startswith("image/")
        # Serve without auth → 401
        r3 = requests.get(f"{BASE_URL}{b['url']}")
        assert r3.status_code == 401
        # Patch profile with returned url
        r4 = requests.patch(f"{API}/profile", json={"photo_url": b["url"]}, headers=_h(user_a["token"]))
        assert r4.status_code == 200
        me = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        assert me["photo_url"] == b["url"]

    def test_upload_non_image_rejected(self, user_a):
        files = {"file": ("p.txt", io.BytesIO(b"hello"), "text/plain")}
        r = requests.post(f"{API}/files/upload", files=files, headers=_h(user_a["token"]))
        assert r.status_code == 400


# -------- Filters update + enforcement --------
class TestFilters:
    def test_set_and_get_filters(self, user_a):
        f = {"age_min": 40, "age_max": 60, "require_verified": False}
        r = requests.patch(f"{API}/profile/filters", json=f, headers=_h(user_a["token"]))
        assert r.status_code == 200
        me = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        assert me["message_filters"]["age_min"] == 40

    def test_filter_blocks_send(self, user_a, user_b):
        # B (age 26) tries to message A (filter age_min=40)
        r = requests.post(f"{API}/messages/send",
                         json={"to_user_id": user_a["user_id"], "text": "Hi", "is_super": False},
                         headers=_h(user_b["token"]))
        assert r.status_code == 403, r.text
        assert "filter" in r.text.lower()

    def test_super_bypasses_filter(self, user_a, user_b, admin_token):
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"add_balance": 50000}, headers=_h(admin_token))
        r = requests.post(f"{API}/messages/send",
                         json={"to_user_id": user_a["user_id"], "text": "Super!", "is_super": True},
                         headers=_h(user_b["token"]))
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "application"


# -------- Response time tracking --------
class TestResponseTime:
    def test_b_reply_updates_avg_response_min(self, user_a, user_b):
        # A replies to B (B sent super-app above). Wait a moment then send.
        time.sleep(2)
        r = requests.post(f"{API}/messages/send",
                         json={"to_user_id": user_b["user_id"], "text": "Reply!", "is_super": False},
                         headers=_h(user_a["token"]))
        assert r.status_code == 200, r.text
        # A's avg_response_min should be set
        me = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        assert me.get("avg_response_min") is not None
        # Also exposed via candidate detail when B queries A
        r2 = requests.get(f"{API}/candidates/{user_a['user_id']}", headers=_h(user_b["token"]))
        assert r2.status_code == 200
        assert r2.json().get("avg_response_min") is not None


# -------- Block & Report --------
class TestBlockReport:
    def test_block(self, user_a, user_b):
        r = requests.post(f"{API}/messages/block",
                         json={"user_id": user_b["user_id"]},
                         headers=_h(user_a["token"]))
        assert r.status_code == 200

    def test_report(self, user_a, user_b):
        r = requests.post(f"{API}/messages/report",
                         json={"user_id": user_b["user_id"], "reason": "spam"},
                         headers=_h(user_a["token"]))
        assert r.status_code == 200


# -------- Gifts (all kinds, balance check) --------
class TestGifts:
    @pytest.mark.parametrize("kind,price", [("rose", 50), ("box", 200), ("diamond", 500), ("crown", 1500)])
    def test_gift_kinds(self, user_b, admin_token, kind, price):
        # add exact balance
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"add_balance": price}, headers=_h(admin_token))
        # pick a female candidate
        cands = requests.get(f"{API}/candidates", headers=_h(user_b["token"])).json()
        assert len(cands) > 0
        target_id = cands[0]["id"]
        before = requests.get(f"{API}/auth/me", headers=_h(user_b["token"])).json()["balance"]
        r = requests.post(f"{API}/gifts/send",
                         json={"to_user_id": target_id, "gift_kind": kind},
                         headers=_h(user_b["token"]))
        assert r.status_code == 200, r.text
        after = requests.get(f"{API}/auth/me", headers=_h(user_b["token"])).json()["balance"]
        assert before - after == price

    def test_gift_insufficient(self, user_a):
        # A's balance should be 0 (no top-up). Try crown (1500).
        me = requests.get(f"{API}/auth/me", headers=_h(user_a["token"])).json()
        if me["balance"] >= 1500:
            pytest.skip("A has unexpected balance")
        cands = requests.get(f"{API}/candidates", headers=_h(user_a["token"])).json()
        # A is female, search_gender=male → cands are male
        target_id = cands[0]["id"] if cands else None
        if not target_id:
            pytest.skip("no candidates")
        r = requests.post(f"{API}/gifts/send",
                         json={"to_user_id": target_id, "gift_kind": "crown"},
                         headers=_h(user_a["token"]))
        assert r.status_code == 402


# -------- Telegram webhook security --------
class TestTelegramWebhook:
    def test_no_secret(self):
        r = requests.post(f"{API}/telegram/webhook", json={"message": {}})
        assert r.status_code == 403

    def test_wrong_secret(self):
        r = requests.post(f"{API}/telegram/webhook?secret=wrong", json={"message": {}})
        assert r.status_code == 403


# -------- Marketing broadcast (daily cap) --------
class TestBroadcast:
    def test_broadcast_daily_cap(self, admin_token):
        # First run
        r1 = requests.post(f"{API}/admin/notification/broadcast",
                          json={"text": "Promo1"}, headers=_h(admin_token))
        assert r1.status_code == 200, r1.text
        b1 = r1.json()
        assert "sent" in b1 and "skipped_daily_cap" in b1
        # Second
        r2 = requests.post(f"{API}/admin/notification/broadcast",
                          json={"text": "Promo2"}, headers=_h(admin_token))
        assert r2.status_code == 200
        # Third should hit cap → skipped > 0
        r3 = requests.post(f"{API}/admin/notification/broadcast",
                          json={"text": "Promo3"}, headers=_h(admin_token))
        assert r3.status_code == 200
        b3 = r3.json()
        assert b3["skipped_daily_cap"] > 0, f"third broadcast did not skip: {b3}"


# -------- Subscription expiry --------
class TestExpiry:
    def test_plan_auto_downgrade(self, user_b):
        # Directly mutate Mongo: set premium plan with past plan_until
        async def run():
            client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
            db = client[os.environ.get("DB_NAME", "fidem_database")]
            await db.users.update_one(
                {"id": user_b["user_id"]},
                {"$set": {"plan": "premium", "plan_until": "2020-01-01T00:00:00+00:00"}},
            )
            client.close()
        asyncio.run(run())
        # Now /auth/me should auto-downgrade
        me = requests.get(f"{API}/auth/me", headers=_h(user_b["token"])).json()
        assert me["plan"] == "free", f"expected downgrade, got {me['plan']}"
