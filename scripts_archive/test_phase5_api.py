import requests
import json
import uuid
from datetime import datetime

BASE_URL = "http://localhost:8000"

# Mock login to get token (assuming test user exists, otherwise utilize existing pattern)
# For simplicity, we assume we can login with hardcoded credentials or just create one.
# Let's try to reuse the pattern from test_schedule_intent.py

def get_auth_token():
    user_creds = {
        "username": "testuser_v5",
        "password": "password123"
    }
    
    # Try Login
    login_data = user_creds
    response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
    
    if response.status_code == 200:
        return response.json()["access_token"]
    
    print(f"Login failed ({response.status_code}), attempting registration...")
    
    # Try Register
    reg_data = {
        "username": user_creds["username"],
        "password": user_creds["password"],
        "email": "test@example.com" # Assuming email optional or needed? UserCreate usually needs it?
        # Check UserCreate schema? Assume basic fields.
    }
    # UserCreate schema usually match params.
    # Let's try basic register
    response = requests.post(f"{BASE_URL}/api/auth/register", json=reg_data)
    
    if response.status_code == 201:
        print("Registration successful!")
        # Login again
        response = requests.post(f"{BASE_URL}/api/auth/login", data=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]
            
    print(f"Registration/Login failed: {response.text}")
    return None

def test_metrics(token):
    print("\n--- Testing Metrics ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Entry
    data = {
        "metric_type": "weight",
        "value": 75.5,
        "unit": "kg",
        "notes": "Test entry"
    }
    res = requests.post(f"{BASE_URL}/api/metrics/entry", json=data, headers=headers)
    print(f"Create Metric: {res.status_code}")
    if res.status_code == 200:
        print(res.json())
        
    # Get History
    res = requests.get(f"{BASE_URL}/api/metrics/history?metric_type=weight", headers=headers)
    print(f"Get History: {res.status_code}")
    if res.status_code == 200:
        hist = res.json()
        print(f"Found {len(hist)} entries")

def test_study(token):
    print("\n--- Testing Study ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Create Session
    data = {
        "created_at": datetime.now().isoformat(),
        "duration_sec": 1500, # 25 min
        "status": "completed",
        "custom_label": "Test Focus"
    }
    res = requests.post(f"{BASE_URL}/api/study/sessions", json=data, headers=headers)
    print(f"Create Session: {res.status_code}")
    if res.status_code == 200:
        print(res.json())

    # Get Stats
    res = requests.get(f"{BASE_URL}/api/study/stats", headers=headers)
    print(f"Get Stats: {res.status_code}")
    if res.status_code == 200:
        print(res.json())

def test_conversation_persistence(token):
    print("\n--- Testing Conversation Persistence ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get Current
    res = requests.get(f"{BASE_URL}/api/conversation/current", headers=headers)
    print(f"Get Current: {res.status_code}")
    if res.status_code == 200:
        print("Current Conversation ID:", res.json().get("conversation_id"))

    # Reset
    res = requests.post(f"{BASE_URL}/api/conversation/reset", json={}, headers=headers)
    print(f"Reset: {res.status_code}")
    if res.status_code == 200:
        print("New Conversation ID:", res.json().get("conversation_id"))

if __name__ == "__main__":
    token = get_auth_token()
    if token:
        test_metrics(token)
        test_study(token)
        test_conversation_persistence(token)
    else:
        print("Skipping tests due to auth failure")
