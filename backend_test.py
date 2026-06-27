#!/usr/bin/env python3
"""
Backend test for Chat monetization + coins economy + Standard tariff feature.
Tests the NEW monetization system with chat unlocks, coins, and Standard plan.
"""
import requests
import time
import sys

# Base URL from frontend/.env
BASE_URL = "https://clone-test-4.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Test results
results = []

def log_test(name, passed, details=""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    results.append({"name": name, "passed": passed, "details": details})
    print(f"{status}: {name}")
    if details:
        print(f"  Details: {details}")

def test_chat_monetization():
    """Test chat monetization + coins economy + Standard tariff"""
    print("\n" + "="*80)
    print("TESTING: Chat Monetization + Coins Economy + Standard Tariff")
    print("="*80 + "\n")
    
    # ========== SETUP ==========
    print("--- SETUP ---")
    
    # 1. Login admin (VIP user)
    print("\n1. Login admin (VIP user)...")
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    if resp.status_code != 200:
        log_test("Admin login", False, f"Status {resp.status_code}: {resp.text}")
        return
    data = resp.json()
    admin_token = data["token"]
    admin_id = data["user_id"]
    log_test("Admin login", True, f"Admin ID: {admin_id}, is_admin: {data.get('is_admin')}")
    
    # 2. Register a FRESH FREE user A
    print("\n2. Register fresh FREE user A...")
    timestamp = int(time.time())
    user_a_email = f"test_free_user_{timestamp}@example.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": user_a_email,
        "password": "TestPass123",
        "name": f"Test User A {timestamp}"
    })
    if resp.status_code != 200:
        log_test("Register user A", False, f"Status {resp.status_code}: {resp.text}")
        return
    data = resp.json()
    user_a_token = data["token"]
    user_a_id = data["user_id"]
    # Get full user details from /auth/me
    resp_me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {user_a_token}"})
    if resp_me.status_code == 200:
        me_data = resp_me.json()
        user_a_plan = me_data.get("plan", "free")
        user_a_balance = me_data.get("balance", 0)
        user_a_coins = me_data.get("coins", 0)
    else:
        user_a_plan = "free"
        user_a_balance = 0
        user_a_coins = 0
    log_test("Register user A", True, 
             f"User A ID: {user_a_id}, plan: {user_a_plan}, balance: {user_a_balance}, coins: {user_a_coins}")
    
    # 3. Check if user A needs onboarding
    print("\n3. Check user A onboarding status...")
    resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code != 200:
        log_test("Check user A status", False, f"Status {resp.status_code}: {resp.text}")
        return
    user_a_onboarded = resp.json().get("onboarded", False)
    log_test("Check user A status", True, f"Onboarded: {user_a_onboarded}")
    
    # 4. Onboard user A if needed (minimal onboarding)
    if not user_a_onboarded:
        print("\n4. Onboard user A...")
        resp = requests.post(f"{BASE_URL}/profile/onboard", 
                           headers={"Authorization": f"Bearer {user_a_token}"},
                           json={
                               "gender": "male",
                               "birth_date": "1995-01-01",
                               "region": "Toshkent",
                               "marital_status": "single",
                               "has_children": False,
                               "height_cm": 175,
                               "weight_kg": 70,
                               "education": "Oliy",
                               "profession": "Dasturchi",
                               "religion": "Islom",
                               "bio": "Test user"
                           })
        if resp.status_code == 200:
            log_test("Onboard user A", True, "User A onboarded successfully")
        else:
            log_test("Onboard user A", False, f"Status {resp.status_code}: {resp.text}")
    else:
        print("\n4. User A already onboarded, skipping...")
    
    # 5. Get a demo candidate B's id
    print("\n5. Get demo candidate B...")
    resp = requests.get(f"{BASE_URL}/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code != 200:
        log_test("Get candidates", False, f"Status {resp.status_code}: {resp.text}")
        return
    candidates = resp.json()
    if not candidates:
        log_test("Get candidates", False, "No candidates found")
        return
    candidate_b_id = candidates[0]["id"]
    candidate_b_name = candidates[0].get("name", "Unknown")
    log_test("Get candidates", True, f"Candidate B ID: {candidate_b_id}, name: {candidate_b_name}")
    
    # ========== TESTS ==========
    print("\n--- TESTS ---")
    
    # TEST 1: Chat access (free user) - expect requires_unlock=true
    print("\n1. TEST: Chat access (free user)...")
    resp = requests.get(f"{BASE_URL}/chat/access/{candidate_b_id}", 
                       headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        expected_fields = {
            "requires_unlock": True,
            "can_message": False,
            "price_uzs": 9900,
            "price_coins": 100,
            "plan": "free",
            "plan_active": False,
            "guarantee_hours": 48
        }
        all_match = True
        mismatches = []
        for key, expected_val in expected_fields.items():
            actual_val = data.get(key)
            if actual_val != expected_val:
                all_match = False
                mismatches.append(f"{key}: expected {expected_val}, got {actual_val}")
        
        if all_match:
            log_test("Chat access (free user)", True, 
                    f"All fields correct: requires_unlock=true, can_message=false, price_uzs=9900, price_coins=100, plan=free, plan_active=false, guarantee_hours=48, balance={data.get('balance')}, coins={data.get('coins')}, free_credits={data.get('free_credits')}")
        else:
            log_test("Chat access (free user)", False, f"Field mismatches: {', '.join(mismatches)}")
    else:
        log_test("Chat access (free user)", False, f"Status {resp.status_code}: {resp.text}")
    
    # TEST 2: Send blocked (free user) - expect 402 with "chat_locked"
    print("\n2. TEST: Send message blocked (free user)...")
    resp = requests.post(f"{BASE_URL}/messages/send",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"to_user_id": candidate_b_id, "text": "Salom"})
    if resp.status_code == 402:
        detail = resp.json().get("detail", "")
        if "chat_locked" in detail:
            log_test("Send blocked (free user)", True, f"Correctly blocked with 402 and detail: {detail}")
        else:
            log_test("Send blocked (free user)", False, f"Got 402 but wrong detail: {detail}")
    else:
        log_test("Send blocked (free user)", False, f"Expected 402, got {resp.status_code}: {resp.text}")
    
    # TEST 3: Unlock insufficient balance - expect 402
    print("\n3. TEST: Unlock with insufficient balance...")
    resp = requests.post(f"{BASE_URL}/chat/unlock",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"target_id": candidate_b_id, "method": "balance"})
    if resp.status_code == 402:
        log_test("Unlock insufficient balance", True, f"Correctly rejected with 402: {resp.json().get('detail')}")
    else:
        log_test("Unlock insufficient balance", False, f"Expected 402, got {resp.status_code}: {resp.text}")
    
    # TEST 4: Unlock insufficient coins - expect 402
    print("\n4. TEST: Unlock with insufficient coins...")
    resp = requests.post(f"{BASE_URL}/chat/unlock",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"target_id": candidate_b_id, "method": "coins"})
    if resp.status_code == 402:
        log_test("Unlock insufficient coins", True, f"Correctly rejected with 402: {resp.json().get('detail')}")
    else:
        log_test("Unlock insufficient coins", False, f"Expected 402, got {resp.status_code}: {resp.text}")
    
    # TEST 5: Top up + unlock by balance
    print("\n5. TEST: Top up balance + unlock by balance...")
    # 5a. Admin tops up user A's balance
    print("  5a. Admin tops up user A's balance to 20000...")
    resp = requests.patch(f"{BASE_URL}/admin/users/{user_a_id}",
                         headers={"Authorization": f"Bearer {admin_token}"},
                         json={"add_balance": 20000})
    if resp.status_code != 200:
        log_test("Admin top up balance", False, f"Status {resp.status_code}: {resp.text}")
        return
    log_test("Admin top up balance", True, "Balance topped up to 20000")
    
    # 5b. Unlock by balance
    print("  5b. Unlock chat by balance...")
    resp = requests.post(f"{BASE_URL}/chat/unlock",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"target_id": candidate_b_id, "method": "balance"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("ok") and data.get("can_message"):
            log_test("Unlock by balance", True, f"Unlock successful: {data}")
        else:
            log_test("Unlock by balance", False, f"Unlock returned 200 but unexpected data: {data}")
    else:
        log_test("Unlock by balance", False, f"Status {resp.status_code}: {resp.text}")
    
    # 5c. Check chat access after unlock
    print("  5c. Check chat access after unlock...")
    resp = requests.get(f"{BASE_URL}/chat/access/{candidate_b_id}",
                       headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("can_message") and data.get("unlocked"):
            log_test("Chat access after unlock", True, 
                    f"can_message=true, unlocked=true, balance={data.get('balance')}")
        else:
            log_test("Chat access after unlock", False, 
                    f"Expected can_message=true and unlocked=true, got: {data}")
    else:
        log_test("Chat access after unlock", False, f"Status {resp.status_code}: {resp.text}")
    
    # 5d. Send message after unlock
    print("  5d. Send message after unlock...")
    resp = requests.post(f"{BASE_URL}/messages/send",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"to_user_id": candidate_b_id, "text": "Salom, qalaysiz?"})
    if resp.status_code == 200:
        log_test("Send message after unlock", True, f"Message sent successfully: {resp.json().get('id')}")
    else:
        log_test("Send message after unlock", False, f"Status {resp.status_code}: {resp.text}")
    
    # TEST 6: VIP can message freely
    print("\n6. TEST: VIP can message freely...")
    # 6a. Get another candidate for admin to message
    if len(candidates) > 1:
        candidate_c_id = candidates[1]["id"]
    else:
        candidate_c_id = candidate_b_id
    
    # 6a. Check chat access as admin (VIP)
    print("  6a. Check chat access as admin (VIP)...")
    resp = requests.get(f"{BASE_URL}/chat/access/{candidate_c_id}",
                       headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("plan_active") and not data.get("requires_unlock") and data.get("can_message"):
            log_test("VIP chat access", True, 
                    f"plan_active=true, requires_unlock=false, can_message=true, plan={data.get('plan')}")
        else:
            log_test("VIP chat access", False, 
                    f"Expected VIP to have free access, got: plan_active={data.get('plan_active')}, requires_unlock={data.get('requires_unlock')}, can_message={data.get('can_message')}")
    else:
        log_test("VIP chat access", False, f"Status {resp.status_code}: {resp.text}")
    
    # 6b. Send message as admin (VIP) without unlock
    print("  6b. Send message as admin (VIP) without unlock...")
    resp = requests.post(f"{BASE_URL}/messages/send",
                        headers={"Authorization": f"Bearer {admin_token}"},
                        json={"to_user_id": candidate_c_id, "text": "Salom, men admin"})
    if resp.status_code == 200:
        log_test("VIP send message", True, f"VIP sent message without unlock: {resp.json().get('id')}")
    else:
        log_test("VIP send message", False, f"Status {resp.status_code}: {resp.text}")
    
    # TEST 7: Daily coins
    print("\n7. TEST: Daily coins...")
    # 7a. Check daily status
    print("  7a. Check daily status...")
    resp = requests.get(f"{BASE_URL}/daily/status",
                       headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("currency") == "coins":
            log_test("Daily status", True, 
                    f"currency=coins, next_bonus={data.get('next_bonus')}, coins={data.get('coins')}, claimed_today={data.get('claimed_today')}")
        else:
            log_test("Daily status", False, f"Expected currency=coins, got: {data}")
    else:
        log_test("Daily status", False, f"Status {resp.status_code}: {resp.text}")
    
    # 7b. Claim daily coins
    print("  7b. Claim daily coins...")
    resp = requests.post(f"{BASE_URL}/daily/claim",
                        headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("currency") == "coins" and data.get("bonus") >= 20:
            log_test("Daily claim", True, 
                    f"Claimed {data.get('bonus')} coins (currency=coins), coins_after={data.get('coins_after')}, streak={data.get('streak')}")
        else:
            log_test("Daily claim", False, f"Expected coins bonus >= 20, got: {data}")
    else:
        log_test("Daily claim", False, f"Status {resp.status_code}: {resp.text}")
    
    # 7c. Verify coins increased (NOT balance)
    print("  7c. Verify coins increased (NOT balance)...")
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        new_coins = data.get("coins", 0)
        new_balance = data.get("balance", 0)
        # Balance should be 20000 - 9900 = 10100 (from unlock)
        # Coins should be 0 + 20 = 20 (from daily claim)
        if new_coins >= 20:
            log_test("Coins increased", True, f"Coins increased to {new_coins} (balance={new_balance})")
        else:
            log_test("Coins increased", False, f"Expected coins >= 20, got coins={new_coins}, balance={new_balance}")
    else:
        log_test("Coins increased", False, f"Status {resp.status_code}: {resp.text}")
    
    # 7d. Second claim same day should fail
    print("  7d. Second claim same day should fail...")
    resp = requests.post(f"{BASE_URL}/daily/claim",
                        headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 400:
        log_test("Second daily claim blocked", True, f"Correctly rejected with 400: {resp.json().get('detail')}")
    else:
        log_test("Second daily claim blocked", False, f"Expected 400, got {resp.status_code}: {resp.text}")
    
    # TEST 8: Payments purposes
    print("\n8. TEST: Payments purposes...")
    # 8a. Create payment for standard plan
    print("  8a. Create payment for standard plan...")
    resp = requests.post(f"{BASE_URL}/payments/create",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"purpose": "standard"})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("amount") == 19900 and data.get("payment_link"):
            log_test("Payment standard", True, f"amount=19900, payment_link={data.get('payment_link')[:50]}...")
        else:
            log_test("Payment standard", False, f"Expected amount=19900 with payment_link, got: {data}")
    else:
        log_test("Payment standard", False, f"Status {resp.status_code}: {resp.text}")
    
    # 8b. Create payment for chat_unlock WITHOUT target_user_id - expect 400
    print("  8b. Create payment for chat_unlock WITHOUT target_user_id...")
    resp = requests.post(f"{BASE_URL}/payments/create",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"purpose": "chat_unlock"})
    if resp.status_code == 400:
        log_test("Payment chat_unlock without target", True, f"Correctly rejected with 400: {resp.json().get('detail')}")
    else:
        log_test("Payment chat_unlock without target", False, f"Expected 400, got {resp.status_code}: {resp.text}")
    
    # 8c. Create payment for chat_unlock WITH target_user_id
    print("  8c. Create payment for chat_unlock WITH target_user_id...")
    resp = requests.post(f"{BASE_URL}/payments/create",
                        headers={"Authorization": f"Bearer {user_a_token}"},
                        json={"purpose": "chat_unlock", "target_user_id": candidate_b_id})
    if resp.status_code == 200:
        data = resp.json()
        if data.get("amount") == 9900 and data.get("payment_link"):
            log_test("Payment chat_unlock with target", True, f"amount=9900, payment_link={data.get('payment_link')[:50]}...")
        else:
            log_test("Payment chat_unlock with target", False, f"Expected amount=9900 with payment_link, got: {data}")
    else:
        log_test("Payment chat_unlock with target", False, f"Status {resp.status_code}: {resp.text}")
    
    # TEST 9: Regression tests
    print("\n9. TEST: Regression tests...")
    # 9a. Health check
    print("  9a. Health check...")
    resp = requests.get(f"{BASE_URL}/")
    if resp.status_code == 200 and resp.json().get("status") == "ok":
        log_test("Health check", True, f"status=ok")
    else:
        log_test("Health check", False, f"Status {resp.status_code}: {resp.text}")
    
    # 9b. Get candidates as admin
    print("  9b. Get candidates as admin...")
    resp = requests.get(f"{BASE_URL}/candidates",
                       headers={"Authorization": f"Bearer {admin_token}"})
    if resp.status_code == 200 and isinstance(resp.json(), list):
        log_test("Get candidates", True, f"Returned {len(resp.json())} candidates")
    else:
        log_test("Get candidates", False, f"Status {resp.status_code}: {resp.text}")
    
    # 9c. Get auth/me as user A - verify coins field
    print("  9c. Get auth/me as user A - verify coins field...")
    resp = requests.get(f"{BASE_URL}/auth/me",
                       headers={"Authorization": f"Bearer {user_a_token}"})
    if resp.status_code == 200:
        data = resp.json()
        if "coins" in data and data.get("plan") == "free":
            log_test("Auth/me includes coins", True, f"coins={data.get('coins')}, plan={data.get('plan')}")
        else:
            log_test("Auth/me includes coins", False, f"Missing coins field or wrong plan: {data}")
    else:
        log_test("Auth/me includes coins", False, f"Status {resp.status_code}: {resp.text}")

def print_summary():
    """Print test summary"""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])
    total = len(results)
    
    print(f"\nTotal: {total} tests")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {failed} ❌")
    print(f"Success rate: {passed/total*100:.1f}%\n")
    
    if failed > 0:
        print("FAILED TESTS:")
        for r in results:
            if not r["passed"]:
                print(f"  ❌ {r['name']}")
                if r["details"]:
                    print(f"     {r['details']}")
    
    print("\n" + "="*80)
    
    return failed == 0

if __name__ == "__main__":
    try:
        test_chat_monetization()
        success = print_summary()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
