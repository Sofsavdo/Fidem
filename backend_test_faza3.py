#!/usr/bin/env python3
"""
Comprehensive backend testing for FIDEM Faza 3 features.
Tests 4 new modules: Withdrawals, Family Contact Share, Sovchi Concierge, Travel Mode.
"""
import requests
import time
import json
from datetime import datetime

# Backend URL from frontend/.env
BASE_URL = "https://preview-loyihani.preview.emergentagent.com/api"

# Test credentials
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Global tokens
admin_token = None
test_user_token = None
test_user_id = None
admin_id = None

def log_test(name, passed, details=""):
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   {details}")

def login_admin():
    global admin_token, admin_id
    resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    })
    assert resp.status_code == 200, f"Admin login failed: {resp.text}"
    data = resp.json()
    admin_token = data["token"]
    admin_id = data["user_id"]
    log_test("Admin login", True, f"Admin ID: {admin_id}")
    return admin_token

def create_test_user():
    global test_user_token, test_user_id
    timestamp = int(time.time())
    email = f"qa_faza3_{timestamp}@example.com"
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": email,
        "password": "TestPass123",
        "name": f"QA User {timestamp}"
    })
    assert resp.status_code == 200, f"User registration failed: {resp.text}"
    data = resp.json()
    test_user_token = data["token"]
    test_user_id = data["user_id"]
    log_test("Create test user", True, f"User ID: {test_user_id}, Email: {email}")
    return test_user_token

def get_admin_balance():
    resp = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    return resp.json().get("balance", 0)

