"""Iteration 3 tests: WebSocket real-time, auth rate limit, broadcast dry_run."""
from __future__ import annotations
import asyncio
import json
import os
import pathlib
import uuid

import pytest
import requests
import websockets

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
if not BASE_URL:
    env = pathlib.Path("/app/frontend/.env").read_text()
    for line in env.splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            BASE_URL = line.split("=", 1)[1].strip()
BASE_URL = (BASE_URL or "").rstrip("/")
API = f"{BASE_URL}/api"
WS_BASE = BASE_URL.replace("https://", "wss://").replace("http://", "ws://")

ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"
RUN = uuid.uuid4().hex[:6]
PW = "Test@1234"


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _onboard(token, gender, age_year):
    payload = {
        "name": "T", "gender": gender, "birth_date": f"{age_year}-01-01",
        "country": "Uzbekistan", "region": "Toshkent", "district": "X",
        "marital_status": "single", "has_children": False, "children_count": 0,
        "height_cm": 175, "weight_kg": 70, "education": "Oliy",
        "profession": "Eng", "religion": "Islom", "looking_for": "Oila",
        "search_gender": "female" if gender == "male" else "male",
        "search_age_min": 18, "search_age_max": 60, "search_region": "Toshkent",
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
    email = f"i3+a_{RUN}@fidem.uz"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": "A"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "male", 1995)
    return d


@pytest.fixture(scope="module")
def user_b():
    email = f"i3+b_{RUN}@fidem.uz"
    r = requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": "B"})
    assert r.status_code == 200
    d = r.json()
    _onboard(d["token"], "female", 1997)
    return d


# ---------- WebSocket basic ----------
class TestWebSocketBasic:
    def test_ws_invalid_token_closes(self):
        async def run():
            try:
                async with websockets.connect(f"{WS_BASE}/api/ws?token=garbage", open_timeout=10) as ws:
                    # If accepted, server should immediately close with 4401
                    try:
                        await asyncio.wait_for(ws.recv(), timeout=3)
                    except Exception:
                        pass
                    return ws.close_code
            except websockets.exceptions.InvalidStatus as e:
                # Ingress may reject with HTTP error
                return e.response.status_code
            except websockets.exceptions.ConnectionClosed as e:
                return e.code
        code = asyncio.run(run())
        assert code in (4401, 1006, 1000, 403, 401), f"got {code}"

    def test_ws_connect_and_ping(self, user_a):
        async def run():
            async with websockets.connect(
                f"{WS_BASE}/api/ws?token={user_a['token']}", open_timeout=10
            ) as ws:
                hello = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
                assert hello.get("type") == "connected"
                assert hello.get("user_id") == user_a["user_id"]
                await ws.send("ping")
                pong = await asyncio.wait_for(ws.recv(), timeout=5)
                assert pong == "pong"
        asyncio.run(run())


# ---------- Real-time message broadcast ----------
class TestRealtimeMessage:
    def test_message_pushed_to_both(self, user_a, user_b):
        """B sends message to A; both A's and B's WS should receive 'message' event."""
        async def run():
            ws_a = await websockets.connect(f"{WS_BASE}/api/ws?token={user_a['token']}", open_timeout=10)
            ws_b = await websockets.connect(f"{WS_BASE}/api/ws?token={user_b['token']}", open_timeout=10)
            try:
                # Drain hello
                await asyncio.wait_for(ws_a.recv(), timeout=5)
                await asyncio.wait_for(ws_b.recv(), timeout=5)

                # B sends message to A (B is female, A is male — A's search_gender=female so OK)
                # Send REST call from another task to not block ws receive
                async def send():
                    await asyncio.sleep(0.5)
                    return requests.post(
                        f"{API}/messages/send",
                        json={"to_user_id": user_a["user_id"], "text": f"Hello RT {RUN}", "is_super": False},
                        headers=_h(user_b["token"]),
                    )

                send_task = asyncio.create_task(send())

                # Collect events from both sockets in parallel
                async def recv_msg(ws):
                    for _ in range(5):
                        raw = await asyncio.wait_for(ws.recv(), timeout=8)
                        try:
                            ev = json.loads(raw)
                        except Exception:
                            continue
                        if ev.get("type") == "message":
                            return ev
                    return None

                ev_a, ev_b, resp = await asyncio.gather(recv_msg(ws_a), recv_msg(ws_b), send_task)
                assert resp.status_code == 200, resp.text
                assert ev_a is not None, "A did not receive 'message' WS event"
                assert ev_b is not None, "B did not receive 'message' WS event (multi-tab)"
                assert ev_a["data"].get("text") == f"Hello RT {RUN}"
            finally:
                await ws_a.close()
                await ws_b.close()
        asyncio.run(run())


# ---------- Real-time gift ----------
class TestRealtimeGift:
    def test_gift_pushed_via_ws(self, user_a, user_b, admin_token):
        # Top up B
        requests.patch(f"{API}/admin/users/{user_b['user_id']}",
                       json={"add_balance": 100}, headers=_h(admin_token))

        async def run():
            ws_a = await websockets.connect(f"{WS_BASE}/api/ws?token={user_a['token']}", open_timeout=10)
            try:
                await asyncio.wait_for(ws_a.recv(), timeout=5)  # hello

                async def send():
                    await asyncio.sleep(0.5)
                    return requests.post(
                        f"{API}/gifts/send",
                        json={"to_user_id": user_a["user_id"], "gift_kind": "rose"},
                        headers=_h(user_b["token"]),
                    )

                send_task = asyncio.create_task(send())

                gift_ev = None
                for _ in range(8):
                    raw = await asyncio.wait_for(ws_a.recv(), timeout=8)
                    try:
                        ev = json.loads(raw)
                    except Exception:
                        continue
                    if ev.get("type") == "message" and ev.get("data", {}).get("kind") == "gift":
                        gift_ev = ev
                        break
                resp = await send_task
                assert resp.status_code == 200, resp.text
                assert gift_ev is not None, "Did not receive gift WS event"
            finally:
                await ws_a.close()
        asyncio.run(run())


# ---------- Auth rate limit ----------
class TestAuthRateLimit:
    def test_login_rate_limit(self):
        # 11 wrong-password attempts → 11th must be 429
        email = f"i3+rl_{RUN}@fidem.uz"
        requests.post(f"{API}/auth/register", json={"email": email, "password": PW, "name": "RL"})

        last = None
        for i in range(11):
            r = requests.post(f"{API}/auth/login",
                              json={"email": email, "password": "wrong-pw"})
            last = r
            if r.status_code == 429:
                break
        assert last is not None
        assert last.status_code == 429, f"expected 429 within 11 attempts, last={last.status_code}"


# ---------- Broadcast dry_run ----------
class TestBroadcastDryRun:
    def test_dry_run_does_not_send(self, admin_token):
        r = requests.post(f"{API}/admin/notification/broadcast",
                          json={"text": "DryRun-Promo", "dry_run": True},
                          headers=_h(admin_token))
        assert r.status_code == 200, r.text
        body = r.json()
        assert body.get("dry_run") is True
        assert isinstance(body.get("would_send"), int) and body["would_send"] >= 0
        # Real send keys should be absent
        assert "sent" not in body
