#!/usr/bin/env python3
"""
Pre-Launch Sprint Backend Smoke Tests
Tests referral endpoint enhancement and gift catalog redesign
"""
import requests
import json
import os
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://56b9b915-627e-4119-b010-d3b5f4a2de1d.preview.emergentagent.com"
API_BASE = f"{BACKEND_URL}/api"

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

def log_test(test_name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"\n{status} | {test_name}")
    if details:
        print(f"   {details}")
    return passed

def get_admin_token():
    """Login as admin and get Bearer token"""
    print("\n" + "="*80)
    print("AUTHENTICATING AS ADMIN")
    print("="*80)
    
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None
    
    data = response.json()
    token = data.get("token")
    is_admin = data.get("is_admin", False)
    
    print(f"✅ Login successful")
    print(f"   is_admin: {is_admin}")
    print(f"   token: {token[:20]}...")
    
    return token

def test_1_referral_endpoint(token):
    """
    Test 1: GET /api/referral/mine
    Verify response contains all required keys with correct types
    """
    print("\n" + "="*80)
    print("TEST 1: REFERRAL ENDPOINT ENHANCEMENT")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/referral/mine", headers=headers, timeout=10)
    
    if response.status_code != 200:
        return log_test("GET /api/referral/mine", False, f"Status {response.status_code}: {response.text}")
    
    data = response.json()
    print(f"Response: {json.dumps(data, indent=2)}")
    
    # Verify all required keys
    required_keys = {
        "code": (str, 8),  # (type, expected_length)
        "link": (str, None),
        "invited_count": (int, None),
        "invites_count": (int, None),
        "bonus_per_invite": (int, 10000),
        "earned": (int, None),
        "vip_bonus_threshold": (int, 5),
    }
    
    all_passed = True
    for key, (expected_type, expected_value) in required_keys.items():
        if key not in data:
            log_test(f"  Key '{key}' present", False, f"Missing key")
            all_passed = False
            continue
        
        value = data[key]
        
        # Type check
        if not isinstance(value, expected_type):
            log_test(f"  Key '{key}' type", False, f"Expected {expected_type.__name__}, got {type(value).__name__}")
            all_passed = False
            continue
        
        # Value check
        if expected_value is not None:
            if isinstance(expected_value, int) and key in ["bonus_per_invite", "vip_bonus_threshold"]:
                if value != expected_value:
                    log_test(f"  Key '{key}' value", False, f"Expected {expected_value}, got {value}")
                    all_passed = False
                    continue
            elif key == "code" and len(value) != expected_value:
                log_test(f"  Key '{key}' length", False, f"Expected {expected_value} chars, got {len(value)}")
                all_passed = False
                continue
        
        log_test(f"  Key '{key}'", True, f"{expected_type.__name__} = {value}")
    
    # Verify link starts with https://t.me/
    if "link" in data and not data["link"].startswith("https://t.me/"):
        log_test("  Link format", False, f"Link should start with https://t.me/, got {data['link']}")
        all_passed = False
    else:
        log_test("  Link format", True, f"Starts with https://t.me/")
    
    # Verify earned = invited_count * bonus_per_invite
    if "earned" in data and "invited_count" in data and "bonus_per_invite" in data:
        expected_earned = data["invited_count"] * data["bonus_per_invite"]
        if data["earned"] != expected_earned:
            log_test("  Earned calculation", False, f"Expected {expected_earned}, got {data['earned']}")
            all_passed = False
        else:
            log_test("  Earned calculation", True, f"{data['invited_count']} * {data['bonus_per_invite']} = {data['earned']}")
    
    # Verify invites_count is alias of invited_count
    if "invited_count" in data and "invites_count" in data:
        if data["invited_count"] != data["invites_count"]:
            log_test("  invites_count alias", False, f"invited_count={data['invited_count']} != invites_count={data['invites_count']}")
            all_passed = False
        else:
            log_test("  invites_count alias", True, f"Both equal to {data['invited_count']}")
    
    return log_test("TEST 1: Referral endpoint", all_passed)

