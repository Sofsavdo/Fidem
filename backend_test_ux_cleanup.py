#!/usr/bin/env python3
"""
Backend testing for FIDEM UX cleanup sprint
Tests the unified referral endpoint and candidates district filter
"""

import requests
import json
from typing import Dict, Any

# Base URL from frontend/.env
BASE_URL = "https://93687cfe-abc0-46fa-a8bb-a682c4e9ffaf.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

def print_test(name: str):
    """Print test name"""
    print(f"\n{'='*80}")
    print(f"TEST: {name}")
    print('='*80)

def print_result(passed: bool, message: str):
    """Print test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {message}")

def print_response(response: requests.Response):
    """Print response details"""
    print(f"Status: {response.status_code}")
    try:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Response text: {response.text[:500]}")

def login_admin() -> str:
    """Login as admin and return token"""
    print_test("Admin Login")
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("token")
        is_admin = data.get("is_admin")
        print_result(True, f"Admin login successful, is_admin={is_admin}")
        return token
    else:
        print_result(False, "Admin login failed")
        return None

def test_referral_mine(token: str):
    """Test GET /api/referral/mine - unified endpoint with ALL fields"""
    print_test("GET /api/referral/mine - Unified Referral Endpoint")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/referral/mine", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    
    # Check all required fields
    required_fields = {
        "code": str,
        "link": str,
        "invited_count": int,
        "invites_count": int,  # alias
        "invited": int,  # legacy alias
        "bonus_per_invite": int,
        "earned": int,
        "vip_bonus_threshold": int,
        "redeemed_weeks": int,
        "available_weeks": int,
        "next_milestone": int,
        "premium_per_milestone_days": int
    }
    
    all_passed = True
    
    for field, expected_type in required_fields.items():
        if field not in data:
            print_result(False, f"Missing field: {field}")
            all_passed = False
        elif not isinstance(data[field], expected_type):
            print_result(False, f"Field {field} has wrong type: expected {expected_type.__name__}, got {type(data[field]).__name__}")
            all_passed = False
        else:
            print_result(True, f"Field {field} = {data[field]} ({expected_type.__name__})")
    
    # Validate specific values
    if data.get("code") and len(data["code"]) != 8:
        print_result(False, f"code should be 8 characters, got {len(data['code'])}")
        all_passed = False
    
    if data.get("link") and not data["link"].startswith("https://t.me/"):
        print_result(False, f"link should start with 'https://t.me/', got {data['link']}")
        all_passed = False
    
    if data.get("bonus_per_invite") != 10000:
        print_result(False, f"bonus_per_invite should be 10000, got {data.get('bonus_per_invite')}")
        all_passed = False
    
    if data.get("vip_bonus_threshold") != 5:
        print_result(False, f"vip_bonus_threshold should be 5, got {data.get('vip_bonus_threshold')}")
        all_passed = False
    
    if data.get("premium_per_milestone_days") != 7:
        print_result(False, f"premium_per_milestone_days should be 7, got {data.get('premium_per_milestone_days')}")
        all_passed = False
    
    # Check aliases match
    if data.get("invited_count") != data.get("invites_count"):
        print_result(False, f"invites_count alias doesn't match invited_count: {data.get('invites_count')} != {data.get('invited_count')}")
        all_passed = False
    
    if data.get("invited_count") != data.get("invited"):
        print_result(False, f"invited alias doesn't match invited_count: {data.get('invited')} != {data.get('invited_count')}")
        all_passed = False
    
    # Check earned calculation
    expected_earned = data.get("invited_count", 0) * 10000
    if data.get("earned") != expected_earned:
        print_result(False, f"earned should be {expected_earned}, got {data.get('earned')}")
        all_passed = False
    
    # Check available_weeks calculation (should be max(0, invited_count//3 - redeemed_weeks))
    expected_available = max(0, data.get("invited_count", 0) // 3 - data.get("redeemed_weeks", 0))
    if data.get("available_weeks") != expected_available:
        print_result(False, f"available_weeks should be {expected_available}, got {data.get('available_weeks')}")
        all_passed = False
    
    # Check non-negative values
    for field in ["invited_count", "redeemed_weeks", "available_weeks", "next_milestone"]:
        if data.get(field, -1) < 0:
            print_result(False, f"{field} should be >= 0, got {data.get(field)}")
            all_passed = False
    
    if all_passed:
        print_result(True, "All fields present with correct types and values")
    
    return all_passed

def test_candidates_baseline(token: str):
    """Test GET /api/candidates baseline (no filters)"""
    print_test("GET /api/candidates - Baseline (no filters)")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/candidates", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print_result(False, f"Expected list, got {type(data)}")
        return False
    
    print_result(True, f"Baseline candidates returned: {len(data)} candidates")
    return True

def test_candidates_region_filter(token: str):
    """Test GET /api/candidates?region=Toshkent"""
    print_test("GET /api/candidates?region=Toshkent")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/candidates?region=Toshkent", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print_result(False, f"Expected list, got {type(data)}")
        return False
    
    # Check all items have region=Toshkent
    all_correct = True
    for item in data:
        if item.get("region") != "Toshkent":
            print_result(False, f"Candidate {item.get('id')} has region={item.get('region')}, expected Toshkent")
            all_correct = False
    
    if all_correct:
        print_result(True, f"All {len(data)} candidates have region=Toshkent")
    
    return all_correct

def test_candidates_district_filter(token: str):
    """Test GET /api/candidates?region=Toshkent&district=Yunusobod"""
    print_test("GET /api/candidates?region=Toshkent&district=Yunusobod")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/candidates?region=Toshkent&district=Yunusobod", headers=headers)
    print_response(response)
    
    if response.status_code not in [200]:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if not isinstance(data, list):
        print_result(False, f"Expected list, got {type(data)}")
        return False
    
    # May return empty list (no seed data has district), but should NOT return 500/422
    print_result(True, f"District filter accepted, returned {len(data)} candidates (may be empty if no seed data)")
    
    return True

def test_regression_health(token: str):
    """Test GET /api/ - health check"""
    print_test("Regression: GET /api/ - Health Check")
    
    response = requests.get(f"{BASE_URL}/")
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if data.get("status") != "ok" or data.get("service") != "fidem":
        print_result(False, f"Expected {{status:ok, service:fidem}}, got {data}")
        return False
    
    print_result(True, "Health check passed")
    return True

def test_regression_auth_me(token: str):
    """Test GET /api/auth/me"""
    print_test("Regression: GET /api/auth/me")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    required_fields = ["email", "coins", "balance", "plan"]
    all_present = all(field in data for field in required_fields)
    
    if not all_present:
        missing = [f for f in required_fields if f not in data]
        print_result(False, f"Missing fields: {missing}")
        return False
    
    print_result(True, f"User data returned with email={data.get('email')}, coins={data.get('coins')}, balance={data.get('balance')}, plan={data.get('plan')}")
    return True

def test_regression_report_message(token: str):
    """Test POST /api/messages/report"""
    print_test("Regression: POST /api/messages/report")
    
    # First get a candidate to report
    headers = {"Authorization": f"Bearer {token}"}
    candidates_response = requests.get(f"{BASE_URL}/candidates", headers=headers)
    
    if candidates_response.status_code != 200 or not candidates_response.json():
        print_result(False, "Cannot get candidates for report test")
        return False
    
    candidate_id = candidates_response.json()[0].get("id")
    
    # Now report
    response = requests.post(
        f"{BASE_URL}/messages/report",
        headers=headers,
        json={"user_id": candidate_id, "reason": "test"}
    )
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    print_result(True, f"Report submitted successfully for user {candidate_id}")
    return True

def test_regression_invites_status(token: str):
    """Test GET /api/invites/status - legacy endpoint"""
    print_test("Regression: GET /api/invites/status (legacy)")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/invites/status", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    required_fields = ["code", "link", "invited", "available_weeks"]
    all_present = all(field in data for field in required_fields)
    
    if not all_present:
        missing = [f for f in required_fields if f not in data]
        print_result(False, f"Missing fields: {missing}")
        return False
    
    print_result(True, "Legacy invites/status endpoint still works")
    return True

def test_regression_invites_redeem(token: str):
    """Test POST /api/invites/redeem - should return 400 if no available weeks"""
    print_test("Regression: POST /api/invites/redeem")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # First check available_weeks
    status_response = requests.get(f"{BASE_URL}/invites/status", headers=headers)
    if status_response.status_code == 200:
        available_weeks = status_response.json().get("available_weeks", 0)
        print(f"Available weeks: {available_weeks}")
    
    response = requests.post(f"{BASE_URL}/invites/redeem", headers=headers, json={})
    print_response(response)
    
    # If available_weeks == 0, should return 400
    # If available_weeks > 0, should return 200
    # Either way, endpoint should work
    if response.status_code in [200, 400]:
        if response.status_code == 400:
            data = response.json()
            if "Not enough invites" in data.get("detail", "") or "yetarli emas" in data.get("detail", "").lower():
                print_result(True, "Correctly rejected redemption when no available weeks")
            else:
                print_result(True, f"Redemption returned 400: {data.get('detail')}")
        else:
            print_result(True, "Redemption successful (had available weeks)")
        return True
    else:
        print_result(False, f"Expected 200 or 400, got {response.status_code}")
        return False

def test_regression_travel_status(token: str):
    """Test GET /api/travel/status"""
    print_test("Regression: GET /api/travel/status")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/travel/status", headers=headers)
    print_response(response)
    
    if response.status_code != 200:
        print_result(False, f"Expected 200, got {response.status_code}")
        return False
    
    data = response.json()
    if "regions" not in data:
        print_result(False, "Missing 'regions' field")
        return False
    
    regions = data.get("regions", [])
    if len(regions) != 13:
        print_result(False, f"Expected 13 UZ regions, got {len(regions)}")
        return False
    
    print_result(True, f"Travel status returned with {len(regions)} regions")
    return True

def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("FIDEM UX CLEANUP SPRINT - BACKEND TESTING")
    print("="*80)
    
    # Login
    token = login_admin()
    if not token:
        print("\n❌ CRITICAL: Cannot proceed without admin token")
        return
    
    results = {}
    
    # Test 1: Unified referral endpoint
    results["referral_mine"] = test_referral_mine(token)
    
    # Test 2: Candidates filters
    results["candidates_baseline"] = test_candidates_baseline(token)
    results["candidates_region"] = test_candidates_region_filter(token)
    results["candidates_district"] = test_candidates_district_filter(token)
    
    # Test 3: Regression tests
    results["health"] = test_regression_health(token)
    results["auth_me"] = test_regression_auth_me(token)
    results["report"] = test_regression_report_message(token)
    results["invites_status"] = test_regression_invites_status(token)
    results["invites_redeem"] = test_regression_invites_redeem(token)
    results["travel_status"] = test_regression_travel_status(token)
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
