"""Test admin login and schedule API."""
import requests
import traceback

def test():
    print("Testing Login for 'admin'...")
    username = "admin"
    password = "admin123"
    
    try:
        # 1. Login
        login_resp = requests.post(
            "http://localhost:8000/api/auth/login",
            data={"username": username, "password": password}
        )
        
        print(f"Login Status: {login_resp.status_code}")
        
        if login_resp.status_code != 200:
            print(f"❌ Login Failed: {login_resp.text}")
            # Try to register just in case (though create_admin should have done it)
            print("Attempting to register admin to verify DB state...")
            reg_resp = requests.post(
                "http://localhost:8000/api/auth/register",
                json={"username": username, "password": password, "email": "admin@example.com"}
            )
            print(f"Register Status: {reg_resp.status_code} - {reg_resp.text}")
            return

        print("✅ Login Successful")
        token = login_resp.json()["access_token"]
        
        # 2. Test Schedule
        print("\nTesting /api/schedule/today...")
        resp = requests.get(
            "http://localhost:8000/api/schedule/today",
            headers={"Authorization": f"Bearer {token}"}
        )
        print(f"Schedule Status: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ Schedule API OK")
            print(resp.json())
        else:
            print(f"❌ Schedule API Failed: {resp.text}")

    except Exception as e:
        print(f"❌ Exception: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    test()