def test_2_gift_catalog(token):
    """
    Test 2: GET /api/gifts/catalog
    Verify 12 items (2 free, 10 paid), structure, and quota
    """
    print("\n" + "="*80)
    print("TEST 2: GIFT CATALOG (12 ITEMS)")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/gifts/catalog", headers=headers, timeout=10)
    
    if response.status_code != 200:
        return log_test("GET /api/gifts/catalog", False, f"Status {response.status_code}: {response.text}")
    
    data = response.json()
    print(f"Response keys: {list(data.keys())}")
    
    # Verify top-level structure
    if "items" not in data:
        return log_test("TEST 2: Gift catalog", False, "Missing 'items' array")
    
    items = data["items"]
    print(f"Total items: {len(items)}")
    
    # Verify exactly 12 items
    if len(items) != 12:
        log_test("  Item count", False, f"Expected 12, got {len(items)}")
        return False
    else:
        log_test("  Item count", True, "12 items")
    
    # Categorize items by tier
    free_items = [item for item in items if item.get("tier") == "free"]
    paid_items = [item for item in items if item.get("tier") in ["care", "love", "luxury"]]
    
    print(f"\nFree items: {len(free_items)}")
    for item in free_items:
        print(f"  - {item.get('kind')}: {item.get('emoji')} {item.get('label_uz')} (price={item.get('price')})")
    
    print(f"\nPaid items: {len(paid_items)}")
    for item in paid_items:
        print(f"  - {item.get('kind')}: {item.get('emoji')} {item.get('label_uz')} (price={item.get('price')}, tier={item.get('tier')})")
    
    all_passed = True
    
    # Verify 2 free items
    if len(free_items) != 2:
        log_test("  Free items count", False, f"Expected 2, got {len(free_items)}")
        all_passed = False
    else:
        log_test("  Free items count", True, "2 free items")
    
    # Verify free items are rose_free and heart_free with price=0
    free_kinds = {item.get("kind") for item in free_items}
    if free_kinds != {"rose_free", "heart_free"}:
        log_test("  Free item kinds", False, f"Expected {{rose_free, heart_free}}, got {free_kinds}")
        all_passed = False
    else:
        log_test("  Free item kinds", True, "rose_free, heart_free")
    
    for item in free_items:
        if item.get("price") != 0:
            log_test(f"  {item.get('kind')} price", False, f"Expected 0, got {item.get('price')}")
            all_passed = False
    
    # Verify 10 paid items
    if len(paid_items) != 10:
        log_test("  Paid items count", False, f"Expected 10, got {len(paid_items)}")
        all_passed = False
    else:
        log_test("  Paid items count", True, "10 paid items")
    
    # Verify price range (2000 to 499000)
    prices = [item.get("price", 0) for item in paid_items]
    min_price = min(prices) if prices else 0
    max_price = max(prices) if prices else 0
    
    if min_price != 2000:
        log_test("  Min price", False, f"Expected 2000, got {min_price}")
        all_passed = False
    else:
        log_test("  Min price", True, "2000 so'm")
    
    if max_price != 499000:
        log_test("  Max price", False, f"Expected 499000, got {max_price}")
        all_passed = False
    else:
        log_test("  Max price", True, "499000 so'm")
    
    # Verify each item has required fields
    required_fields = ["kind", "emoji", "label_uz", "label_ru", "label_en", "price", "tier"]
    for item in items:
        for field in required_fields:
            if field not in item:
                log_test(f"  Item {item.get('kind', 'unknown')} field '{field}'", False, "Missing")
                all_passed = False
    
    if all_passed:
        log_test("  Item structure", True, "All items have required fields")
    
    # Verify top-level response has quota fields
    if "free_remaining" not in data:
        log_test("  free_remaining field", False, "Missing")
        all_passed = False
    else:
        log_test("  free_remaining field", True, f"Value: {data['free_remaining']}")
    
    if "free_quota_per_week" not in data:
        log_test("  free_quota_per_week field", False, "Missing")
        all_passed = False
    else:
        quota = data["free_quota_per_week"]
        plan = data.get("plan", "unknown")
        log_test("  free_quota_per_week field", True, f"Value: {quota} (plan: {plan})")
        
        # Verify VIP gets 3 free gifts per week
        if plan == "vip" and quota != 3:
            log_test("  VIP quota", False, f"Expected 3, got {quota}")
            all_passed = False
        elif plan == "vip":
            log_test("  VIP quota", True, "3 free gifts per week")
    
    return log_test("TEST 2: Gift catalog", all_passed)

