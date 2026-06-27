#!/usr/bin/env python3
"""
Backend API test suite for FIDEM - FAZA 3.5 NEW FEATURES
Tests: Boost & Spotlight Analytics, Financial Verification, Telegram push notifications
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from io import BytesIO

import httpx

# Base URL from frontend/.env
BASE_URL = "https://loyihani-clone.preview.emergentagent.com/api"
TIMEOUT = 20.0

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Global state
admin_token = None
admin_id = None
new_user_token = None
new_user_id = None
verification_id = None


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


async def test_register_new_user():
    """Register a new user for testing"""
    global new_user_token, new_user_id
    log("Registering new user...")
    timestamp = int(time.time())
    email = f"faza35_user_{timestamp}@example.com"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test@123",
                "name": "Faza35 Test User",
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


# ============================================================================
# 1. BOOST & SPOTLIGHT ANALYTICS
# ============================================================================

async def test_boost_analytics_initial():
    """GET /api/boost/analytics - initial state"""
    log("Testing boost analytics (initial)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost analytics (initial)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        
        # Check structure
        if "boost" not in data or "spotlight" not in data or "lifetime" not in data:
            log_fail("Boost analytics (initial)", "Missing top-level keys")
            return False
        
        boost = data["boost"]
        spotlight = data["spotlight"]
        lifetime = data["lifetime"]
        
        # Check boost fields
        required_boost = ["active", "until", "impressions", "views", "likes", "messages", "roses", "started_at"]
        for field in required_boost:
            if field not in boost:
                log_fail("Boost analytics (initial)", f"Missing boost.{field}")
                return False
        
        # Check spotlight fields
        required_spotlight = ["active", "until", "impressions", "views", "started_at"]
        for field in required_spotlight:
            if field not in spotlight:
                log_fail("Boost analytics (initial)", f"Missing spotlight.{field}")
                return False
        
        # Check lifetime fields
        required_lifetime = ["total_impressions", "total_views", "total_likes", "gifts_received"]
        for field in required_lifetime:
            if field not in lifetime:
                log_fail("Boost analytics (initial)", f"Missing lifetime.{field}")
                return False
        
        log_pass(f"Boost analytics (initial) - boost.active={boost['active']}, spotlight.active={spotlight['active']}, lifetime.total_impressions={lifetime['total_impressions']}")
        return True


async def test_boost_leaderboard_initial():
    """GET /api/boost/leaderboard - may be empty if no one is boosted"""
    log("Testing boost leaderboard (initial)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/leaderboard",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost leaderboard (initial)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        
        if not isinstance(data, list):
            log_fail("Boost leaderboard (initial)", "Expected list")
            return False
        
        # May be empty if no one is boosted
        log_pass(f"Boost leaderboard (initial) - {len(data)} boosted users")
        return True


async def test_admin_topup_balance():
    """PATCH /api/admin/users/{admin_id} to add balance"""
    log("Testing admin top-up balance...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.patch(
            f"{BASE_URL}/admin/users/{admin_id}",
            json={"add_balance": 50000},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin top-up balance", f"Status {resp.status_code}: {resp.text}")
            return False
        
        # Verify balance increased
        resp = await client.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin top-up balance", "Failed to verify balance")
            return False
        
        balance = resp.json().get("balance", 0)
        if balance < 50000:
            log_fail("Admin top-up balance", f"Balance {balance} < 50000")
            return False
        
        log_pass(f"Admin top-up balance - new balance: {balance}")
        return True


async def test_boost_activate():
    """POST /api/boost/activate with use_balance=true"""
    log("Testing boost activate...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/boost/activate",
            json={"use_balance": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost activate", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("active"):
            log_fail("Boost activate", "active=false")
            return False
        
        if not data.get("until"):
            log_fail("Boost activate", "Missing until")
            return False
        
        log_pass(f"Boost activate - active=true, until={data['until']}")
        return True


async def test_boost_analytics_after_activate():
    """GET /api/boost/analytics after activation - verify started_at and counters reset"""
    log("Testing boost analytics (after activate)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost analytics (after activate)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        boost = data["boost"]
        
        if not boost["active"]:
            log_fail("Boost analytics (after activate)", "boost.active=false")
            return False
        
        if not boost["started_at"]:
            log_fail("Boost analytics (after activate)", "Missing boost.started_at")
            return False
        
        # Counters should be 0 after activation
        if boost["impressions"] != 0:
            log_fail("Boost analytics (after activate)", f"impressions={boost['impressions']}, expected 0")
            return False
        
        log_pass(f"Boost analytics (after activate) - active=true, started_at={boost['started_at']}, impressions=0")
        return True


async def test_candidates_trigger_impressions():
    """GET /api/candidates as new user - should increment admin's boost impressions"""
    log("Testing candidates (trigger impressions)...")
    if not new_user_token:
        log_fail("Candidates (trigger impressions)", "No new user token")
        return False
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/candidates",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Candidates (trigger impressions)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Candidates (trigger impressions)", "Expected list")
            return False
        
        # Check if admin appears in candidates
        admin_in_list = any(c.get("id") == admin_id for c in data)
        
        log_pass(f"Candidates (trigger impressions) - {len(data)} candidates, admin_in_list={admin_in_list}")
        return True


