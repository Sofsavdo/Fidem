#!/usr/bin/env python3
"""
Backend test for: Global country/region + religion optional — OnboardingProfile model relaxed
Test scenarios:
1. Admin login regression
2. Health regression
3. Register fresh user A
4. Minimal Kyrgyzstan onboard (religion="")
5. GET /api/auth/me for user A (verify country, region, religion)
6. Religion optional regression (PATCH religion="")
7. PATCH search_country
8. Existing demos still loadable (GET /api/candidates)
9. Reject onboard without country
10. Reject onboard without name
"""

import requests
import random
import sys
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://a4ce9824-c731-4cee-aea8-08b0ccd714e3.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Test results
results = []

def log_test(test_num, description, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({
        "test": test_num,
        "description": description,
        "passed": passed,
        "details": details
    })
    print(f"\n{'='*80}")
    print(f"Test {test_num}: {description}")
    print(f"Status: {status}")
    if details:
        print(f"Details: {details}")
    print(f"{'='*80}")

def test_1_admin_login():
    """Test 1: Admin login regression"""
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }, timeout=10)
        
        if resp.status_code != 200:
            log_test(1, "Admin login regression", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return None
        
        data = resp.json()
        if not data.get("token"):
            log_test(1, "Admin login regression", False, "No token in response")
            return None
        
        if not data.get("is_admin"):
            log_test(1, "Admin login regression", False, "is_admin is not true")
            return None
        
        log_test(1, "Admin login regression", True, f"Token received, is_admin={data.get('is_admin')}")
        return data["token"]
    except Exception as e:
        log_test(1, "Admin login regression", False, f"Exception: {str(e)}")
        return None

def test_2_health():
    """Test 2: Health regression"""
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        
        if resp.status_code != 200:
            log_test(2, "Health regression", False, f"Expected 200, got {resp.status_code}")
            return False
        
        data = resp.json()
        if data.get("status") != "ok":
            log_test(2, "Health regression", False, f"Expected status=ok, got {data}")
            return False
        
        log_test(2, "Health regression", True, f"Response: {data}")
        return True
    except Exception as e:
        log_test(2, "Health regression", False, f"Exception: {str(e)}")
        return False

def test_3_register_user_a():
    """Test 3: Register fresh user A"""
    try:
        # Generate unique email with real TLD
        timestamp = int(datetime.now().timestamp())
        email = f"test_kg_{timestamp}@gmail.com"
        
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test KG",
            "email": email,
            "password": "Test@1234"
        }, timeout=10)
        
        if resp.status_code != 200:
            log_test(3, "Register fresh user A", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return None, None
        
        data = resp.json()
        if not data.get("token"):
            log_test(3, "Register fresh user A", False, "No token in response")
            return None, None
        
        if data.get("onboarded") != False:
            log_test(3, "Register fresh user A", False, f"Expected onboarded=false, got {data.get('onboarded')}")
            return None, None
        
        log_test(3, "Register fresh user A", True, f"User registered: {email}, token received, onboarded=false")
        return data["token"], email
    except Exception as e:
        log_test(3, "Register fresh user A", False, f"Exception: {str(e)}")
        return None, None

def test_4_minimal_kyrgyzstan_onboard(token):
    """Test 4: Minimal Kyrgyzstan onboard with religion=''"""
    try:
        # Minimal payload - many optional fields omitted
        payload = {
            "gender": "male",
            "birth_date": "1995-06-15",
            "country": "Kyrgyzstan",
            "region": "Bishkek",
            "marital_status": "single",
            "has_children": False,
            "children_count": 0,
            "height_cm": 178,
            "weight_kg": 75,
            "name": "Test KG",
            "search_gender": "female",
            "search_age_min": 22,
            "search_age_max": 35,
            "photo_url": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=600&q=80&auto=format&fit=crop",
            "religion": ""
        }
        
        resp = requests.post(f"{BASE_URL}/profile/onboard", 
                           json=payload,
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=15)
        
        # If photo verification fails with no_face, try alternative photo
        if resp.status_code == 400 and "photo_invalid:no_face" in resp.text:
            print("First photo rejected, trying alternative portrait...")
            payload["photo_url"] = "https://images.unsplash.com/photo-1547425260-76bcadfb4f2c?w=600&q=80&auto=format&fit=crop"
            resp = requests.post(f"{BASE_URL}/profile/onboard", 
                               json=payload,
                               headers={"Authorization": f"Bearer {token}"},
                               timeout=15)
        
        if resp.status_code != 200:
            log_test(4, "Minimal Kyrgyzstan onboard", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_test(4, "Minimal Kyrgyzstan onboard", False, f"Expected ok=true, got {data}")
            return False
        
        if "completeness" not in data:
            log_test(4, "Minimal Kyrgyzstan onboard", False, "No completeness in response")
            return False
        
        log_test(4, "Minimal Kyrgyzstan onboard", True, f"Onboarding successful, completeness={data.get('completeness')}")
        return True
    except Exception as e:
        log_test(4, "Minimal Kyrgyzstan onboard", False, f"Exception: {str(e)}")
        return False

def test_5_get_me_user_a(token):
    """Test 5: GET /api/auth/me for user A - verify country, region, religion"""
    try:
        resp = requests.get(f"{BASE_URL}/auth/me",
                          headers={"Authorization": f"Bearer {token}"},
                          timeout=10)
        
        if resp.status_code != 200:
            log_test(5, "GET /api/auth/me for user A", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        
        # Verify required fields
        checks = []
        
        if data.get("country") != "Kyrgyzstan":
            checks.append(f"country={data.get('country')} (expected Kyrgyzstan)")
        
        if data.get("region") != "Bishkek":
            checks.append(f"region={data.get('region')} (expected Bishkek)")
        
        # Religion should be empty string (not None, not missing)
        if "religion" not in data:
            checks.append("religion field missing")
        elif data.get("religion") != "":
            checks.append(f"religion={repr(data.get('religion'))} (expected empty string)")
        
        if data.get("onboarded") != True:
            checks.append(f"onboarded={data.get('onboarded')} (expected true)")
        
        # search_country and search_region may be present (can be "" or have values)
        if "search_country" not in data:
            checks.append("search_country field missing")
        
        if checks:
            log_test(5, "GET /api/auth/me for user A", False, f"Validation failed: {', '.join(checks)}")
            return False
        
        log_test(5, "GET /api/auth/me for user A", True, 
                f"country={data.get('country')}, region={data.get('region')}, religion={repr(data.get('religion'))}, "
                f"onboarded={data.get('onboarded')}, search_country={repr(data.get('search_country'))}, "
                f"search_region={repr(data.get('search_region'))}")
        return True
    except Exception as e:
        log_test(5, "GET /api/auth/me for user A", False, f"Exception: {str(e)}")
        return False

def test_6_religion_optional_patch(token):
    """Test 6: Religion optional regression - PATCH religion=''"""
    try:
        # PATCH with religion=""
        resp = requests.patch(f"{BASE_URL}/profile",
                            json={"religion": ""},
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        
        if resp.status_code != 200:
            log_test(6, "Religion optional PATCH", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not data.get("ok"):
            log_test(6, "Religion optional PATCH", False, f"Expected ok=true, got {data}")
            return False
        
        # Verify with GET /api/auth/me
        resp2 = requests.get(f"{BASE_URL}/auth/me",
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=10)
        
        if resp2.status_code != 200:
            log_test(6, "Religion optional PATCH", False, f"GET /auth/me failed: {resp2.status_code}")
            return False
        
        me_data = resp2.json()
        if me_data.get("religion") != "":
            log_test(6, "Religion optional PATCH", False, f"religion={repr(me_data.get('religion'))} (expected empty string)")
            return False
        
        log_test(6, "Religion optional PATCH", True, "PATCH successful, religion remains empty string")
        return True
    except Exception as e:
        log_test(6, "Religion optional PATCH", False, f"Exception: {str(e)}")
        return False

def test_7_patch_search_country(token):
    """Test 7: PATCH search_country and country"""
    try:
        # PATCH with new country and search_country
        resp = requests.patch(f"{BASE_URL}/profile",
                            json={
                                "country": "Turkey",
                                "region": "Istanbul",
                                "search_country": "Turkey",
                                "search_region": "Istanbul"
                            },
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        
        if resp.status_code != 200:
            log_test(7, "PATCH search_country", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return False
        
        # Verify with GET /api/auth/me
        resp2 = requests.get(f"{BASE_URL}/auth/me",
                           headers={"Authorization": f"Bearer {token}"},
                           timeout=10)
        
        if resp2.status_code != 200:
            log_test(7, "PATCH search_country", False, f"GET /auth/me failed: {resp2.status_code}")
            return False
        
        data = resp2.json()
        checks = []
        
        if data.get("country") != "Turkey":
            checks.append(f"country={data.get('country')} (expected Turkey)")
        
        if data.get("region") != "Istanbul":
            checks.append(f"region={data.get('region')} (expected Istanbul)")
        
        if data.get("search_country") != "Turkey":
            checks.append(f"search_country={data.get('search_country')} (expected Turkey)")
        
        if data.get("search_region") != "Istanbul":
            checks.append(f"search_region={data.get('search_region')} (expected Istanbul)")
        
        if checks:
            log_test(7, "PATCH search_country", False, f"Validation failed: {', '.join(checks)}")
            return False
        
        log_test(7, "PATCH search_country", True, 
                f"country={data.get('country')}, region={data.get('region')}, "
                f"search_country={data.get('search_country')}, search_region={data.get('search_region')}")
        return True
    except Exception as e:
        log_test(7, "PATCH search_country", False, f"Exception: {str(e)}")
        return False

def test_8_existing_demos_loadable(admin_token):
    """Test 8: Existing demos still loadable - GET /api/candidates"""
    try:
        resp = requests.get(f"{BASE_URL}/candidates",
                          headers={"Authorization": f"Bearer {admin_token}"},
                          timeout=10)
        
        if resp.status_code != 200:
            log_test(8, "Existing demos loadable", False, f"Expected 200, got {resp.status_code}: {resp.text}")
            return False
        
        data = resp.json()
        if not isinstance(data, list):
            log_test(8, "Existing demos loadable", False, f"Expected list, got {type(data)}")
            return False
        
        # Should have ~8 seeded Uzbek users
        if len(data) < 5:
            log_test(8, "Existing demos loadable", False, f"Expected ~8 candidates, got {len(data)}")
            return False
        
        # Verify UserPublic doesn't crash on missing fields
        for candidate in data:
            if "id" not in candidate or "name" not in candidate:
                log_test(8, "Existing demos loadable", False, f"Missing required fields in candidate: {candidate}")
                return False
        
        log_test(8, "Existing demos loadable", True, f"Loaded {len(data)} candidates successfully")
        return True
    except Exception as e:
        log_test(8, "Existing demos loadable", False, f"Exception: {str(e)}")
        return False

def test_9_reject_onboard_without_country():
    """Test 9: Reject onboard without country"""
    try:
        # Register new user
        timestamp = int(datetime.now().timestamp())
        email = f"test_no_country_{timestamp}@gmail.com"
        
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test No Country",
            "email": email,
            "password": "Test@1234"
        }, timeout=10)
        
        if resp.status_code != 200:
            log_test(9, "Reject onboard without country", False, f"Registration failed: {resp.status_code}")
            return False
        
        token = resp.json().get("token")
        
        # Try to onboard WITHOUT country field
        payload = {
            "gender": "female",
            "birth_date": "1998-03-20",
            # "country": "Kyrgyzstan",  # OMITTED
            "region": "Bishkek",
            "marital_status": "single",
            "has_children": False,
            "height_cm": 165,
            "weight_kg": 55,
            "name": "Test No Country",
            "search_gender": "male",
            "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&q=80",
            "religion": ""
        }
        
        resp2 = requests.post(f"{BASE_URL}/profile/onboard",
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        
        # Should get 422 validation error
        if resp2.status_code != 422:
            log_test(9, "Reject onboard without country", False, 
                    f"Expected 422, got {resp2.status_code}: {resp2.text}")
            return False
        
        log_test(9, "Reject onboard without country", True, f"Correctly rejected with 422: {resp2.text}")
        return True
    except Exception as e:
        log_test(9, "Reject onboard without country", False, f"Exception: {str(e)}")
        return False

def test_10_reject_onboard_without_name():
    """Test 10: Reject onboard without name"""
    try:
        # Register new user
        timestamp = int(datetime.now().timestamp())
        email = f"test_no_name_{timestamp}@gmail.com"
        
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": "Test No Name",
            "email": email,
            "password": "Test@1234"
        }, timeout=10)
        
        if resp.status_code != 200:
            log_test(10, "Reject onboard without name", False, f"Registration failed: {resp.status_code}")
            return False
        
        token = resp.json().get("token")
        
        # Try to onboard WITHOUT name field
        payload = {
            "gender": "female",
            "birth_date": "1998-03-20",
            "country": "Kyrgyzstan",
            "region": "Bishkek",
            "marital_status": "single",
            "has_children": False,
            "height_cm": 165,
            "weight_kg": 55,
            # "name": "Test No Name",  # OMITTED
            "search_gender": "male",
            "photo_url": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=600&q=80",
            "religion": ""
        }
        
        resp2 = requests.post(f"{BASE_URL}/profile/onboard",
                            json=payload,
                            headers={"Authorization": f"Bearer {token}"},
                            timeout=10)
        
        # Should get 422 validation error
        if resp2.status_code != 422:
            log_test(10, "Reject onboard without name", False, 
                    f"Expected 422, got {resp2.status_code}: {resp2.text}")
            return False
        
        log_test(10, "Reject onboard without name", True, f"Correctly rejected with 422: {resp2.text}")
        return True
    except Exception as e:
        log_test(10, "Reject onboard without name", False, f"Exception: {str(e)}")
        return False

def main():
    print("="*80)
    print("BACKEND TEST: Global country/region + religion optional")
    print("="*80)
    
    # Test 1: Admin login
    admin_token = test_1_admin_login()
    if not admin_token:
        print("\n❌ CRITICAL: Admin login failed, cannot continue")
        sys.exit(1)
    
    # Test 2: Health check
    test_2_health()
    
    # Test 3: Register user A
    user_a_token, user_a_email = test_3_register_user_a()
    if not user_a_token:
        print("\n❌ CRITICAL: User registration failed, cannot continue")
        sys.exit(1)
    
    # Test 4: Minimal Kyrgyzstan onboard
    onboard_success = test_4_minimal_kyrgyzstan_onboard(user_a_token)
    if not onboard_success:
        print("\n⚠️ WARNING: Onboarding failed, some tests may be skipped")
    
    # Test 5: GET /api/auth/me for user A
    if onboard_success:
        test_5_get_me_user_a(user_a_token)
    
    # Test 6: Religion optional PATCH
    if onboard_success:
        test_6_religion_optional_patch(user_a_token)
    
    # Test 7: PATCH search_country
    if onboard_success:
        test_7_patch_search_country(user_a_token)
    
    # Test 8: Existing demos loadable
    test_8_existing_demos_loadable(admin_token)
    
    # Test 9: Reject onboard without country
    test_9_reject_onboard_without_country()
    
    # Test 10: Reject onboard without name
    test_10_reject_onboard_without_name()
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"{status} Test {r['test']}: {r['description']}")
    
    print(f"\n{'='*80}")
    print(f"TOTAL: {passed}/{total} tests passed")
    print(f"{'='*80}")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n⚠️ {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