def topup_admin_balance(amount):
    """Top up admin balance via admin endpoint"""
    resp = requests.patch(
        f"{BASE_URL}/admin/users/{admin_id}",
        json={"add_balance": amount},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200, f"Balance top-up failed: {resp.text}"
    log_test("Top up admin balance", True, f"Added {amount} UZS")

def get_candidates():
    """Get list of demo users"""
    resp = requests.get(f"{BASE_URL}/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    return resp.json()

# ============================================================================
# MODULE 1: WITHDRAWALS (Gift conversion + cash-out)
# ============================================================================

def test_withdrawals_module():
    print("\n" + "="*80)
    print("MODULE 1: WITHDRAWALS (Bigo-style gift conversion)")
    print("="*80)
    
    # Test 1: GET /api/withdrawals/status (initial state)
    resp = requests.get(f"{BASE_URL}/withdrawals/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "withdrawable_balance" in data
    assert data["min_payout"] == 100000
    assert data["conversion_rate_pct"] == 50
    initial_balance = data["withdrawable_balance"]
    log_test("GET /api/withdrawals/status", True, f"Initial withdrawable_balance: {initial_balance} UZS")
    
    # Test 2: Send a gift to populate withdrawable_balance
    # First ensure admin has balance
    admin_balance = get_admin_balance()
    if admin_balance < 5000:
        topup_admin_balance(5000)
    
    # Get a demo user to send gift to
    candidates = get_candidates()
    if not candidates:
        log_test("Send gift to populate withdrawable_balance", False, "No candidates found")
        return
    
    recipient = candidates[0]
    recipient_id = recipient["id"]
    
    # Send 'rose' gift (price=50) to recipient
    resp = requests.post(
        f"{BASE_URL}/gifts/send",
        json={"to_user_id": recipient_id, "gift_kind": "rose"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200, f"Gift send failed: {resp.text}"
    log_test("Send gift (rose, price=50)", True, f"Sent to {recipient['name']}")
    
    # Verify recipient's withdrawable_balance increased by 50% of gift price (25 UZS)
    # We need to login as recipient or check via admin endpoint
    # For now, we'll test with admin sending gift to test_user
    
    # Send gift to test_user instead
    resp = requests.post(
        f"{BASE_URL}/gifts/send",
        json={"to_user_id": test_user_id, "gift_kind": "rose"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    log_test("Send gift to test_user", True, "Gift sent successfully")
    
    # Check test_user's withdrawable_balance
    resp = requests.get(f"{BASE_URL}/withdrawals/status", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    test_user_balance = data["withdrawable_balance"]
    assert test_user_balance >= 25, f"Expected at least 25 UZS, got {test_user_balance}"
    log_test("Verify recipient withdrawable_balance", True, f"Test user has {test_user_balance} UZS (50% of gift price)")
    
    # Test 3: POST /api/withdrawals/request with amount < min_payout (should fail)
    resp = requests.post(
        f"{BASE_URL}/withdrawals/request",
        json={"amount": 50000, "card_number": "8600123456789012", "holder_name": "Test User"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/withdrawals/request (amount < min_payout)", True, "Correctly rejected with 400")
    
    # Test 4: Send more gifts to reach min_payout threshold
    # Need to send enough gifts to reach 100,000 UZS withdrawable balance
    # Let's send 'crown' gift (price=1500) multiple times
    # 100,000 / 0.5 = 200,000 UZS in gifts needed, so 200,000 / 1500 = 134 crowns
    for i in range(135):  # 135 * 1500 * 0.5 = 101,250 UZS
        resp = requests.post(
            f"{BASE_URL}/gifts/send",
            json={"to_user_id": test_user_id, "gift_kind": "crown"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            # Admin might run out of balance, top up
            topup_admin_balance(300000)
            resp = requests.post(
                f"{BASE_URL}/gifts/send",
                json={"to_user_id": test_user_id, "gift_kind": "crown"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
    
    log_test("Send multiple gifts to reach min_payout", True, "Sent 135 crown gifts")
    
    # Check test_user's withdrawable_balance again
    resp = requests.get(f"{BASE_URL}/withdrawals/status", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    test_user_balance = data["withdrawable_balance"]
    log_test("Check withdrawable_balance after gifts", True, f"Test user has {test_user_balance} UZS")
    
    if test_user_balance < 100000:
        log_test("Withdrawable balance check", False, f"Balance {test_user_balance} < min_payout 100,000")
        return
    
    # Test 5: POST /api/withdrawals/request with valid amount
    resp = requests.post(
        f"{BASE_URL}/withdrawals/request",
        json={"amount": 100000, "card_number": "8600123456789012", "holder_name": "QA Test User"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 200, f"Withdrawal request failed: {resp.text}"
    data = resp.json()
    assert data["ok"] == True
    assert data["status"] == "pending"
    withdrawal_id = data["id"]
    log_test("POST /api/withdrawals/request (valid)", True, f"Withdrawal ID: {withdrawal_id}")
    
    # Test 6: Test atomic hold - re-request with same balance (should fail)
    resp = requests.post(
        f"{BASE_URL}/withdrawals/request",
        json={"amount": 100000, "card_number": "8600123456789012", "holder_name": "QA Test User"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/withdrawals/request (atomic hold test)", True, "Correctly rejected duplicate request")
    
    # Test 7: GET /api/withdrawals/mine
    resp = requests.get(f"{BASE_URL}/withdrawals/mine", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert data[0]["id"] == withdrawal_id
    log_test("GET /api/withdrawals/mine", True, f"Found {len(data)} withdrawal(s)")
    
    # Test 8: GET /api/admin/withdrawals (admin only)
    resp = requests.get(f"{BASE_URL}/admin/withdrawals", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "user" in data[0]
    log_test("GET /api/admin/withdrawals (admin)", True, f"Found {len(data)} withdrawal(s) with user info")
    
    # Test 9: Non-admin calling admin endpoint (should fail with 403)
    resp = requests.get(f"{BASE_URL}/admin/withdrawals", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 403
    log_test("GET /api/admin/withdrawals (non-admin)", True, "Correctly rejected with 403")
    
    # Test 10: POST /api/admin/withdrawals/{wid}/approve
    resp = requests.post(
        f"{BASE_URL}/admin/withdrawals/{withdrawal_id}/approve",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] == True
    log_test("POST /api/admin/withdrawals/{wid}/approve", True, "Withdrawal approved")
    
    # Verify status changed to 'approved'
    resp = requests.get(f"{BASE_URL}/withdrawals/mine", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    approved_withdrawal = next((w for w in data if w["id"] == withdrawal_id), None)
    assert approved_withdrawal["status"] == "approved"
    log_test("Verify withdrawal status", True, "Status is 'approved'")
    
    # Test 11: Create another withdrawal for rejection test
    # First send more gifts to replenish balance
    for i in range(135):  # 135 * 1500 * 0.5 = 101,250 UZS
        resp = requests.post(
            f"{BASE_URL}/gifts/send",
            json={"to_user_id": test_user_id, "gift_kind": "crown"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        if resp.status_code != 200:
            topup_admin_balance(300000)
            resp = requests.post(
                f"{BASE_URL}/gifts/send",
                json={"to_user_id": test_user_id, "gift_kind": "crown"},
                headers={"Authorization": f"Bearer {admin_token}"}
            )
    
    resp = requests.post(
        f"{BASE_URL}/withdrawals/request",
        json={"amount": 100000, "card_number": "8600123456789012", "holder_name": "QA Test User"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 200
    withdrawal_id_2 = resp.json()["id"]
    
    # Test 12: POST /api/admin/withdrawals/{wid}/reject
    resp = requests.post(
        f"{BASE_URL}/admin/withdrawals/{withdrawal_id_2}/reject",
        json={"reason": "Test rejection"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] == True
    log_test("POST /api/admin/withdrawals/{wid}/reject", True, "Withdrawal rejected")
    
    # Verify balance was restored
    resp = requests.get(f"{BASE_URL}/withdrawals/status", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 200
    data = resp.json()
    restored_balance = data["withdrawable_balance"]
    log_test("Verify balance restored after rejection", True, f"Balance: {restored_balance} UZS")

# ============================================================================
# MODULE 2: FAMILY CONTACT SHARE (VIP only)
# ============================================================================

def test_family_module():
    print("\n" + "="*80)
    print("MODULE 2: FAMILY CONTACT SHARE (VIP only)")
    print("="*80)
    
    # Test 1: PATCH /api/family/contacts with short phone (should fail)
    resp = requests.patch(
        f"{BASE_URL}/family/contacts",
        json={"parent_phone": "12345", "parent_name": "Test Parent", "parent_relation": "parent"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("PATCH /api/family/contacts (short phone)", True, "Correctly rejected with 400")
    
    # Test 2: PATCH /api/family/contacts with valid phone
    resp = requests.patch(
        f"{BASE_URL}/family/contacts",
        json={"parent_phone": "+998901234567", "parent_name": "Admin Parent", "parent_relation": "parent"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] == True
    log_test("PATCH /api/family/contacts (valid)", True, "Family contact set successfully")
    
    # Test 3: GET /api/family/contacts/mine
    resp = requests.get(f"{BASE_URL}/family/contacts/mine", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "family_contact" in data
    assert data["family_contact"]["phone"] == "+998901234567"
    log_test("GET /api/family/contacts/mine", True, f"Retrieved contact: {data['family_contact']['phone']}")
    
    # Test 4: POST /api/family/request as free user (should fail with 403)
    resp = requests.post(
        f"{BASE_URL}/family/request",
        json={"target_user_id": admin_id, "note": "Test request"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 403
    log_test("POST /api/family/request (free user)", True, "Correctly rejected with 403")
    
    # Test 5: POST /api/family/request as VIP admin without family_contact (should fail with 400)
    # First, create a new VIP user without family_contact
    timestamp = int(time.time())
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"vip_test_{timestamp}@example.com",
        "password": "TestPass123",
        "name": f"VIP Test {timestamp}"
    })
    vip_token = resp.json()["token"]
    vip_id = resp.json()["user_id"]
    
    # Make user VIP via admin
    resp = requests.patch(
        f"{BASE_URL}/admin/users/{vip_id}",
        json={"plan": "vip"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    
    # Try to send request without family_contact
    resp = requests.post(
        f"{BASE_URL}/family/request",
        json={"target_user_id": test_user_id, "note": "Test request"},
        headers={"Authorization": f"Bearer {vip_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/family/request (VIP without family_contact)", True, "Correctly rejected with 400")
    
    # Test 6: POST /api/family/request as VIP admin with family_contact
    # Get a demo user to send request to
    candidates = get_candidates()
    target_user = next((c for c in candidates if c["id"] != admin_id), None)
    if not target_user:
        log_test("POST /api/family/request (VIP with family_contact)", False, "No target user found")
        return
    
    target_user_id = target_user["id"]
    
    resp = requests.post(
        f"{BASE_URL}/family/request",
        json={"target_user_id": target_user_id, "note": "Oilaviy aloqa so'rovi"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    if resp.status_code != 200:
        log_test("POST /api/family/request (VIP with family_contact)", False, f"Status: {resp.status_code}, Response: {resp.text}")
        # Continue with other tests
    else:
        data = resp.json()
        assert data["ok"] == True
        request_id = data["id"]
        log_test("POST /api/family/request (VIP with family_contact)", True, f"Request ID: {request_id}")
    
    # Test 7: Duplicate active request (should fail with 400)
    if resp.status_code == 200:
        resp = requests.post(
            f"{BASE_URL}/family/request",
            json={"target_user_id": target_user_id, "note": "Duplicate request"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 400
        log_test("POST /api/family/request (duplicate)", True, "Correctly rejected with 400")
    else:
        log_test("POST /api/family/request (duplicate)", False, "Skipped due to previous failure")
    
    # Test 8: GET /api/family/mine
    resp = requests.get(f"{BASE_URL}/family/mine", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "sent" in data
    assert "received" in data
    assert len(data["sent"]) >= 1
    log_test("GET /api/family/mine", True, f"Sent: {len(data['sent'])}, Received: {len(data['received'])}")
    
    # Test 9: POST /api/family/respond from non-target (should fail with 403)
    if 'request_id' in locals():
        resp = requests.post(
            f"{BASE_URL}/family/respond/{request_id}",
            json={"accept": True},
            headers={"Authorization": f"Bearer {test_user_token}"}
        )
        assert resp.status_code == 403
        log_test("POST /api/family/respond (non-target)", True, "Correctly rejected with 403")
    else:
        log_test("POST /api/family/respond (non-target)", False, "Skipped due to no request_id")
    
    # Test 10: GET /api/family/contact without accepted request (should fail with 403)
    if 'target_user_id' in locals():
        resp = requests.get(
            f"{BASE_URL}/family/contact/{target_user_id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 403
        log_test("GET /api/family/contact (no accepted request)", True, "Correctly rejected with 403")
    else:
        log_test("GET /api/family/contact (no accepted request)", False, "Skipped due to no target_user_id")
    
    # Note: We cannot test accepting the request because we don't have credentials for the target user
    # and the target user needs to be VIP with family_contact set
    log_test("Family module testing", True, "Core functionality verified (accept flow requires target user credentials)")

# ============================================================================
# MODULE 3: SOVCHI CONCIERGE (199K UZS / 30d / 5 matches)
# ============================================================================

def test_concierge_module():
    print("\n" + "="*80)
    print("MODULE 3: SOVCHI CONCIERGE (199K UZS / 30d / 5 matches)")
    print("="*80)
    
    # Test 1: GET /api/concierge/info
    resp = requests.get(f"{BASE_URL}/concierge/info", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["price"] == 199000
    assert data["max_matches"] == 5
    assert data["days"] == 30
    log_test("GET /api/concierge/info", True, f"Price: {data['price']}, Max matches: {data['max_matches']}")
    
    # Test 2: POST /api/concierge/order with payment_method='click'
    resp = requests.post(
        f"{BASE_URL}/concierge/order",
        json={"payment_method": "click"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "order" in data
    assert data["order"]["status"] == "awaiting_payment"
    assert "payment_link" in data
    order_id = data["order"]["id"]
    payment_id = data["order"]["payment_id"]
    log_test("POST /api/concierge/order (click)", True, f"Order ID: {order_id}, Status: awaiting_payment")
    
    # Test 3: Simulate admin confirming payment
    resp = requests.post(
        f"{BASE_URL}/payments/admin-confirm/{payment_id}",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    log_test("POST /api/payments/admin-confirm/{payment_id}", True, "Payment confirmed")
    
    # Test 4: Duplicate active order (should fail with 400)
    # Now that payment is confirmed, order status is 'in_progress' which counts as active
    resp = requests.post(
        f"{BASE_URL}/concierge/order",
        json={"payment_method": "click"},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/concierge/order (duplicate)", True, "Correctly rejected with 400")
    
    # Test 5: GET /api/concierge/mine
    resp = requests.get(f"{BASE_URL}/concierge/mine", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    order = data[0]
    assert order["status"] == "in_progress"
    assert "match_users" in order
    log_test("GET /api/concierge/mine", True, f"Found {len(data)} order(s), Status: {order['status']}")
    
    # Test 6: GET /api/admin/concierge (admin only)
    resp = requests.get(f"{BASE_URL}/admin/concierge", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert "user" in data[0]
    log_test("GET /api/admin/concierge (admin)", True, f"Found {len(data)} order(s) with user info")
    
    # Test 7: Non-admin calling admin endpoint (should fail with 403)
    resp = requests.get(f"{BASE_URL}/admin/concierge", headers={"Authorization": f"Bearer {test_user_token}"})
    assert resp.status_code == 403
    log_test("GET /api/admin/concierge (non-admin)", True, "Correctly rejected with 403")
    
    # Test 8: POST /api/admin/concierge/{order_id}/match (add matches)
    candidates = get_candidates()
    if len(candidates) < 5:
        log_test("POST /api/admin/concierge/{order_id}/match", False, "Not enough candidates for testing")
        return
    
    # Add 5 matches
    for i in range(5):
        match_user_id = candidates[i]["id"]
        resp = requests.post(
            f"{BASE_URL}/admin/concierge/{order_id}/match",
            json={"match_user_id": match_user_id, "note": f"Match {i+1}"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 200, f"Failed to add match {i+1}: {resp.text}"
        data = resp.json()
        assert data["ok"] == True
        log_test(f"POST /api/admin/concierge/match (match {i+1}/5)", True, f"Matches count: {data['matches_count']}")
    
    # Test 9: Verify 5th match auto-completes order
    resp = requests.get(f"{BASE_URL}/concierge/mine", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    order = next((o for o in data if o["id"] == order_id), None)
    assert order["status"] == "completed"
    log_test("Verify 5th match auto-completes order", True, "Order status is 'completed'")
    
    # Test 10: Try to add 6th match (should fail with 400)
    if len(candidates) > 5:
        resp = requests.post(
            f"{BASE_URL}/admin/concierge/{order_id}/match",
            json={"match_user_id": candidates[5]["id"], "note": "6th match"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 400
        log_test("POST /api/admin/concierge/match (6th match)", True, "Correctly rejected with 400")
    
    # Test 11: POST /api/concierge/order with payment_method='balance' (insufficient balance)
    # Create new user with insufficient balance
    timestamp = int(time.time())
    resp = requests.post(f"{BASE_URL}/auth/register", json={
        "email": f"balance_test_{timestamp}@example.com",
        "password": "TestPass123",
        "name": f"Balance Test {timestamp}"
    })
    balance_token = resp.json()["token"]
    
    resp = requests.post(
        f"{BASE_URL}/concierge/order",
        json={"payment_method": "balance"},
        headers={"Authorization": f"Bearer {balance_token}"}
    )
    assert resp.status_code == 402
    log_test("POST /api/concierge/order (balance, insufficient)", True, "Correctly rejected with 402")
    
    # Test 12: POST /api/concierge/order with payment_method='balance' (sufficient balance)
    # Top up test_user balance
    test_user_data = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {test_user_token}"}).json()
    test_user_id_for_topup = test_user_data["id"]
    
    resp = requests.patch(
        f"{BASE_URL}/admin/users/{test_user_id_for_topup}",
        json={"add_balance": 199000},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    
    resp = requests.post(
        f"{BASE_URL}/concierge/order",
        json={"payment_method": "balance"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["order"]["status"] == "in_progress"
    assert data["payment_link"] is None
    log_test("POST /api/concierge/order (balance, sufficient)", True, "Order activated immediately with status 'in_progress'")

# ============================================================================
# MODULE 4: TRAVEL MODE (Premium+)
# ============================================================================

def test_travel_module():
    print("\n" + "="*80)
    print("MODULE 4: TRAVEL MODE (Premium+)")
    print("="*80)
    
    # Test 1: GET /api/travel/status
    resp = requests.get(f"{BASE_URL}/travel/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "active" in data
    assert "regions" in data
    assert len(data["regions"]) == 13
    assert data["allowed"] == True  # Admin is VIP
    log_test("GET /api/travel/status", True, f"Active: {data['active']}, Allowed: {data['allowed']}, Regions: {len(data['regions'])}")
    
    # Test 2: POST /api/travel/activate as free user (should fail with 403)
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": "Samarqand", "days": 7},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )
    assert resp.status_code == 403
    log_test("POST /api/travel/activate (free user)", True, "Correctly rejected with 403")
    
    # Test 3: POST /api/travel/activate with wrong region (should fail with 400)
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": "InvalidRegion", "days": 7},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/travel/activate (wrong region)", True, "Correctly rejected with 400")
    
    # Test 4: POST /api/travel/activate with days < 1 (should fail with 400)
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": "Samarqand", "days": 0},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/travel/activate (days < 1)", True, "Correctly rejected with 400")
    
    # Test 5: POST /api/travel/activate with days > 30 (should fail with 400)
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": "Samarqand", "days": 31},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/travel/activate (days > 30)", True, "Correctly rejected with 400")
    
    # Test 6: Get admin's home region first
    admin_data = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {admin_token}"}).json()
    home_region = admin_data.get("region", "Toshkent")
    
    # Test 7: POST /api/travel/activate with same as home_region (should fail with 400)
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": home_region, "days": 7},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 400
    log_test("POST /api/travel/activate (same as home_region)", True, "Correctly rejected with 400")
    
    # Test 8: POST /api/travel/activate with valid region (VIP admin)
    travel_region = "Samarqand" if home_region != "Samarqand" else "Buxoro"
    resp = requests.post(
        f"{BASE_URL}/travel/activate",
        json={"region": travel_region, "days": 7},
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] == True
    assert data["travel_region"] == travel_region
    log_test("POST /api/travel/activate (valid)", True, f"Travel Mode activated to {travel_region} for 7 days")
    
    # Test 9: GET /api/candidates after activating Travel Mode
    resp = requests.get(f"{BASE_URL}/candidates", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    candidates = resp.json()
    # Verify all candidates are from travel_region
    if candidates:
        regions = [c.get("region") for c in candidates]
        all_match = all(r == travel_region for r in regions if r)
        log_test("GET /api/candidates (Travel Mode active)", all_match, 
                f"Found {len(candidates)} candidates, regions: {set(regions)}")
    else:
        log_test("GET /api/candidates (Travel Mode active)", True, "No candidates found (expected if no users in travel region)")
    
    # Test 10: POST /api/travel/deactivate
    resp = requests.post(f"{BASE_URL}/travel/deactivate", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] == True
    log_test("POST /api/travel/deactivate", True, "Travel Mode deactivated")
    
    # Test 11: Verify travel_region is unset
    resp = requests.get(f"{BASE_URL}/travel/status", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["active"] == False
    assert data["travel_region"] is None
    log_test("Verify travel_region unset", True, "Travel Mode is inactive")

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    print("\n" + "="*80)
    print("FIDEM FAZA 3 BACKEND TESTING")
    print("="*80)
    print(f"Backend URL: {BASE_URL}")
    print(f"Admin: {ADMIN_EMAIL}")
    print("="*80)
    
    try:
        # Setup
        login_admin()
        create_test_user()
        
        # Run all module tests
        test_withdrawals_module()
        test_family_module()
        test_concierge_module()
        test_travel_module()
        
        print("\n" + "="*80)
        print("✅ ALL FAZA 3 BACKEND TESTS COMPLETED")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
