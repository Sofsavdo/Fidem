#!/usr/bin/env python3
"""Backend API tests for Fidem auth endpoints."""
import os
import sys
import time
import requests
from datetime import datetime

# Read backend URL from frontend/.env
def get_backend_url():
    env_path = "/app/frontend/.env"
    with open(env_path, "r") as f:
        for line in f:
            if line.startswith("REACT_APP_BACKEND_URL="):
                return line.split("=", 1)[1].strip()
    raise ValueError("REACT_APP_BACKEND_URL not found in /app/frontend/.env")

BASE_URL = get_backend_url() + "/api"
print(f"Testing backend at: {BASE_URL}")

# Test credentials from /app/memory/test_credentials.md
ADMIN_EMAIL = "admin@fidem.uz"
ADMIN_PASSWORD = "Admin@123"

# Track test results
results = {
    "passed": [],
    "failed": []
}

def test_result(name, passed, details=""):
    """Record test result."""
    if passed:
        results["passed"].append(name)
        print(f"✅ PASS: {name}")
        if details:
            print(f"   {details}")
    else:
        results["failed"].append(name)
        print(f"❌ FAIL: {name}")
        if details:
            print(f"   {details}")
    print()

def print_summary():
    """Print test summary."""
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    print(f"Passed: {len(results['passed'])}/{len(results['passed']) + len(results['failed'])}")
    print(f"Failed: {len(results['failed'])}/{len(results['passed']) + len(results['failed'])}")
    
    if results['failed']:
        print("\nFailed tests:")
        for test in results['failed']:
            print(f"  - {test}")
    print("="*80 + "\n")

# Test 1: Health check
print("Test 1: Health check - GET /api/")
try:
    response = requests.get(f"{BASE_URL}/", timeout=10)
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "ok" and data.get("service") == "fidem":
            test_result("Health check", True, f"Response: {data}")
        else:
            test_result("Health check", False, f"Unexpected response: {data}")
    else:
        test_result("Health check", False, f"Status code: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Health check", False, f"Exception: {str(e)}")

# Test 2: Admin login
print("Test 2: Admin login - POST /api/auth/login")
admin_token = None
try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if (data.get("token") and 
            data.get("user_id") and 
            data.get("is_admin") == True and 
            data.get("onboarded") == True):
            admin_token = data["token"]
            test_result("Admin login", True, f"Token received, user_id: {data['user_id']}, is_admin: True, onboarded: True")
        else:
            test_result("Admin login", False, f"Missing expected fields: {data}")
    else:
        test_result("Admin login", False, f"Status code: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Admin login", False, f"Exception: {str(e)}")

# Test 3: Wrong password
print("Test 3: Wrong password - POST /api/auth/login")
try:
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": ADMIN_EMAIL, "password": "WrongPassword123!"},
        timeout=10
    )
    if response.status_code == 401:
        test_result("Wrong password", True, f"Correctly returned 401: {response.json()}")
    else:
        test_result("Wrong password", False, f"Expected 401, got {response.status_code}: {response.text}")
except Exception as e:
    test_result("Wrong password", False, f"Exception: {str(e)}")

# Test 4: Register new user
print("Test 4: Register new user - POST /api/auth/register")
timestamp = int(time.time())
new_user_email = f"qa_user_{timestamp}@example.com"
new_user_password = "Test1234!"
new_user_name = "QA User"
new_user_token = None

try:
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": new_user_email,
            "password": new_user_password,
            "name": new_user_name
        },
        timeout=10
    )
    if response.status_code == 200:
        data = response.json()
        if (data.get("token") and 
            data.get("user_id") and 
            data.get("is_admin") == False and 
            data.get("onboarded") == False):
            new_user_token = data["token"]
            test_result("Register new user", True, f"Token received, user_id: {data['user_id']}, is_admin: False, onboarded: False")
        else:
            test_result("Register new user", False, f"Missing expected fields or wrong values: {data}")
    else:
        test_result("Register new user", False, f"Status code: {response.status_code}, Body: {response.text}")
except Exception as e:
    test_result("Register new user", False, f"Exception: {str(e)}")

# Test 5: Duplicate register
print("Test 5: Duplicate register - POST /api/auth/register")
try:
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": new_user_email,
            "password": new_user_password,
            "name": new_user_name
        },
        timeout=10
    )
    if response.status_code == 400:
        test_result("Duplicate register", True, f"Correctly returned 400: {response.json()}")
    else:
        test_result("Duplicate register", False, f"Expected 400, got {response.status_code}: {response.text}")
except Exception as e:
    test_result("Duplicate register", False, f"Exception: {str(e)}")

# Test 6: Auth me with token
print("Test 6: Auth me with token - GET /api/auth/me")
if admin_token:
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("email") == ADMIN_EMAIL and data.get("is_admin") == True:
                test_result("Auth me with token", True, f"User object received: email={data['email']}, is_admin=True")
            else:
                test_result("Auth me with token", False, f"Unexpected user data: {data}")
        else:
            test_result("Auth me with token", False, f"Status code: {response.status_code}, Body: {response.text}")
    except Exception as e:
        test_result("Auth me with token", False, f"Exception: {str(e)}")
else:
    test_result("Auth me with token", False, "Skipped: No admin token available from Test 2")

# Test 7: Auth me without token
print("Test 7: Auth me without token - GET /api/auth/me")
try:
    response = requests.get(f"{BASE_URL}/auth/me", timeout=10)
    if response.status_code == 401:
        test_result("Auth me without token", True, f"Correctly returned 401: {response.json()}")
    else:
        test_result("Auth me without token", False, f"Expected 401, got {response.status_code}: {response.text}")
except Exception as e:
    test_result("Auth me without token", False, f"Exception: {str(e)}")

# Print summary
print_summary()

# Exit with appropriate code
sys.exit(0 if len(results['failed']) == 0 else 1)