async def test_boost_analytics_impressions_incremented():
    """GET /api/boost/analytics - verify impressions >= 1"""
    log("Testing boost analytics (impressions incremented)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost analytics (impressions)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        boost = data["boost"]
        lifetime = data["lifetime"]
        
        if boost["impressions"] < 1:
            log_fail("Boost analytics (impressions)", f"boost.impressions={boost['impressions']}, expected >= 1")
            return False
        
        if lifetime["total_impressions"] < 1:
            log_fail("Boost analytics (impressions)", f"lifetime.total_impressions={lifetime['total_impressions']}, expected >= 1")
            return False
        
        log_pass(f"Boost analytics (impressions) - boost.impressions={boost['impressions']}, lifetime.total_impressions={lifetime['total_impressions']}")
        return True


async def test_candidate_detail_trigger_views():
    """GET /api/candidates/{admin_id} as new user - should increment admin's boost views"""
    log("Testing candidate detail (trigger views)...")
    if not new_user_token:
        log_fail("Candidate detail (trigger views)", "No new user token")
        return False
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/candidates/{admin_id}",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Candidate detail (trigger views)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if data.get("id") != admin_id:
            log_fail("Candidate detail (trigger views)", "Wrong user returned")
            return False
        
        log_pass(f"Candidate detail (trigger views) - viewed admin profile")
        return True


async def test_boost_analytics_views_incremented():
    """GET /api/boost/analytics - verify views >= 1"""
    log("Testing boost analytics (views incremented)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost analytics (views)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        boost = data["boost"]
        lifetime = data["lifetime"]
        
        if boost["views"] < 1:
            log_fail("Boost analytics (views)", f"boost.views={boost['views']}, expected >= 1")
            return False
        
        if lifetime["total_views"] < 1:
            log_fail("Boost analytics (views)", f"lifetime.total_views={lifetime['total_views']}, expected >= 1")
            return False
        
        log_pass(f"Boost analytics (views) - boost.views={boost['views']}, lifetime.total_views={lifetime['total_views']}")
        return True


async def test_saved_trigger_likes():
    """POST /api/saved {user_id: admin_id} as new user - should increment admin's boost likes"""
    log("Testing saved (trigger likes)...")
    if not new_user_token:
        log_fail("Saved (trigger likes)", "No new user token")
        return False
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/saved",
            json={"user_id": admin_id},
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Saved (trigger likes)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_fail("Saved (trigger likes)", "Response missing 'ok'")
            return False
        
        log_pass(f"Saved (trigger likes) - saved admin")
        return True


async def test_boost_analytics_likes_incremented():
    """GET /api/boost/analytics - verify likes >= 1"""
    log("Testing boost analytics (likes incremented)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/analytics",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost analytics (likes)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        boost = data["boost"]
        lifetime = data["lifetime"]
        
        if boost["likes"] < 1:
            log_fail("Boost analytics (likes)", f"boost.likes={boost['likes']}, expected >= 1")
            return False
        
        if lifetime["total_likes"] < 1:
            log_fail("Boost analytics (likes)", f"lifetime.total_likes={lifetime['total_likes']}, expected >= 1")
            return False
        
        log_pass(f"Boost analytics (likes) - boost.likes={boost['likes']}, lifetime.total_likes={lifetime['total_likes']}")
        return True


async def test_boost_leaderboard_admin_appears():
    """GET /api/boost/leaderboard - admin should appear with non-zero boost_impressions"""
    log("Testing boost leaderboard (admin appears)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/boost/leaderboard",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Boost leaderboard (admin appears)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if not isinstance(data, list):
            log_fail("Boost leaderboard (admin appears)", "Expected list")
            return False
        
        # Find admin in leaderboard
        admin_entry = None
        for entry in data:
            if entry.get("id") == admin_id:
                admin_entry = entry
                break
        
        if not admin_entry:
            log_fail("Boost leaderboard (admin appears)", "Admin not in leaderboard")
            return False
        
        # Check required fields
        required_fields = ["id", "name", "age", "region", "photo_url", "boost_impressions", "boost_until"]
        for field in required_fields:
            if field not in admin_entry:
                log_fail("Boost leaderboard (admin appears)", f"Missing field: {field}")
                return False
        
        if admin_entry["boost_impressions"] < 1:
            log_fail("Boost leaderboard (admin appears)", f"boost_impressions={admin_entry['boost_impressions']}, expected >= 1")
            return False
        
        log_pass(f"Boost leaderboard (admin appears) - admin in leaderboard with boost_impressions={admin_entry['boost_impressions']}")
        return True


# ============================================================================
# 2. FINANCIAL VERIFICATION
# ============================================================================

async def test_verification_mine_initial():
    """GET /api/verification/mine - initial state"""
    log("Testing verification mine (initial)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/verification/mine",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Verification mine (initial)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        # Check structure
        if "items" not in data:
            log_fail("Verification mine (initial)", "Missing 'items'")
            return False
        
        if not isinstance(data["items"], list):
            log_fail("Verification mine (initial)", "'items' should be list")
            return False
        
        # Check verified flags
        required_flags = ["verified_identity", "verified_selfie", "verified_financial"]
        for flag in required_flags:
            if flag not in data:
                log_fail("Verification mine (initial)", f"Missing {flag}")
                return False
            if data[flag] != False:
                log_fail("Verification mine (initial)", f"{flag} should be false for new user")
                return False
        
        log_pass(f"Verification mine (initial) - all verified flags are false, {len(data['items'])} items")
        return True


async def test_verification_request_financial():
    """POST /api/verification/request with kind=financial"""
    global verification_id
    log("Testing verification request (financial)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/verification/request",
            json={
                "kind": "financial",
                "note": "Test financial verification for Faza 3.5",
                "proof_url": "https://example.com/proof.pdf"
            },
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Verification request (financial)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_fail("Verification request (financial)", "Response missing 'ok'")
            return False
        
        verification_id = data.get("id")
        if not verification_id:
            log_fail("Verification request (financial)", "Missing id")
            return False
        
        log_pass(f"Verification request (financial) - id={verification_id}")
        return True


async def test_admin_verifications_pending():
    """GET /api/admin/verifications?status=pending as admin"""
    log("Testing admin verifications (pending)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/admin/verifications?status=pending",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin verifications (pending)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if not isinstance(data, list):
            log_fail("Admin verifications (pending)", "Expected list")
            return False
        
        # Find our verification
        our_verification = None
        for v in data:
            if v.get("id") == verification_id:
                our_verification = v
                break
        
        if not our_verification:
            log_fail("Admin verifications (pending)", "Our verification not found")
            return False
        
        # Check enrichment with user data
        if "user" not in our_verification:
            log_fail("Admin verifications (pending)", "Missing 'user' enrichment")
            return False
        
        user = our_verification["user"]
        required_user_fields = ["name", "email", "photo_url", "id", "verified_financial", "verified_identity", "verified_selfie"]
        for field in required_user_fields:
            if field not in user:
                log_fail("Admin verifications (pending)", f"Missing user.{field}")
                return False
        
        if our_verification.get("status") != "pending":
            log_fail("Admin verifications (pending)", f"status={our_verification.get('status')}, expected 'pending'")
            return False
        
        log_pass(f"Admin verifications (pending) - found verification with user enrichment")
        return True


async def test_admin_verifications_all():
    """GET /api/admin/verifications?status=all as admin"""
    log("Testing admin verifications (all)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/admin/verifications?status=all",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin verifications (all)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if not isinstance(data, list):
            log_fail("Admin verifications (all)", "Expected list")
            return False
        
        log_pass(f"Admin verifications (all) - {len(data)} total verifications")
        return True


async def test_admin_decide_reject():
    """POST /api/admin/verifications/{vid}/decide with approve=false"""
    log("Testing admin decide (reject)...")
    
    # Create a new verification to reject
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/verification/request",
            json={
                "kind": "financial",
                "note": "Test rejection",
                "proof_url": "https://example.com/bad_proof.pdf"
            },
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (reject)", "Failed to create verification")
            return False
        
        reject_vid = resp.json().get("id")
        
        # Reject it
        resp = await client.post(
            f"{BASE_URL}/admin/verifications/{reject_vid}/decide",
            json={"approve": False, "reason": "Hujjat aniq emas"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (reject)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_fail("Admin decide (reject)", "Response missing 'ok'")
            return False
        
        # Verify status changed to rejected
        resp = await client.get(
            f"{BASE_URL}/verification/mine",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (reject)", "Failed to verify rejection")
            return False
        
        items = resp.json().get("items", [])
        rejected_item = None
        for item in items:
            if item.get("id") == reject_vid:
                rejected_item = item
                break
        
        if not rejected_item:
            log_fail("Admin decide (reject)", "Rejected item not found")
            return False
        
        if rejected_item.get("status") != "rejected":
            log_fail("Admin decide (reject)", f"status={rejected_item.get('status')}, expected 'rejected'")
            return False
        
        if rejected_item.get("rejection_reason") != "Hujjat aniq emas":
            log_fail("Admin decide (reject)", f"rejection_reason={rejected_item.get('rejection_reason')}")
            return False
        
        log_pass(f"Admin decide (reject) - status=rejected, rejection_reason populated")
        return True


async def test_admin_decide_approve():
    """POST /api/admin/verifications/{vid}/decide with approve=true"""
    log("Testing admin decide (approve)...")
    
    # Approve the original verification
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/admin/verifications/{verification_id}/decide",
            json={"approve": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (approve)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_fail("Admin decide (approve)", "Response missing 'ok'")
            return False
        
        # Verify user.verified_financial = true
        resp = await client.get(
            f"{BASE_URL}/verification/mine",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (approve)", "Failed to verify approval")
            return False
        
        data = resp.json()
        if not data.get("verified_financial"):
            log_fail("Admin decide (approve)", "verified_financial should be true")
            return False
        
        # Verify 'b_financial' badge added
        resp = await client.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin decide (approve)", "Failed to get user info")
            return False
        
        user = resp.json()
        badges = user.get("badges", [])
        if "b_financial" not in badges:
            log_fail("Admin decide (approve)", f"'b_financial' not in badges: {badges}")
            return False
        
        log_pass(f"Admin decide (approve) - verified_financial=true, 'b_financial' badge added")
        return True


async def test_file_upload_pdf():
    """POST /api/files/upload with PDF file"""
    log("Testing file upload (PDF)...")
    
    # Create a minimal PDF file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f\n0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n190\n%%EOF"
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
        resp = await client.post(
            f"{BASE_URL}/files/upload",
            files=files,
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("File upload (PDF)", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("url"):
            log_fail("File upload (PDF)", "Missing url")
            return False
        
        log_pass(f"File upload (PDF) - url={data['url']}")
        return True


async def test_file_upload_unsupported():
    """POST /api/files/upload with unsupported file type - should fail"""
    log("Testing file upload (unsupported)...")
    
    # Create a text file
    txt_content = b"This is a text file"
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        files = {"file": ("test.txt", BytesIO(txt_content), "text/plain")}
        resp = await client.post(
            f"{BASE_URL}/files/upload",
            files=files,
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 400:
            log_fail("File upload (unsupported)", f"Expected 400, got {resp.status_code}")
            return False
        
        if "Only image" not in resp.text and "PDF" not in resp.text:
            log_fail("File upload (unsupported)", f"Wrong error message: {resp.text}")
            return False
        
        log_pass(f"File upload (unsupported) - correctly rejected with 400")
        return True


# ============================================================================
# 3. TELEGRAM PUSH NOTIFICATIONS (SMOKE TEST)
# ============================================================================

async def test_saved_push_notification():
    """POST /api/saved - should trigger push notification (no error)"""
    log("Testing saved push notification...")
    
    # Admin saves new user
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/saved",
            json={"user_id": new_user_id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Saved push notification", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_fail("Saved push notification", "Response missing 'ok'")
            return False
        
        log_pass(f"Saved push notification - no errors")
        return True


async def test_notifications_list():
    """GET /api/notifications - verify notification was created"""
    log("Testing notifications list...")
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/notifications",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 200:
            log_fail("Notifications list", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        if not isinstance(data, list):
            log_fail("Notifications list", "Expected list")
            return False
        
        # Find notification with 'saqladi' (saved)
        saved_notif = None
        for notif in data:
            if "saqladi" in notif.get("text", "").lower():
                saved_notif = notif
                break
        
        if not saved_notif:
            log_fail("Notifications list", "Saved notification not found")
            return False
        
        # Check if link field exists (may be None)
        if "link" not in saved_notif:
            log_fail("Notifications list", "Missing 'link' field")
            return False
        
        log_pass(f"Notifications list - found saved notification with link field")
        return True


# ============================================================================
# 4. REGRESSION CHECKS
# ============================================================================

async def test_regression_candidates():
    """GET /api/candidates - basic smoke test"""
    log("Testing regression: candidates...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/candidates",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Regression: candidates", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Regression: candidates", "Expected list")
            return False
        
        log_pass(f"Regression: candidates - {len(data)} candidates")
        return True


async def test_regression_withdrawals_status():
    """GET /api/withdrawals/status - smoke test"""
    log("Testing regression: withdrawals/status...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/withdrawals/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Regression: withdrawals/status", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if "withdrawable_balance" not in data:
            log_fail("Regression: withdrawals/status", "Missing withdrawable_balance")
            return False
        
        log_pass(f"Regression: withdrawals/status - OK")
        return True


async def test_regression_concierge_info():
    """GET /api/concierge/info - smoke test"""
    log("Testing regression: concierge/info...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/concierge/info",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Regression: concierge/info", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if "price" not in data:
            log_fail("Regression: concierge/info", "Missing price")
            return False
        
        log_pass(f"Regression: concierge/info - OK")
        return True


async def test_regression_travel_status():
    """GET /api/travel/status - smoke test"""
    log("Testing regression: travel/status...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/travel/status",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Regression: travel/status", f"Status {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if "active" not in data:
            log_fail("Regression: travel/status", "Missing active")
            return False
        
        log_pass(f"Regression: travel/status - OK")
        return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    print("=" * 80)
    print("FIDEM BACKEND TEST SUITE - FAZA 3.5 NEW FEATURES")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 80)
    
    results = []
    
    # Setup
    await test_admin_login()
    await test_register_new_user()
    
    # 1. Boost & Spotlight Analytics
    print("\n" + "=" * 80)
    print("1. BOOST & SPOTLIGHT ANALYTICS")
    print("=" * 80)
    results.append(("Boost analytics (initial)", await test_boost_analytics_initial()))
    results.append(("Boost leaderboard (initial)", await test_boost_leaderboard_initial()))
    results.append(("Admin top-up balance", await test_admin_topup_balance()))
    results.append(("Boost activate", await test_boost_activate()))
    results.append(("Boost analytics (after activate)", await test_boost_analytics_after_activate()))
    results.append(("Candidates (trigger impressions)", await test_candidates_trigger_impressions()))
    results.append(("Boost analytics (impressions)", await test_boost_analytics_impressions_incremented()))
    results.append(("Candidate detail (trigger views)", await test_candidate_detail_trigger_views()))
    results.append(("Boost analytics (views)", await test_boost_analytics_views_incremented()))
    results.append(("Saved (trigger likes)", await test_saved_trigger_likes()))
    results.append(("Boost analytics (likes)", await test_boost_analytics_likes_incremented()))
    results.append(("Boost leaderboard (admin appears)", await test_boost_leaderboard_admin_appears()))
    
    # 2. Financial Verification
    print("\n" + "=" * 80)
    print("2. FINANCIAL VERIFICATION")
    print("=" * 80)
    results.append(("Verification mine (initial)", await test_verification_mine_initial()))
    results.append(("Verification request (financial)", await test_verification_request_financial()))
    results.append(("Admin verifications (pending)", await test_admin_verifications_pending()))
    results.append(("Admin verifications (all)", await test_admin_verifications_all()))
    results.append(("Admin decide (reject)", await test_admin_decide_reject()))
    results.append(("Admin decide (approve)", await test_admin_decide_approve()))
    results.append(("File upload (PDF)", await test_file_upload_pdf()))
    results.append(("File upload (unsupported)", await test_file_upload_unsupported()))
    
    # 3. Telegram Push Notifications
    print("\n" + "=" * 80)
    print("3. TELEGRAM PUSH NOTIFICATIONS (SMOKE TEST)")
    print("=" * 80)
    results.append(("Saved push notification", await test_saved_push_notification()))
    results.append(("Notifications list", await test_notifications_list()))
    
    # 4. Regression Checks
    print("\n" + "=" * 80)
    print("4. REGRESSION CHECKS")
    print("=" * 80)
    results.append(("Regression: candidates", await test_regression_candidates()))
    results.append(("Regression: withdrawals/status", await test_regression_withdrawals_status()))
    results.append(("Regression: concierge/info", await test_regression_concierge_info()))
    results.append(("Regression: travel/status", await test_regression_travel_status()))
    
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
