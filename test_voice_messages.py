#!/usr/bin/env python3
"""
Voice Messages Backend Testing
Tests the new kind='voice' message type end-to-end
"""
import requests
import json
from datetime import datetime

# Backend URL from frontend/.env
BACKEND_URL = "https://loyihani-clone.preview.emergentagent.com"
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
        return None, None
    
    data = response.json()
    token = data.get("token")
    user_id = data.get("user_id")
    is_admin = data.get("is_admin", False)
    
    print(f"✅ Login successful")
    print(f"   user_id: {user_id}")
    print(f"   is_admin: {is_admin}")
    print(f"   token: {token[:20]}...")
    
    return token, user_id

def test_1_send_voice_message(token, admin_id):
    """
    Test 1: Send voice message
    POST /api/messages/send with kind='voice', voice_url, voice_duration
    Expected: 200 OK (no text moderation should run, no 422)
    """
    print("\n" + "="*80)
    print("TEST 1: SEND VOICE MESSAGE")
    print("="*80)
    
    # First, get a candidate to send message to
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{API_BASE}/candidates", headers=headers, timeout=10)
    
    if response.status_code != 200:
        return log_test("GET /api/candidates", False, f"Status {response.status_code}: {response.text}")
    
    candidates = response.json()
    if not candidates or len(candidates) == 0:
        return log_test("GET /api/candidates", False, "No candidates found")
    
    candidate_id = candidates[0]["id"]
    candidate_name = candidates[0]["name"]
    print(f"✅ Found candidate: {candidate_name} (id: {candidate_id})")
    
    # Send voice message
    voice_payload = {
        "to_user_id": candidate_id,
        "text": "",
        "kind": "voice",
        "voice_url": "https://example.com/test-voice.webm",
        "voice_duration": 12
    }
    
    print(f"\nSending voice message:")
    print(f"   to_user_id: {candidate_id}")
    print(f"   kind: voice")
    print(f"   voice_url: https://example.com/test-voice.webm")
    print(f"   voice_duration: 12")
    
    response = requests.post(
        f"{API_BASE}/messages/send",
        json=voice_payload,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        return log_test("POST /api/messages/send (voice)", False, 
                       f"Status {response.status_code}: {response.text}")
    
    data = response.json()
    print(f"\n✅ Voice message sent successfully")
    print(f"   message_id: {data.get('id')}")
    print(f"   kind: {data.get('kind')}")
    print(f"   chat_id: {data.get('chat_id')}")
    
    # Verify response structure
    if data.get("kind") != "voice":
        return log_test("Voice message kind", False, f"Expected 'voice', got '{data.get('kind')}'")
    
    return log_test("Send voice message", True, "Voice message sent successfully"), candidate_id, data.get("chat_id")

def test_2_voice_message_persisted(token, admin_id, candidate_id, chat_id):
    """
    Test 2: Voice message persisted with meta
    GET /api/messages/<chat_id>
    Verify: kind == "voice", meta.voice_url, meta.voice_duration
    """
    print("\n" + "="*80)
    print("TEST 2: VOICE MESSAGE PERSISTED WITH META")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    print(f"Fetching messages for chat_id: {chat_id}")
    response = requests.get(
        f"{API_BASE}/messages/{chat_id}",
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        return log_test("GET /api/messages/{chat_id}", False, 
                       f"Status {response.status_code}: {response.text}")
    
    messages = response.json()
    print(f"✅ Retrieved {len(messages)} messages")
    
    # Find the voice message
    voice_message = None
    for msg in messages:
        if msg.get("kind") == "voice":
            voice_message = msg
            break
    
    if not voice_message:
        return log_test("Find voice message", False, "No voice message found in chat history")
    
    print(f"\n✅ Found voice message:")
    print(f"   id: {voice_message.get('id')}")
    print(f"   kind: {voice_message.get('kind')}")
    print(f"   meta: {json.dumps(voice_message.get('meta', {}), indent=6)}")
    
    # Verify kind
    if voice_message.get("kind") != "voice":
        return log_test("Voice message kind", False, 
                       f"Expected 'voice', got '{voice_message.get('kind')}'")
    
    # Verify meta.voice_url
    meta = voice_message.get("meta", {})
    if not meta:
        return log_test("Voice message meta", False, "meta field is missing or empty")
    
    if meta.get("voice_url") != "https://example.com/test-voice.webm":
        return log_test("Voice message meta.voice_url", False, 
                       f"Expected 'https://example.com/test-voice.webm', got '{meta.get('voice_url')}'")
    
    # Verify meta.voice_duration
    if meta.get("voice_duration") != 12:
        return log_test("Voice message meta.voice_duration", False, 
                       f"Expected 12, got {meta.get('voice_duration')}")
    
    return log_test("Voice message persisted with meta", True, 
                   "All fields verified: kind='voice', meta.voice_url, meta.voice_duration")

def test_3_validation(token, candidate_id):
    """
    Test 3: Validation
    1. Missing voice_url → 400
    2. Duration too long (>60s) → 400
    3. Valid duration (10s) → 200
    """
    print("\n" + "="*80)
    print("TEST 3: VALIDATION")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test 3.1: Missing voice_url
    print("\n--- Test 3.1: Missing voice_url ---")
    payload = {
        "to_user_id": candidate_id,
        "text": "",
        "kind": "voice",
        "voice_url": "",
        "voice_duration": 5
    }
    
    response = requests.post(
        f"{API_BASE}/messages/send",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 400:
        log_test("Missing voice_url validation", False, 
                f"Expected 400, got {response.status_code}: {response.text}")
    else:
        log_test("Missing voice_url validation", True, 
                f"Correctly rejected with 400: {response.json().get('detail', response.text)}")
    
    # Test 3.2: Duration too long
    print("\n--- Test 3.2: Duration too long (90s) ---")
    payload = {
        "to_user_id": candidate_id,
        "text": "",
        "kind": "voice",
        "voice_url": "http://x/v.webm",
        "voice_duration": 90
    }
    
    response = requests.post(
        f"{API_BASE}/messages/send",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 400:
        log_test("Duration too long validation", False, 
                f"Expected 400, got {response.status_code}: {response.text}")
    else:
        log_test("Duration too long validation", True, 
                f"Correctly rejected with 400: {response.json().get('detail', response.text)}")
    
    # Test 3.3: Valid duration
    print("\n--- Test 3.3: Valid duration (10s) ---")
    payload = {
        "to_user_id": candidate_id,
        "text": "",
        "kind": "voice",
        "voice_url": "http://x/v.webm",
        "voice_duration": 10
    }
    
    response = requests.post(
        f"{API_BASE}/messages/send",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 200:
        return log_test("Valid voice message", False, 
                       f"Expected 200, got {response.status_code}: {response.text}")
    
    return log_test("Valid voice message", True, "Voice message with 10s duration accepted")

def test_4_text_moderation_still_works(token, candidate_id):
    """
    Test 4: Text moderation still works for kind='text'
    POST /api/messages/send with phone number in text → 422
    """
    print("\n" + "="*80)
    print("TEST 4: TEXT MODERATION STILL WORKS")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Send message with phone number (should be blocked)
    payload = {
        "to_user_id": candidate_id,
        "text": "+998901234567 telefon raqamim",
        "kind": "text"
    }
    
    print(f"Sending text message with phone number:")
    print(f"   text: {payload['text']}")
    
    response = requests.post(
        f"{API_BASE}/messages/send",
        json=payload,
        headers=headers,
        timeout=10
    )
    
    if response.status_code != 422:
        return log_test("Text moderation (phone block)", False, 
                       f"Expected 422, got {response.status_code}: {response.text}")
    
    error_detail = response.json().get("detail", "")
    print(f"✅ Message correctly blocked with 422")
    print(f"   Error: {error_detail}")
    
    return log_test("Text moderation still works", True, 
                   f"Phone number correctly blocked: {error_detail}")

def test_5_regression_existing_endpoints(token):
    """
    Test 5: Regression - existing endpoints still work
    - GET /api/ → 200
    - POST /api/auth/login → 200
    - GET /api/candidates → list
    - GET /api/gifts/catalog → 12 items
    - GET /api/referral/mine → all keys present
    """
    print("\n" + "="*80)
    print("TEST 5: REGRESSION - EXISTING ENDPOINTS")
    print("="*80)
    
    headers = {"Authorization": f"Bearer {token}"}
    all_passed = True
    
    # Test 5.1: GET /api/
    print("\n--- Test 5.1: GET /api/ ---")
    response = requests.get(f"{API_BASE}/", timeout=10)
    if response.status_code != 200:
        log_test("GET /api/", False, f"Status {response.status_code}")
        all_passed = False
    else:
        log_test("GET /api/", True, f"Response: {response.json()}")
    
    # Test 5.2: POST /api/auth/login
    print("\n--- Test 5.2: POST /api/auth/login ---")
    response = requests.post(
        f"{API_BASE}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code != 200:
        log_test("POST /api/auth/login", False, f"Status {response.status_code}")
        all_passed = False
    else:
        log_test("POST /api/auth/login", True, "Login successful")
    
    # Test 5.3: GET /api/candidates
    print("\n--- Test 5.3: GET /api/candidates ---")
    response = requests.get(f"{API_BASE}/candidates", headers=headers, timeout=10)
    if response.status_code != 200:
        log_test("GET /api/candidates", False, f"Status {response.status_code}")
        all_passed = False
    else:
        candidates = response.json()
        log_test("GET /api/candidates", True, f"Retrieved {len(candidates)} candidates")
    
    # Test 5.4: GET /api/gifts/catalog
    print("\n--- Test 5.4: GET /api/gifts/catalog ---")
    response = requests.get(f"{API_BASE}/gifts/catalog", headers=headers, timeout=10)
    if response.status_code != 200:
        log_test("GET /api/gifts/catalog", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        items = data.get("items", [])
        if len(items) != 12:
            log_test("GET /api/gifts/catalog", False, f"Expected 12 items, got {len(items)}")
            all_passed = False
        else:
            log_test("GET /api/gifts/catalog", True, f"Retrieved {len(items)} gift items")
    
    # Test 5.5: GET /api/referral/mine
    print("\n--- Test 5.5: GET /api/referral/mine ---")
    response = requests.get(f"{API_BASE}/referral/mine", headers=headers, timeout=10)
    if response.status_code != 200:
        log_test("GET /api/referral/mine", False, f"Status {response.status_code}")
        all_passed = False
    else:
        data = response.json()
        required_keys = ["code", "link", "invited_count", "invites_count", 
                        "bonus_per_invite", "earned", "vip_bonus_threshold"]
        missing_keys = [k for k in required_keys if k not in data]
        if missing_keys:
            log_test("GET /api/referral/mine", False, f"Missing keys: {missing_keys}")
            all_passed = False
        else:
            log_test("GET /api/referral/mine", True, "All required keys present")
    
    return all_passed

def main():
    """Run all voice message tests"""
    print("\n" + "="*80)
    print("VOICE MESSAGES BACKEND TESTING")
    print("Testing kind='voice' message type end-to-end")
    print("="*80)
    
    # Authenticate
    token, admin_id = get_admin_token()
    if not token:
        print("\n❌ FATAL: Authentication failed. Cannot proceed with tests.")
        return
    
    # Test 1: Send voice message
    result = test_1_send_voice_message(token, admin_id)
    if not result[0]:
        print("\n❌ FATAL: Test 1 failed. Cannot proceed with dependent tests.")
        return
    
    _, candidate_id, chat_id = result
    
    # Test 2: Voice message persisted with meta
    test_2_voice_message_persisted(token, admin_id, candidate_id, chat_id)
    
    # Test 3: Validation
    test_3_validation(token, candidate_id)
    
    # Test 4: Text moderation still works
    test_4_text_moderation_still_works(token, candidate_id)
    
    # Test 5: Regression tests
    test_5_regression_existing_endpoints(token)
    
    print("\n" + "="*80)
    print("VOICE MESSAGES TESTING COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()
