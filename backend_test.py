#!/usr/bin/env python3
"""
Backend API test suite for FIDEM matchmaking app - NEW FEATURES
Tests: Big5 personality, Chaperone/Wali, Roses, AI Icebreakers, AI Moderation
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime

import httpx

# Base URL from frontend/.env
BASE_URL = "https://clone-preview-32.preview.emergentagent.com/api"
TIMEOUT = 20.0  # AI endpoints may take longer

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Global state
admin_token = None
admin_id = None
new_user_token = None
new_user_id = None
wali_token = None
wali_id = None
candidate_id = None


def log(msg: str):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def log_pass(test_name: str):
    print(f"✅ {test_name}")


def log_fail(test_name: str, reason: str):
    print(f"❌ {test_name}: {reason}")


async def test_admin_login():
    """Login as admin to get token"""
    global admin_token, admin_id
    log("Testing admin login...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
        )
        if resp.status_code != 200:
            log_fail("Admin login", f"Status {resp.status_code}: {resp.text}")
            sys.exit(1)
        data = resp.json()
        admin_token = data.get("token")
        admin_id = data.get("user_id")
        if not admin_token or not admin_id:
            log_fail("Admin login", "Missing token or user id")
            sys.exit(1)
        log_pass(f"Admin login (id={admin_id})")


async def test_get_candidate():
    """Get a candidate for testing"""
    global candidate_id
    log("Getting candidate list...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/candidates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Get candidates", f"Status {resp.status_code}")
            return
        data = resp.json()
        if not data:
            log_fail("Get candidates", "No candidates found")
            return
        # Find Madina or use first candidate
        for c in data:
            if "madina" in c.get("name", "").lower():
                candidate_id = c.get("id")
                break
        if not candidate_id and data:
            candidate_id = data[0].get("id")
        log_pass(f"Got candidate (id={candidate_id})")


# ============================================================================
# 1. BIG 5 / OCEAN PERSONALITY TEST
# ============================================================================

async def test_personality_questions_uz():
    """GET /api/personality/questions?lang=uz"""
    log("Testing personality questions (uz)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/personality/questions?lang=uz")
        if resp.status_code != 200:
            log_fail("Personality questions (uz)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        questions = data.get("questions", [])
        trait_labels = data.get("trait_labels", {})
        if len(questions) != 20:
            log_fail("Personality questions (uz)", f"Expected 20 questions, got {len(questions)}")
            return False
        # Validate structure
        q = questions[0]
        if not all(k in q for k in ["id", "trait", "question", "scale"]):
            log_fail("Personality questions (uz)", "Missing required keys")
            return False
        if len(q["scale"]) != 5:
            log_fail("Personality questions (uz)", f"Expected 5 scale options, got {len(q['scale'])}")
            return False
        if len(trait_labels) != 5:
            log_fail("Personality questions (uz)", f"Expected 5 trait labels, got {len(trait_labels)}")
            return False
        log_pass("Personality questions (uz) - 20 questions with 5-point Likert scale")
        return True


async def test_personality_questions_ru():
    """GET /api/personality/questions?lang=ru"""
    log("Testing personality questions (ru)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/personality/questions?lang=ru")
        if resp.status_code != 200:
            log_fail("Personality questions (ru)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if len(data.get("questions", [])) != 20:
            log_fail("Personality questions (ru)", "Wrong number of questions")
            return False
        log_pass("Personality questions (ru) - localization works")
        return True


async def test_personality_questions_en():
    """GET /api/personality/questions?lang=en"""
    log("Testing personality questions (en)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/personality/questions?lang=en")
        if resp.status_code != 200:
            log_fail("Personality questions (en)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if len(data.get("questions", [])) != 20:
            log_fail("Personality questions (en)", "Wrong number of questions")
            return False
        log_pass("Personality questions (en) - localization works")
        return True


async def test_personality_submit():
    """POST /api/personality/submit with full answers"""
    log("Testing personality submit...")
    # Create full answer set (all 20 questions)
    answers = {
        "o1": 5, "o2": 4, "o3": 2, "o4": 5,
        "c1": 5, "c2": 5, "c3": 1, "c4": 5,
        "e1": 4, "e2": 3, "e3": 3, "e4": 4,
        "a1": 5, "a2": 5, "a3": 1, "a4": 5,
        "n1": 2, "n2": 2, "n3": 4, "n4": 1,
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/personality/submit",
            json=answers,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Personality submit", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Personality submit", "Response missing 'ok'")
            return False
        scores = data.get("scores", {})
        if len(scores) != 5:
            log_fail("Personality submit", f"Expected 5 trait scores, got {len(scores)}")
            return False
        # Check all scores are 0-100
        for trait, score in scores.items():
            if not (0 <= score <= 100):
                log_fail("Personality submit", f"{trait} score {score} out of range")
                return False
        bonus = data.get("bonus", 0)
        if bonus != 200:
            log_fail("Personality submit", f"Expected 200 bonus, got {bonus}")
            return False
        log_pass(f"Personality submit - scores: {scores}, bonus: {bonus}")
        return True


async def test_personality_submit_empty():
    """POST /api/personality/submit with empty body - should fail"""
    log("Testing personality submit (empty)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/personality/submit",
            json={},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Personality submit (empty)", f"Expected 400, got {resp.status_code}")
            return False
        log_pass("Personality submit (empty) - correctly rejected with 400")
        return True


async def test_personality_mine():
    """GET /api/personality/mine"""
    log("Testing personality mine...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/personality/mine",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Personality mine", f"Status {resp.status_code}")
            return False
        data = resp.json()
        scores = data.get("scores", {})
        if not scores:
            log_fail("Personality mine", "No scores returned")
            return False
        log_pass(f"Personality mine - scores: {scores}")
        return True


async def test_register_new_user():
    """Register a new user for compatibility testing"""
    global new_user_token, new_user_id
    log("Registering new user...")
    timestamp = int(time.time())
    email = f"test_user_{timestamp}@example.com"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test@123",
                "name": "Test User",
                "gender": "male",
                "birth_date": "1995-01-01"
            }
        )
        if resp.status_code != 200:
            log_fail("Register new user", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        new_user_token = data.get("token")
        new_user_id = data.get("user_id")
        if not new_user_token or not new_user_id:
            log_fail("Register new user", "Missing token or id")
            return False
        log_pass(f"Register new user (id={new_user_id})")
        return True


async def test_personality_compatibility_locked():
    """GET /api/personality/compatibility/{admin_id} as free user - should be locked"""
    log("Testing personality compatibility (locked)...")
    if not new_user_token or not admin_id:
        log_fail("Personality compatibility (locked)", "Missing new user token or admin id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/personality/compatibility/{admin_id}",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Personality compatibility (locked)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not data.get("locked"):
            log_fail("Personality compatibility (locked)", "Expected locked=true for free user")
            return False
        if data.get("unlock_price") != 20000:
            log_fail("Personality compatibility (locked)", f"Expected unlock_price=20000, got {data.get('unlock_price')}")
            return False
        log_pass(f"Personality compatibility (locked) - score: {data.get('score')}, unlock_price: 20000")
        return True


async def test_personality_compatibility_unlocked():
    """GET /api/personality/compatibility/{candidate_id} as admin (VIP) - should be unlocked with AI report"""
    log("Testing personality compatibility (unlocked - VIP)...")
    if not candidate_id:
        log_fail("Personality compatibility (unlocked)", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/personality/compatibility/{candidate_id}?lang=uz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Personality compatibility (unlocked)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if data.get("locked"):
            log_fail("Personality compatibility (unlocked)", "Expected locked=false for VIP user")
            return False
        report = data.get("report", {})
        if not report:
            log_fail("Personality compatibility (unlocked)", "Missing report")
            return False
        # Check report structure
        required_keys = ["summary", "strengths", "watch_outs", "conversation_starters"]
        for key in required_keys:
            if key not in report:
                log_fail("Personality compatibility (unlocked)", f"Missing {key} in report")
                return False
        if not isinstance(report["strengths"], list) or len(report["strengths"]) == 0:
            log_fail("Personality compatibility (unlocked)", "strengths should be non-empty list")
            return False
        if not isinstance(report["watch_outs"], list):
            log_fail("Personality compatibility (unlocked)", "watch_outs should be list")
            return False
        if not isinstance(report["conversation_starters"], list) or len(report["conversation_starters"]) == 0:
            log_fail("Personality compatibility (unlocked)", "conversation_starters should be non-empty list")
            return False
        log_pass(f"Personality compatibility (unlocked) - AI report with summary, {len(report['strengths'])} strengths, {len(report['conversation_starters'])} starters")
        return True


# ============================================================================
# 2. WALI/CHAPERONE
# ============================================================================

async def test_chaperone_invite():
    """POST /api/chaperone/invite"""
    global chaperone_code
    log("Testing chaperone invite...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/chaperone/invite",
            json={"relation": "parent"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone invite", f"Status {resp.status_code}: {resp.text}")
            return False, None
        data = resp.json()
        code = data.get("code")
        if not code or len(code) != 8:
            log_fail("Chaperone invite", f"Expected 8-char code, got {code}")
            return False, None
        link_app = data.get("link_app")
        link_tg = data.get("link_tg")
        if not link_app:
            log_fail("Chaperone invite", "Missing link_app")
            return False, None
        log_pass(f"Chaperone invite - code: {code}, link_tg: {link_tg}")
        return True, code


async def test_register_wali_user():
    """Register a wali user"""
    global wali_token, wali_id
    log("Registering wali user...")
    timestamp = int(time.time())
    email = f"wali_{timestamp}@example.com"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Wali@123",
                "name": "Wali User",
                "gender": "male",
                "birth_date": "1970-01-01"
            }
        )
        if resp.status_code != 200:
            log_fail("Register wali user", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        wali_token = data.get("token")
        wali_id = data.get("user_id")
        if not wali_token or not wali_id:
            log_fail("Register wali user", "Missing token or id")
            return False
        log_pass(f"Register wali user (id={wali_id})")
        return True


async def test_chaperone_accept(code: str):
    """POST /api/chaperone/accept with valid code"""
    log("Testing chaperone accept...")
    if not wali_token:
        log_fail("Chaperone accept", "No wali token")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/chaperone/accept",
            json={"code": code},
            headers={"Authorization": f"Bearer {wali_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone accept", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Chaperone accept", "Response missing 'ok'")
            return False
        log_pass("Chaperone accept - wali linked successfully")
        return True


async def test_chaperone_accept_bogus():
    """POST /api/chaperone/accept with bogus code - should fail"""
    log("Testing chaperone accept (bogus code)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/chaperone/accept",
            json={"code": "BOGUS123"},
            headers={"Authorization": f"Bearer {wali_token}"}
        )
        if resp.status_code != 404:
            log_fail("Chaperone accept (bogus)", f"Expected 404, got {resp.status_code}")
            return False
        log_pass("Chaperone accept (bogus) - correctly rejected with 404")
        return True


async def test_chaperone_accept_self():
    """POST /api/chaperone/accept with own code - should fail"""
    log("Testing chaperone accept (self)...")
    # Create invite as admin
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/chaperone/invite",
            json={"relation": "parent"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone accept (self)", "Failed to create invite")
            return False
        code = resp.json().get("code")
        # Try to accept own code
        resp = await client.post(
            f"{BASE_URL}/chaperone/accept",
            json={"code": code},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Chaperone accept (self)", f"Expected 400, got {resp.status_code}")
            return False
        if "O'zingiz uchun sovchi bo'la olmaysiz" not in resp.text:
            log_fail("Chaperone accept (self)", "Wrong error message")
            return False
        log_pass("Chaperone accept (self) - correctly rejected with 400")
        return True


async def test_chaperone_mine():
    """GET /api/chaperone/mine as admin"""
    log("Testing chaperone mine...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/chaperone/mine",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone mine", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Chaperone mine", "Expected list")
            return False
        if len(data) == 0:
            log_fail("Chaperone mine", "Expected at least 1 wali")
            return False
        log_pass(f"Chaperone mine - {len(data)} wali(s)")
        return True


async def test_chaperone_wards():
    """GET /api/chaperone/wards as wali"""
    log("Testing chaperone wards...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/chaperone/wards",
            headers={"Authorization": f"Bearer {wali_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone wards", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Chaperone wards", "Expected list")
            return False
        if len(data) == 0:
            log_fail("Chaperone wards", "Expected at least 1 ward")
            return False
        log_pass(f"Chaperone wards - {len(data)} ward(s)")
        return True


async def test_chaperone_ward_chats():
    """GET /api/chaperone/ward/{admin_id}/chats as wali"""
    log("Testing chaperone ward chats...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/chaperone/ward/{admin_id}/chats",
            headers={"Authorization": f"Bearer {wali_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone ward chats", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Chaperone ward chats", "Expected list")
            return False
        # Admin should have at least 1 chat (with Madina from prior tests)
        log_pass(f"Chaperone ward chats - {len(data)} chat(s)")
        return True


async def test_chaperone_delete():
    """DELETE /api/chaperone/{link_id}"""
    log("Testing chaperone delete...")
    # First get the link_id
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/chaperone/mine",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone delete", "Failed to get chaperone list")
            return False
        data = resp.json()
        if not data:
            log_fail("Chaperone delete", "No chaperones to delete")
            return False
        link_id = data[0].get("id")
        if not link_id:
            log_fail("Chaperone delete", "Missing link id")
            return False
        # Delete
        resp = await client.delete(
            f"{BASE_URL}/chaperone/{link_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Chaperone delete", f"Status {resp.status_code}: {resp.text}")
            return False
        result = resp.json()
        if not result.get("ok"):
            log_fail("Chaperone delete", "Response missing 'ok'")
            return False
        log_pass("Chaperone delete - successfully removed")
        return True


# ============================================================================
# 3. HINGE-STYLE ROSES
# ============================================================================

async def test_roses_status():
    """GET /api/roses/status as admin (VIP)"""
    log("Testing roses status...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/roses/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Roses status", f"Status {resp.status_code}")
            return False
        data = resp.json()
        free = data.get("free")
        paid = data.get("paid")
        total = data.get("total")
        weekly_quota = data.get("weekly_quota")
        bundles = data.get("bundles")
        if free is None or paid is None or total is None:
            log_fail("Roses status", "Missing free/paid/total")
            return False
        if weekly_quota != 7:  # VIP gets 7
            log_fail("Roses status", f"Expected weekly_quota=7 for VIP, got {weekly_quota}")
            return False
        if not bundles or not isinstance(bundles, dict):
            log_fail("Roses status", "Missing or invalid bundles")
            return False
        log_pass(f"Roses status - free: {free}, paid: {paid}, total: {total}, weekly_quota: {weekly_quota}")
        return True


async def test_roses_send():
    """POST /api/roses/send to candidate"""
    log("Testing roses send...")
    if not candidate_id:
        log_fail("Roses send", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/roses/send",
            json={"to_user_id": candidate_id, "note": "Salom, sizga alohida e'tibor bilan murojaat qilyapman"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Roses send", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Roses send", "Response missing 'ok'")
            return False
        remaining_free = data.get("remaining_free")
        if remaining_free is None:
            log_fail("Roses send", "Missing remaining_free")
            return False
        log_pass(f"Roses send - remaining_free: {remaining_free}")
        return True


async def test_roses_send_self():
    """POST /api/roses/send to self - should fail"""
    log("Testing roses send (self)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/roses/send",
            json={"to_user_id": admin_id, "note": "Test"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Roses send (self)", f"Expected 400, got {resp.status_code}")
            return False
        log_pass("Roses send (self) - correctly rejected with 400")
        return True


async def test_roses_purchase():
    """POST /api/roses/purchase - should return CLICK payment link"""
    log("Testing roses purchase...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/roses/purchase",
            json={"bundle": "5"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Roses purchase", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        payment_link = data.get("payment_link")
        amount = data.get("amount")
        count = data.get("count")
        if not payment_link or "click" not in payment_link.lower():
            log_fail("Roses purchase", f"Invalid payment_link: {payment_link}")
            return False
        if amount != 20000:
            log_fail("Roses purchase", f"Expected amount=20000, got {amount}")
            return False
        if count != 5:
            log_fail("Roses purchase", f"Expected count=5, got {count}")
            return False
        log_pass(f"Roses purchase - payment_link: {payment_link}, amount: {amount}, count: {count}")
        return True


async def test_roses_purchase_invalid():
    """POST /api/roses/purchase with invalid bundle - should fail"""
    log("Testing roses purchase (invalid)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/roses/purchase",
            json={"bundle": "invalid"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Roses purchase (invalid)", f"Expected 400, got {resp.status_code}")
            return False
        log_pass("Roses purchase (invalid) - correctly rejected with 400")
        return True


async def test_roses_purchase_balance():
    """POST /api/roses/purchase-balance - buy from balance"""
    log("Testing roses purchase-balance...")
    # First check admin balance
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Roses purchase-balance", "Failed to get user info")
            return False
        balance = resp.json().get("balance", 0)
        if balance < 5000:
            log(f"⚠️  Roses purchase-balance - insufficient balance ({balance}), skipping")
            return True
        # Purchase 1 rose bundle (5000 UZS)
        resp = await client.post(
            f"{BASE_URL}/roses/purchase-balance",
            json={"bundle": "1"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Roses purchase-balance", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Roses purchase-balance", "Response missing 'ok'")
            return False
        added = data.get("added")
        if added != 1:
            log_fail("Roses purchase-balance", f"Expected added=1, got {added}")
            return False
        log_pass(f"Roses purchase-balance - added: {added}, balance_after: {data.get('balance_after')}")
        return True


# ============================================================================
# 4. AI ICEBREAKERS
# ============================================================================

async def test_ai_icebreakers():
    """GET /api/ai/icebreakers/{candidate_id}?lang=uz"""
    log("Testing AI icebreakers...")
    if not candidate_id:
        log_fail("AI icebreakers", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/ai/icebreakers/{candidate_id}?lang=uz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("AI icebreakers", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        questions = data.get("questions", [])
        ai_generated = data.get("ai_generated")
        if not questions or not isinstance(questions, list):
            log_fail("AI icebreakers", "Missing or invalid questions")
            return False
        if len(questions) < 3:
            log_fail("AI icebreakers", f"Expected at least 3 questions, got {len(questions)}")
            return False
        log_pass(f"AI icebreakers - {len(questions)} questions, ai_generated: {ai_generated}")
        return True


async def test_ai_icebreakers_self():
    """GET /api/ai/icebreakers/{admin_id} as admin - should fail"""
    log("Testing AI icebreakers (self)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/ai/icebreakers/{admin_id}?lang=uz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("AI icebreakers (self)", f"Expected 400, got {resp.status_code}")
            return False
        log_pass("AI icebreakers (self) - correctly rejected with 400")
        return True


# ============================================================================
# 5. AI MODERATION
# ============================================================================

async def test_ai_moderation_phone():
    """POST /api/messages/send with phone number - should be blocked"""
    log("Testing AI moderation (phone)...")
    if not candidate_id:
        log_fail("AI moderation (phone)", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/messages/send",
            json={"to_user_id": candidate_id, "text": "Salom, mening telefon +998901234567 ga qo'ng'iroq qiling"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 422:
            log_fail("AI moderation (phone)", f"Expected 422, got {resp.status_code}")
            return False
        if "telefon" not in resp.text.lower():
            log_fail("AI moderation (phone)", f"Wrong error message: {resp.text}")
            return False
        log_pass("AI moderation (phone) - correctly blocked with 422")
        return True


async def test_ai_moderation_username():
    """POST /api/messages/send with @username - should be blocked"""
    log("Testing AI moderation (@username)...")
    if not candidate_id:
        log_fail("AI moderation (@username)", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/messages/send",
            json={"to_user_id": candidate_id, "text": "@username menga yozing"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 422:
            log_fail("AI moderation (@username)", f"Expected 422, got {resp.status_code}")
            return False
        if "tashqi" not in resp.text.lower():
            log_fail("AI moderation (@username)", f"Wrong error message: {resp.text}")
            return False
        log_pass("AI moderation (@username) - correctly blocked with 422")
        return True


async def test_ai_moderation_normal():
    """POST /api/messages/send with normal message - should pass"""
    log("Testing AI moderation (normal)...")
    if not candidate_id:
        log_fail("AI moderation (normal)", "No candidate_id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/messages/send",
            json={"to_user_id": candidate_id, "text": "Salom! Yaxshimisiz? Qanday kunlar o'tmoqda?"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("AI moderation (normal)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("id"):
            log_fail("AI moderation (normal)", "Message not created")
            return False
        log_pass("AI moderation (normal) - message passed moderation")
        return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    print("=" * 80)
    print("FIDEM BACKEND TEST SUITE - NEW FEATURES")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 80)
    
    results = []
    
    # Setup
    await test_admin_login()
    await test_get_candidate()
    
    # 1. Big 5 Personality Test
    print("\n" + "=" * 80)
    print("1. BIG 5 / OCEAN PERSONALITY TEST")
    print("=" * 80)
    results.append(("Personality questions (uz)", await test_personality_questions_uz()))
    results.append(("Personality questions (ru)", await test_personality_questions_ru()))
    results.append(("Personality questions (en)", await test_personality_questions_en()))
    results.append(("Personality submit", await test_personality_submit()))
    results.append(("Personality submit (empty)", await test_personality_submit_empty()))
    results.append(("Personality mine", await test_personality_mine()))
    
    # Register new user for compatibility testing
    await test_register_new_user()
    results.append(("Personality compatibility (locked)", await test_personality_compatibility_locked()))
    results.append(("Personality compatibility (unlocked)", await test_personality_compatibility_unlocked()))
    
    # 2. Wali/Chaperone
    print("\n" + "=" * 80)
    print("2. WALI/CHAPERONE")
    print("=" * 80)
    success, code = await test_chaperone_invite()
    results.append(("Chaperone invite", success))
    
    if code:
        await test_register_wali_user()
        results.append(("Chaperone accept", await test_chaperone_accept(code)))
    
    results.append(("Chaperone accept (bogus)", await test_chaperone_accept_bogus()))
    results.append(("Chaperone accept (self)", await test_chaperone_accept_self()))
    results.append(("Chaperone mine", await test_chaperone_mine()))
    results.append(("Chaperone wards", await test_chaperone_wards()))
    results.append(("Chaperone ward chats", await test_chaperone_ward_chats()))
    results.append(("Chaperone delete", await test_chaperone_delete()))
    
    # 3. Roses
    print("\n" + "=" * 80)
    print("3. HINGE-STYLE ROSES")
    print("=" * 80)
    results.append(("Roses status", await test_roses_status()))
    results.append(("Roses send", await test_roses_send()))
    results.append(("Roses send (self)", await test_roses_send_self()))
    results.append(("Roses purchase", await test_roses_purchase()))
    results.append(("Roses purchase (invalid)", await test_roses_purchase_invalid()))
    results.append(("Roses purchase-balance", await test_roses_purchase_balance()))
    
    # 4. AI Icebreakers
    print("\n" + "=" * 80)
    print("4. AI ICEBREAKERS")
    print("=" * 80)
    results.append(("AI icebreakers", await test_ai_icebreakers()))
    results.append(("AI icebreakers (self)", await test_ai_icebreakers_self()))
    
    # 5. AI Moderation
    print("\n" + "=" * 80)
    print("5. AI MODERATION")
    print("=" * 80)
    results.append(("AI moderation (phone)", await test_ai_moderation_phone()))
    results.append(("AI moderation (@username)", await test_ai_moderation_username()))
    results.append(("AI moderation (normal)", await test_ai_moderation_normal()))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    passed = sum(1 for _, r in results if r)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print("\n⚠️  SOME TESTS FAILED")
        print("\nFailed tests:")
        for name, result in results:
            if not result:
                print(f"  - {name}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
