#!/usr/bin/env python3
"""
Quick re-test of payment-purpose fix (CreatePaymentRequest now accepts "standard" and "chat_unlock")
Test scenarios:
1. Login admin
2. POST /api/payments/create {purpose:"standard"} → expect 200 with amount=19900
3. POST /api/payments/create {purpose:"chat_unlock"} WITHOUT target_user_id → expect 400
4. POST /api/payments/create {purpose:"chat_unlock", target_user_id:<candidate_id>} → expect 200 with amount=9900
5. Regression: GET /api/ → {status:ok}; POST /api/payments/create {purpose:"premium"} → 200 amount=79000
"""

import requests
import os
import sys

# Base URL from frontend/.env
BASE_URL = "https://loyihani-clone.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

def test_payment_purpose_fix():
    """Test payment-purpose fix for standard and chat_unlock"""
    
    print("=" * 80)
    print("PAYMENT PURPOSE FIX RE-TEST")
    print("=" * 80)
    
    results = {
        "passed": 0,
        "failed": 0,
        "scenarios": []
    }
    
    # Scenario 1: Login admin to get token
    print("\n[Scenario 1] Login admin to get token")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("token")
            if token:
                print(f"✅ PASS: Admin login successful, token received")
                results["passed"] += 1
                results["scenarios"].append({
                    "name": "Admin login",
                    "status": "PASS",
                    "details": f"HTTP {resp.status_code}, token received"
                })
            else:
                print(f"❌ FAIL: No token in response")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Admin login",
                    "status": "FAIL",
                    "details": "No token in response"
                })
                return results
        else:
            print(f"❌ FAIL: Login failed with HTTP {resp.status_code}")
            print(f"Response: {resp.text}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Admin login",
                "status": "FAIL",
                "details": f"HTTP {resp.status_code}"
            })
            return results
    except Exception as e:
        print(f"❌ FAIL: Exception during login: {e}")
        results["failed"] += 1
        results["scenarios"].append({
            "name": "Admin login",
            "status": "FAIL",
            "details": str(e)
        })
        return results
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get a candidate ID for chat_unlock test
    print("\n[Setup] Getting candidate ID for chat_unlock test")
    try:
        resp = requests.get(f"{BASE_URL}/candidates", headers=headers, timeout=10)
        if resp.status_code == 200:
            candidates = resp.json()
            if candidates and len(candidates) > 0:
                candidate_id = candidates[0]["id"]
                print(f"✅ Got candidate ID: {candidate_id}")
            else:
                print("⚠️ No candidates found, will skip chat_unlock with target_user_id test")
                candidate_id = None
        else:
            print(f"⚠️ Failed to get candidates (HTTP {resp.status_code}), will skip chat_unlock with target_user_id test")
            candidate_id = None
    except Exception as e:
        print(f"⚠️ Exception getting candidates: {e}, will skip chat_unlock with target_user_id test")
        candidate_id = None
    
    # Scenario 2: POST /api/payments/create {purpose:"standard"} → expect 200 with amount=19900
    print("\n[Scenario 2] POST /api/payments/create {purpose:'standard'}")
    try:
        resp = requests.post(f"{BASE_URL}/payments/create", 
                            headers=headers,
                            json={"purpose": "standard"},
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            amount = data.get("payment", {}).get("amount") or data.get("amount")
            payment_link = data.get("payment_link")
            status = data.get("payment", {}).get("status") or data.get("status")
            
            if amount == 19900 and payment_link and status == "pending":
                print(f"✅ PASS: purpose='standard' returns 200 with amount=19900, payment_link present, status='pending'")
                print(f"   Amount: {amount}, Status: {status}, Payment link: {payment_link[:50]}...")
                results["passed"] += 1
                results["scenarios"].append({
                    "name": "Create payment purpose='standard'",
                    "status": "PASS",
                    "details": f"HTTP 200, amount={amount}, status={status}, payment_link present"
                })
            else:
                print(f"❌ FAIL: Response structure incorrect")
                print(f"   Expected: amount=19900, payment_link present, status='pending'")
                print(f"   Got: amount={amount}, payment_link={bool(payment_link)}, status={status}")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Create payment purpose='standard'",
                    "status": "FAIL",
                    "details": f"HTTP 200 but incorrect data: amount={amount}, status={status}"
                })
        else:
            print(f"❌ FAIL: Expected HTTP 200, got {resp.status_code}")
            print(f"Response: {resp.text}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Create payment purpose='standard'",
                "status": "FAIL",
                "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
            })
    except Exception as e:
        print(f"❌ FAIL: Exception: {e}")
        results["failed"] += 1
        results["scenarios"].append({
            "name": "Create payment purpose='standard'",
            "status": "FAIL",
            "details": str(e)
        })
    
    # Scenario 3: POST /api/payments/create {purpose:"chat_unlock"} WITHOUT target_user_id → expect 400
    print("\n[Scenario 3] POST /api/payments/create {purpose:'chat_unlock'} WITHOUT target_user_id")
    try:
        resp = requests.post(f"{BASE_URL}/payments/create", 
                            headers=headers,
                            json={"purpose": "chat_unlock"},
                            timeout=10)
        
        if resp.status_code == 400:
            error_msg = resp.json().get("detail", "")
            if "target_user_id" in error_msg.lower():
                print(f"✅ PASS: purpose='chat_unlock' without target_user_id correctly rejected with 400")
                print(f"   Error: {error_msg}")
                results["passed"] += 1
                results["scenarios"].append({
                    "name": "Create payment purpose='chat_unlock' without target_user_id",
                    "status": "PASS",
                    "details": f"HTTP 400 with correct error: {error_msg}"
                })
            else:
                print(f"❌ FAIL: Got 400 but error message doesn't mention target_user_id")
                print(f"   Error: {error_msg}")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Create payment purpose='chat_unlock' without target_user_id",
                    "status": "FAIL",
                    "details": f"HTTP 400 but wrong error: {error_msg}"
                })
        else:
            print(f"❌ FAIL: Expected HTTP 400, got {resp.status_code}")
            print(f"Response: {resp.text}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Create payment purpose='chat_unlock' without target_user_id",
                "status": "FAIL",
                "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
            })
    except Exception as e:
        print(f"❌ FAIL: Exception: {e}")
        results["failed"] += 1
        results["scenarios"].append({
            "name": "Create payment purpose='chat_unlock' without target_user_id",
            "status": "FAIL",
            "details": str(e)
        })
    
    # Scenario 4: POST /api/payments/create {purpose:"chat_unlock", target_user_id:<candidate_id>} → expect 200 with amount=9900
    if candidate_id:
        print(f"\n[Scenario 4] POST /api/payments/create {{purpose:'chat_unlock', target_user_id:'{candidate_id}'}}")
        try:
            resp = requests.post(f"{BASE_URL}/payments/create", 
                                headers=headers,
                                json={"purpose": "chat_unlock", "target_user_id": candidate_id},
                                timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                amount = data.get("payment", {}).get("amount") or data.get("amount")
                payment_link = data.get("payment_link")
                status = data.get("payment", {}).get("status") or data.get("status")
                
                if amount == 9900 and payment_link:
                    print(f"✅ PASS: purpose='chat_unlock' with target_user_id returns 200 with amount=9900, payment_link present")
                    print(f"   Amount: {amount}, Status: {status}, Payment link: {payment_link[:50]}...")
                    results["passed"] += 1
                    results["scenarios"].append({
                        "name": "Create payment purpose='chat_unlock' with target_user_id",
                        "status": "PASS",
                        "details": f"HTTP 200, amount={amount}, status={status}, payment_link present"
                    })
                else:
                    print(f"❌ FAIL: Response structure incorrect")
                    print(f"   Expected: amount=9900, payment_link present")
                    print(f"   Got: amount={amount}, payment_link={bool(payment_link)}")
                    results["failed"] += 1
                    results["scenarios"].append({
                        "name": "Create payment purpose='chat_unlock' with target_user_id",
                        "status": "FAIL",
                        "details": f"HTTP 200 but incorrect data: amount={amount}"
                    })
            else:
                print(f"❌ FAIL: Expected HTTP 200, got {resp.status_code}")
                print(f"Response: {resp.text}")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Create payment purpose='chat_unlock' with target_user_id",
                    "status": "FAIL",
                    "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
                })
        except Exception as e:
            print(f"❌ FAIL: Exception: {e}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Create payment purpose='chat_unlock' with target_user_id",
                "status": "FAIL",
                "details": str(e)
            })
    else:
        print("\n[Scenario 4] SKIPPED: No candidate ID available")
        results["scenarios"].append({
            "name": "Create payment purpose='chat_unlock' with target_user_id",
            "status": "SKIP",
            "details": "No candidate ID available"
        })
    
    # Scenario 5a: Regression - GET /api/ → {status:ok}
    print("\n[Scenario 5a] Regression: GET /api/")
    try:
        resp = requests.get(f"{BASE_URL}/", timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "ok":
                print(f"✅ PASS: GET /api/ returns {{status:ok}}")
                results["passed"] += 1
                results["scenarios"].append({
                    "name": "Regression: GET /api/",
                    "status": "PASS",
                    "details": "HTTP 200, status=ok"
                })
            else:
                print(f"❌ FAIL: status field not 'ok': {data}")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Regression: GET /api/",
                    "status": "FAIL",
                    "details": f"status={data.get('status')}"
                })
        else:
            print(f"❌ FAIL: Expected HTTP 200, got {resp.status_code}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Regression: GET /api/",
                "status": "FAIL",
                "details": f"HTTP {resp.status_code}"
            })
    except Exception as e:
        print(f"❌ FAIL: Exception: {e}")
        results["failed"] += 1
        results["scenarios"].append({
            "name": "Regression: GET /api/",
            "status": "FAIL",
            "details": str(e)
        })
    
    # Scenario 5b: Regression - POST /api/payments/create {purpose:"premium"} → 200 amount=79000
    print("\n[Scenario 5b] Regression: POST /api/payments/create {purpose:'premium'}")
    try:
        resp = requests.post(f"{BASE_URL}/payments/create", 
                            headers=headers,
                            json={"purpose": "premium"},
                            timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            amount = data.get("payment", {}).get("amount") or data.get("amount")
            
            if amount == 79000:
                print(f"✅ PASS: purpose='premium' returns 200 with amount=79000")
                results["passed"] += 1
                results["scenarios"].append({
                    "name": "Regression: Create payment purpose='premium'",
                    "status": "PASS",
                    "details": f"HTTP 200, amount={amount}"
                })
            else:
                print(f"❌ FAIL: Expected amount=79000, got {amount}")
                results["failed"] += 1
                results["scenarios"].append({
                    "name": "Regression: Create payment purpose='premium'",
                    "status": "FAIL",
                    "details": f"HTTP 200 but amount={amount}"
                })
        else:
            print(f"❌ FAIL: Expected HTTP 200, got {resp.status_code}")
            print(f"Response: {resp.text}")
            results["failed"] += 1
            results["scenarios"].append({
                "name": "Regression: Create payment purpose='premium'",
                "status": "FAIL",
                "details": f"HTTP {resp.status_code}: {resp.text[:100]}"
            })
    except Exception as e:
        print(f"❌ FAIL: Exception: {e}")
        results["failed"] += 1
        results["scenarios"].append({
            "name": "Regression: Create payment purpose='premium'",
            "status": "FAIL",
            "details": str(e)
        })
    
    return results


if __name__ == "__main__":
    results = test_payment_purpose_fix()
    
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    for scenario in results["scenarios"]:
        status_icon = "✅" if scenario["status"] == "PASS" else "❌" if scenario["status"] == "FAIL" else "⏭️"
        print(f"{status_icon} {scenario['name']}: {scenario['status']}")
        if scenario["status"] == "FAIL":
            print(f"   Details: {scenario['details']}")
    
    print(f"\nTotal: {results['passed']} PASSED, {results['failed']} FAILED")
    
    if results["failed"] > 0:
        sys.exit(1)
    else:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
