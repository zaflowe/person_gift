"""Test the exemptions quota endpoint specifically."""
import requests

# Login first
print("🔐 Logging in...")
login_data = {"username": "admin", "password": "admin123"}
response = requests.post("http://localhost:8000/api/auth/login", data=login_data)

if response.status_code == 200:
    token = response. json()["access_token"]
    print(f"✅ Got token: {token[:30]}...\n")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test the quota endpoint multiple times
    print("Testing /api/exemptions/quota 10 times...")
    for i in range(10):
        r = requests.get("http://localhost:8000/api/exemptions/quota", headers=headers)
        if r.status_code == 200:
            print(f"  {i+1}. ✅ 200 OK - {r.json()}")
        else:
            print(f"  {i+1}. ❌ {r.status_code} - {r.text}")
else:
    print(f"❌ Login failed: {response.text}")
