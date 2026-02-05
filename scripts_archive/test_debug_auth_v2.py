import requests
import sys

BASE_URL = "http://localhost:8000/api/auth"

def run_test():
    print("Testing Auth Flow...")
    
    username = "debug_user_v3"
    password = "password123"
    
    # 1. Register
    print(f"1. Registering {username}...")
    try:
        resp = requests.post(f"{BASE_URL}/register", json={"username": username, "password": password})
        if resp.status_code == 201:
            print("   Register Success")
        elif resp.status_code == 400:
            print(f"   Register 400 (Likely exists): {resp.text}")
        else:
            print(f"   Register Failed: {resp.status_code} {resp.text}")
            return
    except Exception as e:
        print(f"   Register Connection failed: {e}")
        return

    # 2. Login
    print("2. Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/login", data={"username": username, "password": password})
        if resp.status_code != 200:
            print(f"   Login failed: {resp.status_code} {resp.text}")
            return
        token = resp.json()["access_token"]
        print(f"   Login Success. Token prefix: {token[:5]}")
    except Exception as e:
         print(f"   Login Connection failed: {e}")
         return

    # 3. Get Me
    print("3. Getting /me...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{BASE_URL}/me", headers=headers)
        
        if resp.status_code == 200:
            print("   Get Me Success: Got user info")
            print(resp.json())
        else:
            print(f"   Get Me FAILED: {resp.status_code}")
            print(f"   Response: {resp.text}")
    except Exception as e:
         print(f"   Get Me Connection failed: {e}")

if __name__ == "__main__":
    run_test()
