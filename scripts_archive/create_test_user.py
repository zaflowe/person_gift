"""Register a test user for testing."""
import requests

BASE_URL = "http://localhost:8000"

print("Creating test user...")
response = requests.post(
    f"{BASE_URL}/api/auth/register",
    json={
        "username": "testuser",
        "email": "test@test.com",
        "password": "testpass123"
    }
)

if response.status_code == 201:
    print("✅ Test user created successfully")
    print(response.json())
else:
    print(f"Response: {response.status_code}")
    print(response.text)
