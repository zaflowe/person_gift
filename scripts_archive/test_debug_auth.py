import requests
import sys

BASE_URL = "http://localhost:8000/api/auth"

def run_test():
    print("Testing Auth Flow...")
    
    # 1. Register
    username = "debug_user_v2"
    password = "password123"
    print(f"1. Registering {username}...")
    try:
        resp = requests.post(f"{BASE_URL}/register", json={"username": username, "password": password})
        if resp.status_code == 201:
            print("   Success")
        elif resp.status_code == 400 and "already exists" in resp.text:
            print("   User exists, proceeding to login")
        else:
            print(f"   Failed: {resp.status_code} {resp.text}")
            return
    except Exception as e:
        print(f"   Connection failed: {e}")
        return

    # 2. Login
    print("2. Logging in...")
    resp = requests.post(f"{BASE_URL}/login", data={"username": username, "password": password})
    if resp.status_code != 200:
        print(f"   Login failed: {resp.status_code} {resp.text}")
        return
    
    token = resp.json()["access_token"]
    print(f"   Got token: {token[:10]}...")

    # 3. Get Me
    print("3. Getting /me...")
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"{BASE_URL}/me", headers=headers)
    
    if resp.status_code == 200:
        print("   Success: Got user info")
        print(resp.json())
    else:
        print(f"   FAILED: {resp.status_code}")
        print(f"   Response: {resp.text}")

if __name__ == "__main__":
    run_test()
