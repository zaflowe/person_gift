"""Test script to debug chat endpoint JSON parsing issues."""
import sys
import os
import json
import requests
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

BASE_URL = "http://localhost:8000"

def test_chat_simple_task():
    """Test creating a simple task via chat endpoint."""
    print("\n" + "="*60)
    print("Testing Chat Endpoint: Simple Task Creation")
    print("="*60)
    
    # Step 1: Login/Register to get token
    print("\n[1] Authenticating...")
    auth_response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": "test_user", "password": "test_pass"}
    )
    
    if auth_response.status_code == 401:
        print("   Login failed, attempting registration...")
        reg_response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"username": "test_user", "password": "test_pass"}
        )
        if reg_response.status_code == 200:
            print("   ✅ Registration successful")
            auth_response = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"username": "test_user", "password": "test_pass"}
            )
        else:
            print(f"   ❌ Registration failed: {reg_response.status_code}")
            return
    
    if auth_response.status_code != 200:
        print(f"   ❌ Authentication failed: {auth_response.status_code}")
        return
    
    token = auth_response.json().get("access_token")
    print(f"   ✅ Authenticated, token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: Get current conversation
    print("\n[2] Getting conversation state...")
    conv_response = requests.get(
        f"{BASE_URL}/api/conversation/current",
        headers=headers
    )
    
    if conv_response.status_code != 200:
        print(f"   ❌ Failed to get conversation: {conv_response.status_code}")
        return
    
    conv_data = conv_response.json()
    conversation_id = conv_data.get("conversation_id")
    print(f"   ✅ Conversation ID: {conversation_id}")
    
    # Step 3: Send chat message
    print("\n[3] Sending chat message: '定个八点去吃饭的任务'")
    chat_response = requests.post(
        f"{BASE_URL}/api/conversation/chat",
        headers=headers,
        json={
            "conversation_id": conversation_id,
            "message": "定个八点去吃饭的任务"
        }
    )
    
    print(f"\n   Response Status: {chat_response.status_code}")
    
    if chat_response.status_code == 200:
        print("   ✅ SUCCESS!")
        result = chat_response.json()
        print(f"   Action Type: {result.get('action_type')}")
        print(f"   Message: {result.get('message')[:100]}...")
    else:
        print("   ❌ FAILED!")
        print(f"   Response: {chat_response.text}")
        
        # Try to parse error details
        try:
            error_data = chat_response.json()
            print(f"\n   Error Details:")
            print(f"   {json.dumps(error_data, indent=2, ensure_ascii=False)}")
        except:
            pass

if __name__ == "__main__":
    test_chat_simple_task()