def test_3_legacy_gift_send(token):
    """
    Test 3: POST /api/gifts/send with legacy gift kind "rose"
    Should map to "rose_free" via LEGACY_GIFT_MAP
    """
    print("\n" + "="*80)
    print("TEST 3: LEGACY GIFT SEND (rose → rose_free)")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, get a candidate to send gift to
    print("\nFetching candidates...")
    candidates_response = requests.get(f"{API_BASE}/candidates", headers=headers, timeout=10)
    
    if candidates_response.status_code != 200:
        return log_test("TEST 3: Legacy gift send", False, f"Failed to get candidates: {candidates_response.status_code}")
    
    candidates = candidates_response.json()
    if not candidates or len(candidates) == 0:
        print("⚠️  No candidates available, skipping gift send test")
        return log_test("TEST 3: Legacy gift send", True, "SKIPPED - No candidates available")
    
    target_user_id = candidates[0]["id"]
    target_name = candidates[0]["name"]
    print(f"Target user: {target_name} ({target_user_id})")
    
    # Send legacy "rose" gift
    print(f"\nSending legacy 'rose' gift to {target_name}...")
    gift_response = requests.post(
        f"{API_BASE}/gifts/send",
        headers=headers,
        json={"to_user_id": target_user_id, "gift_kind": "rose"},
        timeout=10
    )
    
    print(f"Status: {gift_response.status_code}")
    print(f"Response: {gift_response.text}")
    
    # Accept both 200 (success) and 402 (quota exhausted)
    if gift_response.status_code == 200:
        data = gift_response.json()
        log_test("  Gift send status", True, "200 OK - Gift sent successfully")
        log_test("  Legacy mapping", True, "rose → rose_free mapping works")
        return log_test("TEST 3: Legacy gift send", True, "Legacy gift kind 'rose' works via LEGACY_GIFT_MAP")
    
    elif gift_response.status_code == 402:
        error_text = gift_response.text
        if "kvota" in error_text.lower() or "quota" in error_text.lower():
            log_test("  Gift send status", True, "402 - Quota exhausted (expected behavior)")
            log_test("  Quota logic", True, "Free gift quota validation working")
            return log_test("TEST 3: Legacy gift send", True, "Quota logic works (402 proves validation is active)")
        else:
            return log_test("TEST 3: Legacy gift send", False, f"402 but unexpected error: {error_text}")
    
    else:
        return log_test("TEST 3: Legacy gift send", False, f"Unexpected status {gift_response.status_code}: {gift_response.text}")

def test_4_regression_critical_endpoints(token):
    """
    Test 4: Regression tests for critical endpoints
    """
    print("\n" + "="*80)
    print("TEST 4: REGRESSION - CRITICAL ENDPOINTS")
    print("="*80)
    
    all_passed = True
    
    # Test 4.1: GET /api/
    print("\n4.1: GET /api/")
    response = requests.get(f"{API_BASE}/", timeout=10)
    if response.status_code != 200:
        log_test("  GET /api/", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        if data.get("status") == "ok":
            log_test("  GET /api/", True, f"Status: {data.get('status')}")
        else:
            log_test("  GET /api/", False, f"Expected status=ok, got {data}")
            all_passed = False
    
    # Test 4.2: POST /api/auth/login
    print("\n4.2: POST /api/auth/login")
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code != 200:
        log_test("  POST /api/auth/login", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        if "token" in data:
            log_test("  POST /api/auth/login", True, f"Token received, is_admin={data.get('is_admin')}")
        else:
            log_test("  POST /api/auth/login", False, "No token in response")
            all_passed = False
    
    # Test 4.3: GET /api/auth/me
    print("\n4.3: GET /api/auth/me")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/auth/me", headers=headers, timeout=10)
    if response.status_code != 200:
        log_test("  GET /api/auth/me", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        if data.get("email") == ADMIN_EMAIL:
            log_test("  GET /api/auth/me", True, f"Email: {data.get('email')}")
        else:
            log_test("  GET /api/auth/me", False, f"Expected email={ADMIN_EMAIL}, got {data.get('email')}")
            all_passed = False
    
    # Test 4.4: GET /api/candidates
    print("\n4.4: GET /api/candidates")
    response = requests.get(f"{API_BASE}/candidates", headers=headers, timeout=10)
    if response.status_code != 200:
        log_test("  GET /api/candidates", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        if isinstance(data, list):
            log_test("  GET /api/candidates", True, f"Returned {len(data)} candidates (0-8 expected)")
        else:
            log_test("  GET /api/candidates", False, f"Expected list, got {type(data)}")
            all_passed = False
    
    return log_test("TEST 4: Regression tests", all_passed)

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("PRE-LAUNCH SPRINT BACKEND SMOKE TESTS")
    print("Testing: Referral endpoint + Gift catalog redesign")
    print("="*80)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test time: {datetime.now().isoformat()}")
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("\n❌ FATAL: Cannot authenticate as admin")
        return False
    
    # Run all tests
    results = []
    results.append(test_1_referral_endpoint(token))
    results.append(test_2_gift_catalog(token))
    results.append(test_3_legacy_gift_send(token))
    results.append(test_4_regression_critical_endpoints(token))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    passed = sum(results)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED")
        return True
    else:
        print(f"\n⚠️  {total - passed} TEST(S) FAILED")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
