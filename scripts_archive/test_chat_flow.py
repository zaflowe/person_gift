"""Complete end-to-end test for chat planner flow."""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

# Step 1: Login
print("=" * 60)
print("Step 1: Login")
print("=" * 60)

login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    data={"username": "testuser", "password": "testpass123"}  # OAuth2 requires form-data
)
assert login_response.status_code == 200, f"Login failed: {login_response.text}"
token = login_response.json()["access_token"]
print(f"✅ Login successful, token: {token[:20]}...")

headers = {"Authorization": f"Bearer {token}"}

# Step 2: Send chat message (complex intent)
print("\n" + "=" * 60)
print("Step 2: Send chat message - complex project")
print("=" * 60)

chat_payload = {
    "message": "我要考安徽大学人工智能学院里控制科学与工程的硕士",
    "conversation_id": None
}

chat_response = requests.post(
    f"{BASE_URL}/api/conversation/chat",
    json=chat_payload,
    headers=headers
)
assert chat_response.status_code == 200, f"Chat failed: {chat_response.text}"
chat_result = chat_response.json()

print(f"✅ Chat successful")
print(f"   Action: {chat_result['action_type']}")
print(f"   Message: {chat_result['message']}")
print(f"   Conversation ID: {chat_result['conversation_id']}")

if chat_result['action_type'] == 'ask_more':
    # Need more info
    print("\n   AI is asking for more information...")
    conversation_id = chat_result['conversation_id']
    
    # Send additional info
    chat_payload2 = {
        "message": "请生成计划",
        "conversation_id": conversation_id
    }
    
    chat_response2 = requests.post(
        f"{BASE_URL}/api/conversation/chat",
        json=chat_payload2,
        headers=headers
    )
    assert chat_response2.status_code == 200, f"Chat 2 failed: {chat_response2.text}"
    chat_result = chat_response2.json()
    
    print(f"   Second chat successful")
    print(f"   Action: {chat_result['action_type']}")

# Step 3: Check if plan was generated
if chat_result['action_type'] == 'create_project':
    print("\n" + "=" * 60)
    print("Step 3: Plan generated!")
    print("=" * 60)
    
    session_id = chat_result['conversation_id']
    plan = chat_result['plan']
    
    print(f"   Planning Session ID: {session_id}")
    print(f"   Project: {plan['project']['title']}")
    print(f"   Tasks: {len(plan['tasks'])}")
    for i, task in enumerate(plan['tasks'][:3]):
        print(f"      {i+1}. {task['title']}")
    
    # Step 4: Commit the plan
    print("\n" + "=" * 60)
    print("Step 4: Commit plan")
    print("=" * 60)
    
    commit_payload = {
        "session_id": session_id,
        "plan": plan
    }
    
    print(f"   Sending commit request with session_id: {session_id}")
    
    commit_response = requests.post(
        f"{BASE_URL}/api/planner/commit",
        json=commit_payload,
        headers=headers
    )
    
    print(f"   Response status: {commit_response.status_code}")
    print(f"   Response: {commit_response.text[:500]}")
    
    if commit_response.status_code == 200:
        commit_result = commit_response.json()
        print(f"\n✅ SUCCESS! Plan committed!")
        print(f"   Project ID: {commit_result['project_id']}")
        print(f"   Created {len(commit_result['task_ids'])} tasks")
        
        # Step 5: Verify project exists
        print("\n" + "=" * 60)
        print("Step 5: Verify project created")
        print("=" * 60)
        
        project_response = requests.get(
            f"{BASE_URL}/api/projects/{commit_result['project_id']}",
            headers=headers
        )
        
        if project_response.status_code == 200:
            project = project_response.json()
            print(f"✅ Project verified: {project['title']}")
            print(f"   Status: {project['status']}")
        else:
            print(f"❌ Failed to get project: {project_response.text}")
    else:
        print(f"\n❌ COMMIT FAILED!")
        print(f"   Error: {commit_response.text}")
        
        # Debug: Check if session exists in database
        print("\n" + "=" * 60)
        print("Debug: Checking database")
        print("=" * 60)
        import sqlite3
        conn = sqlite3.connect('data/person_gift.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, user_id, message FROM planning_sessions WHERE id = ?", (session_id,))
        result = cursor.fetchone()
        
        if result:
            print(f"✅ PlanningSession EXISTS in database")
            print(f"   ID: {result[0]}")
            print(f"   User ID: {result[1]}")
            print(f"   Message: {result[2][:50]}...")
        else:
            print(f"❌ PlanningSession NOT FOUND in database")
            print(f"   Searched for ID: {session_id}")
            
            # List all sessions
            cursor.execute("SELECT id, created_at FROM planning_sessions ORDER BY created_at DESC LIMIT 5")
            sessions = cursor.fetchall()
            print(f"\n   Recent sessions:")
            for sess in sessions:
                print(f"      {sess[0]} - {sess[1]}")
        
        conn.close()
else:
    print(f"\n❌ Unexpected action type: {chat_result['action_type']}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
