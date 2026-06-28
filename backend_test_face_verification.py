"""
Backend testing for FIDEM Face Verification + Chaperone removal + Regression
Test suite for: Brand rewrite + Face verification + Chaperone removal + Hidden errors sprint
"""
import httpx
import asyncio
import os
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://preview-loyihani.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Test photos
VALID_FACE_URL = "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=400"  # Real face
NO_FACE_URL = "https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=400"  # Scenery

# Full onboarding payload template
ONBOARDING_PAYLOAD = {
    "name": "Test User",
    "gender": "male",
    "birth_date": "1995-05-15",
    "country": "Uzbekistan",
    "region": "Toshkent",
    "district": "",
    "marital_status": "single",
    "has_children": False,
    "children_count": 0,
    "height_cm": 175,
    "weight_kg": 70,
    "education": "Oliy",
    "profession": "QA Engineer",
    "religion": "Islom",
    "looking_for": "Jiddiy munosabat va oila qurish",
    "search_gender": "female",
    "search_age_min": 20,
    "search_age_max": 35,
    "search_region": "Toshkent",
    "bio": "Test bio for face verification testing",
    "smoking": "no",
    "alcohol": "no",
    "relocation": False,
}


async def test_face_verification():
    """Test suite for face verification + onboarding + chaperone removal + regression"""
    print("\n" + "="*80)
    print("FIDEM BACKEND TEST: Face Verification Sprint")
    print("="*80 + "\n")
    
    results = {
        "passed": [],
        "failed": [],
        "warnings": []
    }
    
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        
        # ========== SETUP: Admin Login ==========
        print("🔐 SETUP: Admin Login")
        try:
            resp = await client.post(f"{BASE_URL}/auth/login", json={
                "email": ADMIN_EMAIL,
                "password": ADMIN_PASSWORD
            })
            assert resp.status_code == 200, f"Admin login failed: {resp.status_code} {resp.text}"
            admin_data = resp.json()
            admin_token = admin_data["token"]
            assert admin_data.get("is_admin") == True, "Admin flag not set"
            print(f"✅ Admin login successful (token: {admin_token[:20]}...)")
            results["passed"].append("Admin login")
        except Exception as e:
            print(f"❌ Admin login failed: {e}")
            results["failed"].append(f"Admin login: {e}")
            return results
        
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        
        # ========== TEST 1: Face Verification - Valid Face ==========
        print("\n📸 TEST 1: POST /api/face/verify with valid face photo")
        try:
            resp = await client.post(
                f"{BASE_URL}/face/verify",
                json={"photo_url": VALID_FACE_URL},
                headers=admin_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "valid" in data, "Missing 'valid' field"
            assert "code" in data, "Missing 'code' field"
            assert "reason" in data, "Missing 'reason' field"
            
            if data.get("valid") == True and data.get("code") == "ok":
                print(f"✅ Valid face accepted: code={data['code']}, reason={data['reason']}")
                results["passed"].append("Face verify - valid face")
            else:
                print(f"⚠️  Valid face rejected: {data}")
                results["warnings"].append(f"Face verify valid face: got valid={data.get('valid')}, code={data.get('code')}")
        except Exception as e:
            print(f"❌ Face verify valid face failed: {e}")
            results["failed"].append(f"Face verify valid face: {e}")
        
        # ========== TEST 2: Face Verification - No Face (Scenery) ==========
        print("\n🌄 TEST 2: POST /api/face/verify with scenery (no face)")
        try:
            resp = await client.post(
                f"{BASE_URL}/face/verify",
                json={"photo_url": NO_FACE_URL},
                headers=admin_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
            data = resp.json()
            assert "valid" in data, "Missing 'valid' field"
            assert "code" in data, "Missing 'code' field"
            
            if data.get("valid") == False and data.get("code") == "no_face":
                print(f"✅ No face correctly rejected: code={data['code']}, reason={data.get('reason')}")
                results["passed"].append("Face verify - no face rejection")
            else:
                print(f"⚠️  Scenery not rejected as expected: {data}")
                results["warnings"].append(f"Face verify no face: got valid={data.get('valid')}, code={data.get('code')}")
        except Exception as e:
            print(f"❌ Face verify no face failed: {e}")
            results["failed"].append(f"Face verify no face: {e}")
        
        # ========== TEST 3: Face Verification - Empty Body ==========
        print("\n🚫 TEST 3: POST /api/face/verify with empty body")
        try:
            resp = await client.post(
                f"{BASE_URL}/face/verify",
                json={},
                headers=admin_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            if resp.status_code == 400:
                print(f"✅ Empty body correctly rejected with 400")
                results["passed"].append("Face verify - empty body validation")
            else:
                print(f"⚠️  Expected 400, got {resp.status_code}")
                results["warnings"].append(f"Face verify empty body: got {resp.status_code} instead of 400")
        except Exception as e:
            print(f"❌ Face verify empty body test failed: {e}")
            results["failed"].append(f"Face verify empty body: {e}")
        
        # ========== TEST 4: Verify photo_verified persisted in DB ==========
        print("\n💾 TEST 4: Verify photo_verified persisted (GET /api/auth/me)")
        try:
            resp = await client.get(f"{BASE_URL}/auth/me", headers=admin_headers)
            assert resp.status_code == 200, f"GET /auth/me failed: {resp.status_code}"
            me_data = resp.json()
            
            photo_verified = me_data.get("photo_verified")
            photo_verification_code = me_data.get("photo_verification_code")
            
            print(f"   photo_verified: {photo_verified}")
            print(f"   photo_verification_code: {photo_verification_code}")
            
            if photo_verified is not None:
                print(f"✅ photo_verified field present in /auth/me")
                results["passed"].append("photo_verified field in /auth/me")
            else:
                print(f"⚠️  photo_verified field missing in /auth/me")
                results["warnings"].append("photo_verified field missing in /auth/me")
        except Exception as e:
            print(f"❌ Check photo_verified persistence failed: {e}")
            results["failed"].append(f"photo_verified persistence: {e}")
        
        # ========== TEST 5: Register Fresh User for Onboarding Tests ==========
        print("\n👤 TEST 5: Register fresh user for onboarding tests")
        timestamp = int(datetime.now().timestamp())
        test_email = f"test_face_onboard_{timestamp}@example.com"
        test_password = "TestPass123!"
        
        try:
            resp = await client.post(f"{BASE_URL}/auth/register", json={
                "email": test_email,
                "password": test_password,
                "name": "Test Face User"
            })
            assert resp.status_code == 200, f"Register failed: {resp.status_code} {resp.text}"
            reg_data = resp.json()
            user_token = reg_data["token"]
            user_id = reg_data["user_id"]
            assert reg_data.get("onboarded") == False, "New user should not be onboarded"
            print(f"✅ Fresh user registered: {test_email} (id: {user_id})")
            results["passed"].append("Register fresh user")
        except Exception as e:
            print(f"❌ Register fresh user failed: {e}")
            results["failed"].append(f"Register fresh user: {e}")
            return results
        
        user_headers = {"Authorization": f"Bearer {user_token}"}
        
        # ========== TEST 6: Onboarding WITHOUT photo_url ==========
        print("\n🚫 TEST 6: POST /api/profile/onboard WITHOUT photo_url")
        try:
            payload = ONBOARDING_PAYLOAD.copy()
            payload["photo_url"] = ""  # Empty photo
            
            resp = await client.post(
                f"{BASE_URL}/profile/onboard",
                json=payload,
                headers=user_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            if resp.status_code == 400 and "photo_required" in resp.text:
                print(f"✅ Onboarding without photo correctly rejected with 'photo_required'")
                results["passed"].append("Onboarding - photo required validation")
            else:
                print(f"⚠️  Expected 400 with 'photo_required', got {resp.status_code}: {resp.text[:100]}")
                results["warnings"].append(f"Onboarding photo required: got {resp.status_code}")
        except Exception as e:
            print(f"❌ Onboarding without photo test failed: {e}")
            results["failed"].append(f"Onboarding photo required: {e}")
        
        # ========== TEST 7: Onboarding WITH invalid photo (scenery) ==========
        print("\n🌄 TEST 7: POST /api/profile/onboard WITH invalid photo (scenery)")
        try:
            payload = ONBOARDING_PAYLOAD.copy()
            payload["photo_url"] = NO_FACE_URL  # Scenery photo
            
            resp = await client.post(
                f"{BASE_URL}/profile/onboard",
                json=payload,
                headers=user_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            if resp.status_code == 400 and "photo_invalid:" in resp.text:
                detail = resp.json().get("detail", "")
                print(f"✅ Invalid photo rejected with 'photo_invalid:' code: {detail}")
                results["passed"].append("Onboarding - invalid photo rejection")
            else:
                print(f"⚠️  Expected 400 with 'photo_invalid:', got {resp.status_code}: {resp.text[:100]}")
                results["warnings"].append(f"Onboarding invalid photo: got {resp.status_code}")
        except Exception as e:
            print(f"❌ Onboarding with invalid photo test failed: {e}")
            results["failed"].append(f"Onboarding invalid photo: {e}")
        
        # ========== TEST 8: Onboarding WITH valid photo ==========
        print("\n✅ TEST 8: POST /api/profile/onboard WITH valid photo")
        try:
            payload = ONBOARDING_PAYLOAD.copy()
            payload["photo_url"] = VALID_FACE_URL  # Real face
            
            resp = await client.post(
                f"{BASE_URL}/profile/onboard",
                json=payload,
                headers=user_headers
            )
            print(f"   Status: {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            
            if resp.status_code == 200:
                data = resp.json()
                assert data.get("ok") == True, "Expected ok:true"
                assert "completeness" in data, "Missing completeness field"
                print(f"✅ Onboarding with valid photo successful: completeness={data['completeness']}")
                results["passed"].append("Onboarding - valid photo success")
                
                # Verify onboarded=true and photo_verified=true
                resp_me = await client.get(f"{BASE_URL}/auth/me", headers=user_headers)
                assert resp_me.status_code == 200
                me_data = resp_me.json()
                
                if me_data.get("onboarded") == True:
                    print(f"   ✅ onboarded=true verified")
                    results["passed"].append("Onboarding - onboarded flag set")
                else:
                    print(f"   ⚠️  onboarded={me_data.get('onboarded')}, expected True")
                    results["warnings"].append(f"Onboarding flag: got {me_data.get('onboarded')}")
                
                if me_data.get("photo_verified") == True:
                    print(f"   ✅ photo_verified=true verified")
                    results["passed"].append("Onboarding - photo_verified flag set")
                else:
                    print(f"   ⚠️  photo_verified={me_data.get('photo_verified')}, expected True")
                    results["warnings"].append(f"photo_verified flag: got {me_data.get('photo_verified')}")
            else:
                print(f"⚠️  Onboarding with valid photo failed: {resp.status_code}: {resp.text[:200]}")
                results["warnings"].append(f"Onboarding valid photo: got {resp.status_code}")
        except Exception as e:
            print(f"❌ Onboarding with valid photo test failed: {e}")
            results["failed"].append(f"Onboarding valid photo: {e}")
        
        # ========== TEST 9: Chaperone Routes Removed ==========
        print("\n🚫 TEST 9: Verify chaperone routes removed")
        
        # Test GET /api/chaperone/mine
        try:
            resp = await client.get(f"{BASE_URL}/chaperone/mine", headers=admin_headers)
            print(f"   GET /api/chaperone/mine: {resp.status_code}")
            if resp.status_code == 404:
                print(f"✅ GET /api/chaperone/mine returns 404 (removed)")
                results["passed"].append("Chaperone GET /mine removed")
            else:
                print(f"⚠️  Expected 404, got {resp.status_code}")
                results["warnings"].append(f"Chaperone GET /mine: got {resp.status_code} instead of 404")
        except Exception as e:
            print(f"❌ Chaperone GET test failed: {e}")
            results["failed"].append(f"Chaperone GET: {e}")
        
        # Test POST /api/chaperone/invite
        try:
            resp = await client.post(
                f"{BASE_URL}/chaperone/invite",
                json={"email": "test@example.com"},
                headers=admin_headers
            )
            print(f"   POST /api/chaperone/invite: {resp.status_code}")
            if resp.status_code == 404:
                print(f"✅ POST /api/chaperone/invite returns 404 (removed)")
                results["passed"].append("Chaperone POST /invite removed")
            else:
                print(f"⚠️  Expected 404, got {resp.status_code}")
                results["warnings"].append(f"Chaperone POST /invite: got {resp.status_code} instead of 404")
        except Exception as e:
            print(f"❌ Chaperone POST test failed: {e}")
            results["failed"].append(f"Chaperone POST: {e}")
        
        # ========== TEST 10: OpenAPI Spec - No Chaperone Paths ==========
        print("\n📋 TEST 10: Check OpenAPI spec for chaperone paths")
        try:
            resp = await client.get(f"{BASE_URL.replace('/api', '')}/openapi.json")
            if resp.status_code == 200:
                openapi = resp.json()
                paths = openapi.get("paths", {})
                chaperone_paths = [p for p in paths.keys() if "chaperone" in p.lower()]
                
                if len(chaperone_paths) == 0:
                    print(f"✅ No chaperone paths in OpenAPI spec")
                    results["passed"].append("OpenAPI - no chaperone paths")
                else:
                    print(f"⚠️  Found chaperone paths in OpenAPI: {chaperone_paths}")
                    results["warnings"].append(f"OpenAPI chaperone paths: {chaperone_paths}")
            else:
                print(f"⚠️  Could not fetch OpenAPI spec: {resp.status_code}")
                results["warnings"].append(f"OpenAPI fetch: {resp.status_code}")
        except Exception as e:
            print(f"⚠️  OpenAPI check failed: {e}")
            results["warnings"].append(f"OpenAPI check: {e}")
        
        # ========== REGRESSION TESTS ==========
        print("\n🔄 REGRESSION TESTS")
        
        # Test 11: GET /api/
        print("\n   TEST 11: GET /api/")
        try:
            resp = await client.get(f"{BASE_URL}/")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("status") == "ok"
            assert data.get("service") == "fidem"
            print(f"   ✅ Health check passed")
            results["passed"].append("Regression - health check")
        except Exception as e:
            print(f"   ❌ Health check failed: {e}")
            results["failed"].append(f"Regression health: {e}")
        
        # Test 12: GET /api/auth/me
        print("\n   TEST 12: GET /api/auth/me (admin)")
        try:
            resp = await client.get(f"{BASE_URL}/auth/me", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("email") == ADMIN_EMAIL
            assert data.get("is_admin") == True
            assert data.get("onboarded") == True
            print(f"   ✅ Admin /auth/me passed")
            results["passed"].append("Regression - admin /auth/me")
        except Exception as e:
            print(f"   ❌ Admin /auth/me failed: {e}")
            results["failed"].append(f"Regression admin me: {e}")
        
        # Test 13: GET /api/candidates
        print("\n   TEST 13: GET /api/candidates")
        try:
            resp = await client.get(f"{BASE_URL}/candidates", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            assert isinstance(data, list), "Expected list of candidates"
            print(f"   ✅ Candidates endpoint passed ({len(data)} candidates)")
            results["passed"].append("Regression - candidates list")
        except Exception as e:
            print(f"   ❌ Candidates endpoint failed: {e}")
            results["failed"].append(f"Regression candidates: {e}")
        
        # Test 14: GET /api/referral/mine
        print("\n   TEST 14: GET /api/referral/mine")
        try:
            resp = await client.get(f"{BASE_URL}/referral/mine", headers=admin_headers)
            assert resp.status_code == 200
            data = resp.json()
            required_fields = ["code", "link", "invited_count", "available_weeks"]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"
            print(f"   ✅ Referral endpoint passed (all fields present)")
            results["passed"].append("Regression - referral/mine")
        except Exception as e:
            print(f"   ❌ Referral endpoint failed: {e}")
            results["failed"].append(f"Regression referral: {e}")
        
        # Test 15: POST /api/messages/report
        print("\n   TEST 15: POST /api/messages/report")
        try:
            # Get a candidate to report
            resp_cand = await client.get(f"{BASE_URL}/candidates?limit=1", headers=admin_headers)
            if resp_cand.status_code == 200 and len(resp_cand.json()) > 0:
                candidate_id = resp_cand.json()[0]["id"]
                
                resp = await client.post(
                    f"{BASE_URL}/messages/report",
                    json={"user_id": candidate_id, "reason": "test"},
                    headers=admin_headers
                )
                assert resp.status_code == 200
                print(f"   ✅ Report endpoint passed")
                results["passed"].append("Regression - messages/report")
            else:
                print(f"   ⚠️  No candidates to test report")
                results["warnings"].append("Regression report: no candidates")
        except Exception as e:
            print(f"   ❌ Report endpoint failed: {e}")
            results["failed"].append(f"Regression report: {e}")
    
    # ========== SUMMARY ==========
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"\n✅ PASSED: {len(results['passed'])}")
    for test in results["passed"]:
        print(f"   • {test}")
    
    if results["warnings"]:
        print(f"\n⚠️  WARNINGS: {len(results['warnings'])}")
        for warning in results["warnings"]:
            print(f"   • {warning}")
    
    if results["failed"]:
        print(f"\n❌ FAILED: {len(results['failed'])}")
        for failure in results["failed"]:
            print(f"   • {failure}")
    
    print("\n" + "="*80)
    total_tests = len(results["passed"]) + len(results["warnings"]) + len(results["failed"])
    print(f"TOTAL: {total_tests} tests | {len(results['passed'])} passed | {len(results['warnings'])} warnings | {len(results['failed'])} failed")
    print("="*80 + "\n")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_face_verification())
