"""Quick test to verify API endpoints return correct data."""
import requests
import json

# First, login to get a valid token
print("🔐 Logging in...")
login_data = {
    "username": "admin",
    "password": "admin123"
}
response = requests.post(
    "http://localhost:8000/api/auth/login",
    data=login_data
)
print(f"Login status: {response.status_code}")

if response.status_code == 200:
    token = response.json()["access_token"]
    print(f"✅ Token obtained: {token[:20]}...\n")
    
    # Test various endpoints
    headers = {"Authorization": f"Bearer {token}"}
    
    endpoints = [
        "/api/auth/me",
        "/api/tasks",
        "/api/projects",
        "/api/exemptions/quota",
        "/api/dashboard/weekly?weeks=1"
    ]
    
    for endpoint in endpoints:
        print(f"Testing {endpoint}...")
        r = requests.get(f"http://localhost:8000{endpoint}", headers=headers)
        print(f"  Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"  ✅ Data: {json.dumps(data, indent=2, ensure_ascii=False)[:200]}...")
        else:
            print(f"  ❌ Error: {r.text[:100]}")
        print()
else:
    print(f"❌ Login failed: {response.text}")
