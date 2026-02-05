import requests
import sys

BASE_URL = "http://localhost:8000/api"

def run_test():
    print("Testing System Task...")
    
    # 1. Login (reuse debug user)
    username = "debug_user_v2"
    password = "password123"
    print(f"1. Logging in as {username}...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})
        if resp.status_code != 200:
            # Try registering if missing (db might have been reset?)
            print("   Login failed, trying register...")
            requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": password})
            resp = requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})
            
        if resp.status_code != 200:
            print(f"   Login FAILED: {resp.status_code} {resp.text}")
            return
            
        token = resp.json()["access_token"]
        print(f"   Got token.")
    except Exception as e:
        print(f"   Connection failed: {e}")
        return

    # 2. Call weekly-system-check
    print("2. Calling /tasks/weekly-system-check...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.post(f"{BASE_URL}/tasks/weekly-system-check", headers=headers, json={})
    
    if resp.status_code == 200:
        print("   Success:")
        print(resp.json())
    else:
        print(f"   FAILED: {resp.status_code}")
        print(f"   Response: {resp.text}")

if __name__ == "__main__":
    run_test()
