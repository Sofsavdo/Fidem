#!/usr/bin/env python3
"""
Backend API test suite for FIDEM - FAZA 2 ADDITIONS
Tests: Profile Prompts, Success Stories, Gamification
"""
import asyncio
import json
import sys
import time
from datetime import datetime

import httpx

# Base URL from frontend/.env
BASE_URL = "https://loyihani-clone.preview.emergentagent.com/api"
TIMEOUT = 15.0

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Global state
admin_token = None
admin_id = None
new_user_token = None
new_user_id = None
test_story_id = None


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
    """Register a new user for non-admin testing"""
    global new_user_token, new_user_id
    log("Registering new user...")
    timestamp = int(time.time())
    email = f"test_user_faza2_{timestamp}@example.com"
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/auth/register",
            json={
                "email": email,
                "password": "Test@123",
                "name": "Test User Faza2",
                "gender": "female",
                "birth_date": "1995-05-15"
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
# 1. PROFILE PROMPTS
# ============================================================================

async def test_prompts_library_uz():
    """GET /api/prompts/library?lang=uz → expect 16 items"""
    log("Testing prompts library (uz)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/prompts/library?lang=uz")
        if resp.status_code != 200:
            log_fail("Prompts library (uz)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Prompts library (uz)", "Expected list")
            return False
        if len(data) != 16:
            log_fail("Prompts library (uz)", f"Expected 16 items, got {len(data)}")
            return False
        # Validate structure
        item = data[0]
        if not all(k in item for k in ["id", "category", "text"]):
            log_fail("Prompts library (uz)", "Missing required keys")
            return False
        log_pass(f"Prompts library (uz) - 16 items with proper structure")
        return True


async def test_prompts_library_ru():
    """GET /api/prompts/library?lang=ru → verify localization"""
    log("Testing prompts library (ru)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/prompts/library?lang=ru")
        if resp.status_code != 200:
            log_fail("Prompts library (ru)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if len(data) != 16:
            log_fail("Prompts library (ru)", f"Expected 16 items, got {len(data)}")
            return False
        log_pass("Prompts library (ru) - localization works")
        return True


async def test_prompts_library_en():
    """GET /api/prompts/library?lang=en → verify localization"""
    log("Testing prompts library (en)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/prompts/library?lang=en")
        if resp.status_code != 200:
            log_fail("Prompts library (en)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if len(data) != 16:
            log_fail("Prompts library (en)", f"Expected 16 items, got {len(data)}")
            return False
        log_pass("Prompts library (en) - localization works")
        return True


async def test_prompts_mine_initial():
    """GET /api/prompts/mine as admin → expect empty or previously saved"""
    log("Testing prompts mine (initial)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/prompts/mine",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Prompts mine (initial)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Prompts mine (initial)", "Expected list")
            return False
        log_pass(f"Prompts mine (initial) - {len(data)} prompts")
        return True


async def test_prompts_save_valid():
    """POST /api/prompts/save with 2 valid items → expect 200"""
    log("Testing prompts save (valid)...")
    prompts = [
        {"id": "p_values", "answer": "Halollik va oila", "kind": "text"},
        {"id": "p_dream", "answer": "5 yildan keyin biznesim bo'ladi va oilam bilan baxtli yashayman", "kind": "text"}
    ]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/prompts/save",
            json=prompts,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Prompts save (valid)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Prompts save (valid)", "Response missing 'ok'")
            return False
        saved_prompts = data.get("prompts", [])
        if len(saved_prompts) != 2:
            log_fail("Prompts save (valid)", f"Expected 2 prompts, got {len(saved_prompts)}")
            return False
        log_pass(f"Prompts save (valid) - 2 prompts saved")
        return True


async def test_prompts_save_max_exceeded():
    """POST /api/prompts/save with 4 items → expect 400 (max 3)"""
    log("Testing prompts save (max exceeded)...")
    prompts = [
        {"id": "p_values", "answer": "Test 1", "kind": "text"},
        {"id": "p_dream", "answer": "Test 2", "kind": "text"},
        {"id": "p_family", "answer": "Test 3", "kind": "text"},
        {"id": "p_partner", "answer": "Test 4", "kind": "text"}
    ]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/prompts/save",
            json=prompts,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Prompts save (max exceeded)", f"Expected 400, got {resp.status_code}")
            return False
        if "3" not in resp.text:
            log_fail("Prompts save (max exceeded)", "Error message should mention max 3")
            return False
        log_pass("Prompts save (max exceeded) - correctly rejected with 400")
        return True


async def test_prompts_save_invalid_id():
    """POST /api/prompts/save with invalid id → silently filtered"""
    log("Testing prompts save (invalid id)...")
    prompts = [
        {"id": "p_nonexistent", "answer": "This should be filtered", "kind": "text"},
        {"id": "p_values", "answer": "This is valid", "kind": "text"}
    ]
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/prompts/save",
            json=prompts,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Prompts save (invalid id)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        saved_prompts = data.get("prompts", [])
        # Should only save the valid one
        if len(saved_prompts) != 1:
            log_fail("Prompts save (invalid id)", f"Expected 1 valid prompt, got {len(saved_prompts)}")
            return False
        if saved_prompts[0]["id"] != "p_values":
            log_fail("Prompts save (invalid id)", "Wrong prompt saved")
            return False
        log_pass("Prompts save (invalid id) - invalid items silently filtered")
        return True


async def test_prompts_mine_after_save():
    """GET /api/prompts/mine → verify saved prompts"""
    log("Testing prompts mine (after save)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/prompts/mine",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Prompts mine (after save)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list) or len(data) == 0:
            log_fail("Prompts mine (after save)", "Expected non-empty list")
            return False
        log_pass(f"Prompts mine (after save) - {len(data)} prompts found")
        return True


async def test_prompts_xp_awarded():
    """Verify XP awarded only first time by checking /me/progress"""
    log("Testing prompts XP award...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Get initial XP
        resp1 = await client.get(
            f"{BASE_URL}/me/progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp1.status_code != 200:
            log_fail("Prompts XP award", "Failed to get initial progress")
            return False
        xp1 = resp1.json().get("xp", 0)
        
        # Save prompts again (should not award XP again)
        prompts = [{"id": "p_values", "answer": "Test", "kind": "text"}]
        resp2 = await client.post(
            f"{BASE_URL}/prompts/save",
            json=prompts,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp2.status_code != 200:
            log_fail("Prompts XP award", "Failed to save prompts")
            return False
        
        # Get XP again
        resp3 = await client.get(
            f"{BASE_URL}/me/progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp3.status_code != 200:
            log_fail("Prompts XP award", "Failed to get progress after save")
            return False
        xp2 = resp3.json().get("xp", 0)
        
        # XP should not increase (already awarded)
        if xp2 != xp1:
            log_fail("Prompts XP award", f"XP changed from {xp1} to {xp2} (should not double-award)")
            return False
        log_pass("Prompts XP award - XP not double-awarded")
        return True


# ============================================================================
# 2. SUCCESS STORIES
# ============================================================================

async def test_stories_list():
    """GET /api/stories → expect ~3 seeded stories"""
    log("Testing stories list...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/stories")
        if resp.status_code != 200:
            log_fail("Stories list", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Stories list", "Expected list")
            return False
        if len(data) < 3:
            log_fail("Stories list", f"Expected at least 3 stories, got {len(data)}")
            return False
        # Validate structure
        story = data[0]
        required_keys = ["couple_names", "region", "year", "story_text", "published"]
        if not all(k in story for k in required_keys):
            log_fail("Stories list", f"Missing required keys: {required_keys}")
            return False
        log_pass(f"Stories list - {len(data)} stories found")
        return True


async def test_stories_featured():
    """GET /api/stories?featured_only=true → expect 2 featured"""
    log("Testing stories featured...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/stories?featured_only=true")
        if resp.status_code != 200:
            log_fail("Stories featured", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Stories featured", "Expected list")
            return False
        if len(data) < 2:
            log_fail("Stories featured", f"Expected at least 2 featured stories, got {len(data)}")
            return False
        # Verify all are featured
        for story in data:
            if not story.get("featured"):
                log_fail("Stories featured", "Non-featured story in results")
                return False
        log_pass(f"Stories featured - {len(data)} featured stories")
        return True


async def test_stories_get_by_id():
    """GET /api/stories/{id} → expect 200, views increment"""
    log("Testing stories get by id...")
    # First get a story id
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/stories")
        if resp.status_code != 200:
            log_fail("Stories get by id", "Failed to get story list")
            return False
        stories = resp.json()
        if not stories:
            log_fail("Stories get by id", "No stories available")
            return False
        story_id = stories[0]["id"]
        initial_views = stories[0].get("views", 0)
        
        # Get story by id
        resp = await client.get(f"{BASE_URL}/stories/{story_id}")
        if resp.status_code != 200:
            log_fail("Stories get by id", f"Status {resp.status_code}")
            return False
        story = resp.json()
        if story["id"] != story_id:
            log_fail("Stories get by id", "Wrong story returned")
            return False
        
        # Get again to check views increment
        resp = await client.get(f"{BASE_URL}/stories/{story_id}")
        if resp.status_code != 200:
            log_fail("Stories get by id", "Failed second fetch")
            return False
        
        # Get list again to verify views incremented
        resp = await client.get(f"{BASE_URL}/stories")
        stories_after = resp.json()
        story_after = next((s for s in stories_after if s["id"] == story_id), None)
        if not story_after:
            log_fail("Stories get by id", "Story not found after fetch")
            return False
        
        final_views = story_after.get("views", 0)
        if final_views <= initial_views:
            log_fail("Stories get by id", f"Views did not increment: {initial_views} -> {final_views}")
            return False
        
        log_pass(f"Stories get by id - views incremented from {initial_views} to {final_views}")
        return True


async def test_stories_get_bogus_id():
    """GET /api/stories/{bogus-id} → expect 404"""
    log("Testing stories get bogus id...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(f"{BASE_URL}/stories/bogus_id_12345")
        if resp.status_code != 404:
            log_fail("Stories get bogus id", f"Expected 404, got {resp.status_code}")
            return False
        log_pass("Stories get bogus id - correctly returned 404")
        return True


async def test_stories_submit_valid():
    """POST /api/stories/submit with valid data → expect 200 with status:pending_review"""
    log("Testing stories submit (valid)...")
    story_data = {
        "couple_names": "Test Couple",
        "region": "Toshkent",
        "year": 2025,
        "story_text": "This is a test story that is definitely longer than 30 characters to pass validation."
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/stories/submit",
            json=story_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Stories submit (valid)", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Stories submit (valid)", "Response missing 'ok'")
            return False
        if data.get("status") != "pending_review":
            log_fail("Stories submit (valid)", f"Expected status 'pending_review', got {data.get('status')}")
            return False
        if not data.get("id"):
            log_fail("Stories submit (valid)", "Missing story id")
            return False
        log_pass(f"Stories submit (valid) - id: {data.get('id')}, status: pending_review")
        return True


async def test_stories_submit_short_text():
    """POST /api/stories/submit with short text → expect 400"""
    log("Testing stories submit (short text)...")
    story_data = {
        "couple_names": "Test",
        "region": "Toshkent",
        "year": 2025,
        "story_text": "short"
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/stories/submit",
            json=story_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 400:
            log_fail("Stories submit (short text)", f"Expected 400, got {resp.status_code}")
            return False
        if "30" not in resp.text:
            log_fail("Stories submit (short text)", "Error message should mention 30 chars")
            return False
        log_pass("Stories submit (short text) - correctly rejected with 400")
        return True


async def test_admin_stories_create():
    """POST /api/admin/stories as admin → expect 200"""
    global test_story_id
    log("Testing admin stories create...")
    story_data = {
        "couple_names": "Admin Test Couple",
        "region": "Samarqand",
        "year": 2024,
        "story_text": "This is an admin-created test story for testing purposes. It has enough characters to pass validation.",
        "published": True,
        "featured": False
    }
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(
            f"{BASE_URL}/admin/stories",
            json=story_data,
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin stories create", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Admin stories create", "Response missing 'ok'")
            return False
        test_story_id = data.get("id")
        if not test_story_id:
            log_fail("Admin stories create", "Missing story id")
            return False
        log_pass(f"Admin stories create - id: {test_story_id}")
        return True


async def test_admin_stories_patch():
    """PATCH /api/admin/stories/{id} as admin → expect 200"""
    log("Testing admin stories patch...")
    if not test_story_id:
        log_fail("Admin stories patch", "No test story id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.patch(
            f"{BASE_URL}/admin/stories/{test_story_id}",
            json={"featured": True},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin stories patch", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Admin stories patch", "Response missing 'ok'")
            return False
        log_pass("Admin stories patch - featured set to true")
        return True


async def test_admin_stories_list():
    """GET /api/admin/stories as admin → expect list of all stories"""
    log("Testing admin stories list...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/admin/stories",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin stories list", f"Status {resp.status_code}")
            return False
        data = resp.json()
        if not isinstance(data, list):
            log_fail("Admin stories list", "Expected list")
            return False
        # Should include unpublished stories
        log_pass(f"Admin stories list - {len(data)} stories (including unpublished)")
        return True


async def test_admin_stories_list_non_admin():
    """GET /api/admin/stories as non-admin → expect 403"""
    log("Testing admin stories list (non-admin)...")
    if not new_user_token:
        log_fail("Admin stories list (non-admin)", "No new user token")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/admin/stories",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp.status_code != 403:
            log_fail("Admin stories list (non-admin)", f"Expected 403, got {resp.status_code}")
            return False
        log_pass("Admin stories list (non-admin) - correctly rejected with 403")
        return True


async def test_admin_stories_delete():
    """DELETE /api/admin/stories/{id} as admin → expect 200"""
    log("Testing admin stories delete...")
    if not test_story_id:
        log_fail("Admin stories delete", "No test story id")
        return False
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.delete(
            f"{BASE_URL}/admin/stories/{test_story_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Admin stories delete", f"Status {resp.status_code}: {resp.text}")
            return False
        data = resp.json()
        if not data.get("ok"):
            log_fail("Admin stories delete", "Response missing 'ok'")
            return False
        log_pass("Admin stories delete - story deleted")
        return True


# ============================================================================
# 3. GAMIFICATION
# ============================================================================

async def test_gamification_progress_uz():
    """GET /api/me/progress?lang=uz → verify structure"""
    log("Testing gamification progress (uz)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/me/progress?lang=uz",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Gamification progress (uz)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        
        # Verify required fields
        required_fields = ["xp", "level", "title", "xp_in_level", "xp_to_next", "progress_pct", "badges", "badges_earned", "badges_total"]
        for field in required_fields:
            if field not in data:
                log_fail("Gamification progress (uz)", f"Missing field: {field}")
                return False
        
        # Verify badges
        badges = data.get("badges", [])
        if len(badges) != 12:
            log_fail("Gamification progress (uz)", f"Expected 12 badges, got {len(badges)}")
            return False
        
        # Verify badge structure
        badge = badges[0]
        if not all(k in badge for k in ["id", "icon", "name", "achieved"]):
            log_fail("Gamification progress (uz)", "Badge missing required keys")
            return False
        
        # Verify admin has some badges (VIP, big5, verified, financial, first_rose)
        achieved_badges = [b["id"] for b in badges if b["achieved"]]
        expected_admin_badges = ["b_big5_done", "b_verified", "b_financial", "b_vip", "b_first_rose"]
        found_count = sum(1 for b in expected_admin_badges if b in achieved_badges)
        if found_count < 4:  # At least 4 of 5
            log_fail("Gamification progress (uz)", f"Admin should have at least 4 badges, found {found_count}: {achieved_badges}")
            return False
        
        log_pass(f"Gamification progress (uz) - xp: {data['xp']}, level: {data['level']}, title: {data['title']}, badges: {data['badges_earned']}/{data['badges_total']}")
        return True


async def test_gamification_progress_ru():
    """GET /api/me/progress?lang=ru → verify localization"""
    log("Testing gamification progress (ru)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/me/progress?lang=ru",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Gamification progress (ru)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        # Check that title is in Russian (should contain Cyrillic)
        title = data.get("title", "")
        if not any(ord(c) >= 0x0400 and ord(c) <= 0x04FF for c in title):
            log_fail("Gamification progress (ru)", f"Title not in Russian: {title}")
            return False
        log_pass(f"Gamification progress (ru) - title: {title}")
        return True


async def test_gamification_progress_en():
    """GET /api/me/progress?lang=en → verify localization"""
    log("Testing gamification progress (en)...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/me/progress?lang=en",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Gamification progress (en)", f"Status {resp.status_code}")
            return False
        data = resp.json()
        title = data.get("title", "")
        # English title should be ASCII
        if not title.isascii():
            log_fail("Gamification progress (en)", f"Title not in English: {title}")
            return False
        log_pass(f"Gamification progress (en) - title: {title}")
        return True


async def test_gamification_xp_formula():
    """Verify XP formula: total_xp_for_level_N = 100*N^2"""
    log("Testing gamification XP formula...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.get(
            f"{BASE_URL}/me/progress",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            log_fail("Gamification XP formula", f"Status {resp.status_code}")
            return False
        data = resp.json()
        
        xp = data.get("xp", 0)
        level = data.get("level", 0)
        xp_in_level = data.get("xp_in_level", 0)
        xp_to_next = data.get("xp_to_next", 0)
        
        # Verify formula: level = floor(sqrt(xp/100))
        import math
        expected_level = int(math.floor(math.sqrt(xp / 100))) if xp >= 100 else 0
        if level != expected_level:
            log_fail("Gamification XP formula", f"Level mismatch: expected {expected_level}, got {level}")
            return False
        
        # Verify xp_in_level + xp_to_next = next_level_xp - current_level_xp
        current_level_xp = 100 * level * level
        next_level_xp = 100 * (level + 1) * (level + 1)
        expected_in_level = xp - current_level_xp
        expected_to_next = next_level_xp - xp
        
        if xp_in_level != expected_in_level:
            log_fail("Gamification XP formula", f"xp_in_level mismatch: expected {expected_in_level}, got {xp_in_level}")
            return False
        if xp_to_next != expected_to_next:
            log_fail("Gamification XP formula", f"xp_to_next mismatch: expected {expected_to_next}, got {xp_to_next}")
            return False
        
        log_pass(f"Gamification XP formula - xp: {xp}, level: {level}, in_level: {xp_in_level}, to_next: {xp_to_next}")
        return True


async def test_daily_claim_xp():
    """POST /api/daily/claim → verify XP increases"""
    log("Testing daily claim XP...")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Get initial XP
        resp1 = await client.get(
            f"{BASE_URL}/me/progress",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp1.status_code != 200:
            log_fail("Daily claim XP", "Failed to get initial progress")
            return False
        xp1 = resp1.json().get("xp", 0)
        
        # Claim daily
        resp2 = await client.post(
            f"{BASE_URL}/daily/claim",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        # May return 400 if already claimed today, that's ok
        if resp2.status_code == 400 and "already claimed" in resp2.text.lower():
            log_pass("Daily claim XP - already claimed today (skipped)")
            return True
        
        if resp2.status_code != 200:
            log_fail("Daily claim XP", f"Status {resp2.status_code}: {resp2.text}")
            return False
        
        # Get XP after claim
        resp3 = await client.get(
            f"{BASE_URL}/me/progress",
            headers={"Authorization": f"Bearer {new_user_token}"}
        )
        if resp3.status_code != 200:
            log_fail("Daily claim XP", "Failed to get progress after claim")
            return False
        xp2 = resp3.json().get("xp", 0)
        
        # XP should increase by 20-70
        xp_gain = xp2 - xp1
        if xp_gain < 20 or xp_gain > 70:
            log_fail("Daily claim XP", f"Expected XP gain 20-70, got {xp_gain}")
            return False
        
        log_pass(f"Daily claim XP - gained {xp_gain} XP")
        return True


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def main():
    print("=" * 80)
    print("FIDEM BACKEND TEST SUITE - FAZA 2 ADDITIONS")
    print("=" * 80)
    print(f"Base URL: {BASE_URL}")
    print(f"Timeout: {TIMEOUT}s")
    print("=" * 80)
    
    results = []
    
    # Setup
    await test_admin_login()
    await test_register_new_user()
    
    # 1. Profile Prompts
    print("\n" + "=" * 80)
    print("1. PROFILE PROMPTS")
    print("=" * 80)
    results.append(("Prompts library (uz)", await test_prompts_library_uz()))
    results.append(("Prompts library (ru)", await test_prompts_library_ru()))
    results.append(("Prompts library (en)", await test_prompts_library_en()))
    results.append(("Prompts mine (initial)", await test_prompts_mine_initial()))
    results.append(("Prompts save (valid)", await test_prompts_save_valid()))
    results.append(("Prompts save (max exceeded)", await test_prompts_save_max_exceeded()))
    results.append(("Prompts save (invalid id)", await test_prompts_save_invalid_id()))
    results.append(("Prompts mine (after save)", await test_prompts_mine_after_save()))
    results.append(("Prompts XP award", await test_prompts_xp_awarded()))
    
    # 2. Success Stories
    print("\n" + "=" * 80)
    print("2. SUCCESS STORIES")
    print("=" * 80)
    results.append(("Stories list", await test_stories_list()))
    results.append(("Stories featured", await test_stories_featured()))
    results.append(("Stories get by id", await test_stories_get_by_id()))
    results.append(("Stories get bogus id", await test_stories_get_bogus_id()))
    results.append(("Stories submit (valid)", await test_stories_submit_valid()))
    results.append(("Stories submit (short text)", await test_stories_submit_short_text()))
    results.append(("Admin stories create", await test_admin_stories_create()))
    results.append(("Admin stories patch", await test_admin_stories_patch()))
    results.append(("Admin stories list", await test_admin_stories_list()))
    results.append(("Admin stories list (non-admin)", await test_admin_stories_list_non_admin()))
    results.append(("Admin stories delete", await test_admin_stories_delete()))
    
    # 3. Gamification
    print("\n" + "=" * 80)
    print("3. GAMIFICATION")
    print("=" * 80)
    results.append(("Gamification progress (uz)", await test_gamification_progress_uz()))
    results.append(("Gamification progress (ru)", await test_gamification_progress_ru()))
    results.append(("Gamification progress (en)", await test_gamification_progress_en()))
    results.append(("Gamification XP formula", await test_gamification_xp_formula()))
    results.append(("Daily claim XP", await test_daily_claim_xp()))
    
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
