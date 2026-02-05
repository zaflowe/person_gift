
import requests
import json
import sys

# Configuration
BASE_URL = "http://127.0.0.1:8000"
API_URL = f"{BASE_URL}/api/conversation/chat"


def test_view_schedule_intent():
    print("Testing view_schedule intent...")
    
    # Login first
    try:
        login_res = requests.post(f"{BASE_URL}/api/auth/login", data={"username": "testuser", "password": "testpass123"})
        if login_res.status_code != 200:
            print("❌ Login failed (testuser/testpass123)")
            return False
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"❌ Login error: {e}")
        return False

    # 1. Start a new conversation
    payload = {
        "message": "查看今天的日程安排"
    }
    
    try:
        response = requests.post(API_URL, json=payload, headers=headers)
        if response.status_code != 200:
            print(f"❌ API Error: {response.status_code} {response.text}")
            return False
            
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
        # Check intent
        if data.get("intent") == "view_schedule":
            print("✅ Intent recognized correctly: view_schedule")
        else:
            print(f"❌ Intent mismatch. Expected 'view_schedule', got '{data.get('intent')}'")
            return False
            
        # Check message content (it should contain schedule info or 'no schedule' message)
        msg = data.get("message", "")
        if "安排" in msg or "日程" in msg:
             print("✅ Response contains schedule related text")
        else:
             print("⚠️ Response might not be about schedule")
             
        return True
        
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_view_schedule_intent()
    sys.exit(0 if success else 1)
