import requests
import sys

BASE_URL = "http://localhost:8000/api"

def run_test():
    print("Testing System Task New Route...")
    
    username = "debug_user_v2" # reuse
    password = "password123"
    
    # Login
    print("Logging in...")
    try:
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})
        if resp.status_code != 200:
             requests.post(f"{BASE_URL}/auth/register", json={"username": username, "password": password})
             resp = requests.post(f"{BASE_URL}/auth/login", data={"username": username, "password": password})
        
        token = resp.json()["access_token"]
        print("Got token")
    except Exception as e:
        print(f"Login failed: {e}")
        return

    # Call New Route
    print("Calling /system-tasks/weekly-check...")
    try:
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.post(f"http://localhost:8000/api/system-tasks/weekly-check", headers=headers, json={})
        
        if resp.status_code == 200:
            print("Success:")
            print(resp.json())
        else:
            print(f"FAILED: {resp.status_code}")
            print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Call failed: {e}")

if __name__ == "__main__":
    run_test()
