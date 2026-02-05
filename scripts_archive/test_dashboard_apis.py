"""Test Dashboard V2 APIs."""
import sys
import os
sys.path.append(os.getcwd())

import requests
from app.config import settings

BASE_URL = "http://localhost:8000/api"
DASHBOARD_URL = f"{BASE_URL}/dashboard"

def test_dashboard_apis():
    print("\n" + "="*50)
    print("Testing Dashboard V2 APIs")
    print("="*50)

    # 1. Login (Mock) -> Assuming mock auth or previous token logic, 
    # but for now let's use the assumption that we can get a token or use mock mode if enabled.
    # Actually, let's just assume we can use the same flow as other tests.
    # For robust testing, we need a valid token.
    # Let's try to login as admin
    try:
        auth_resp = requests.post(f"{BASE_URL}/auth/login", data={"username": "admin", "password": "password"})
        if auth_resp.status_code == 200:
            token = auth_resp.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            print("✅ Login successful")
        else:
            print(f"⚠️ Login failed, trying without auth (if mock mode): {auth_resp.status_code}")
            headers = {}
    except Exception as e:
        print(f"❌ Login failed: {e}")
        return

    # 2. Test Get Strategic Projects
    print("\nAttempting to fetch strategic projects...")
    try:
        resp = requests.get(f"{DASHBOARD_URL}/projects/strategic", headers=headers)
        if resp.status_code == 200:
            projects = resp.json()
            print(f"✅ Fetch strategic projects success. Count: {len(projects)}")
            for p in projects:
                print(f"  - {p['title']} (Progress: {p['progress']}%)")
        else:
            print(f"❌ Fetch strategic projects failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

    # 3. Test Daily Reminder Data
    print("\nAttempting to fetch daily reminder data...")
    try:
        resp = requests.get(f"{DASHBOARD_URL}/daily-reminder-data", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print("✅ Fetch reminder data success")
            print(f"  - Incomplete Tasks: {data['incomplete_tasks']['count']}")
            print(f"  - Overdue Tasks: {data['overdue_tasks']['count']}")
            print(f"  - Due Soon Tasks: {data['due_soon_tasks']['count']}")
            print(f"  - System Task Exists: {data['system_task']['exists']}")
        else:
            print(f"❌ Fetch reminder data failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_dashboard_apis()
