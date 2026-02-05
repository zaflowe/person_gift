"""Test Weekly System Task Logic."""
import sys
import os
sys.path.append(os.getcwd())

import requests
from datetime import datetime

BASE_URL = "http://localhost:8000/api"

def test_weekly_system_task():
    print("\n" + "="*50)
    print("Testing Weekly System Task Auto-Generation")
    print("="*50)

    # Login
    try:
        auth_resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "password"})
        if auth_resp.status_code == 200:
            token = auth_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful")
        else:
            print(f"⚠️ Login failed: {auth_resp.status_code}")
            return
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # Trigger System Check
    print("\nTriggering weekly system check...")
    try:
        resp = requests.post(f"{BASE_URL}/tasks/weekly-system-check", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Request successful")
            if data["created"]:
                print(f"  ✨ Logic: New task CREATED")
                print(f"  - Title: {data['task']['title']}")
                print(f"  - Deadline: {data['task']['deadline']}")
            else:
                print(f"  ℹ️ Logic: Task ALREADY EXISTS")
                print(f"  - Title: {data['task']['title']}")
        else:
            print(f"❌ Request failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_weekly_system_task()
