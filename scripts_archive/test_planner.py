"""Quick test for Planner API."""
import requests
import json

# Login
print("🔐 Logging in...")
login_resp = requests.post(
    "http://localhost:8000/api/auth/login",
    data={"username": "admin", "password": "admin123"}
)
token = login_resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

print(f"✅ Token: {token[:20]}...\n")

# Test /plan
print("📝 Testing /api/planner/plan...")
plan_resp = requests.post(
    "http://localhost:8000/api/planner/plan",
    headers=headers,
    json={
        "message": "我想学完微积分，目标是3个月",
        "context": {
            "today": "2026-02-01"
        }
    }
)

if plan_resp.status_code == 200:
    plan_data = plan_resp.json()
    print(f"✅ Plan generated!")
    print(f"   Session ID: {plan_data['session_id']}")
    print(f"   Project: {plan_data['plan']['project']['title']}")
    print(f"   Tasks: {len(plan_data['plan']['tasks'])}")
    print(f"\n{json.dumps(plan_data['plan'], indent=2, ensure_ascii=False)}\n")
    
    # Test /commit
    print("💾 Testing /api/planner/commit...")
    commit_resp = requests.post(
        "http://localhost:8000/api/planner/commit",
        headers=headers,
        json={
            "session_id": plan_data["session_id"],
            "plan": plan_data["plan"]
        }
    )
    
    if commit_resp.status_code == 200:
        commit_data = commit_resp.json()
        print(f"✅ Plan committed!")
        print(f"   Project ID: {commit_data['project_id']}")
        print(f"   Task IDs: {commit_data['task_ids']}")
        
        # Verify project was created
        project_resp = requests.get(
            f"http://localhost:8000/api/projects/{commit_data['project_id']}",
            headers=headers
        )
        if project_resp.status_code == 200:
            project = project_resp.json()
            print(f"\n✅ Project verified: {project['title']}")
            print(f"   Status: {project['status']}")
            print(f"   Tasks count: {len(commit_data['task_ids'])}")
    else:
        print(f"❌ Commit failed: {commit_resp.status_code}")
        print(commit_resp.text)
else:
    print(f"❌ Plan failed: {plan_resp.status_code}")
    print(plan_resp.text)
