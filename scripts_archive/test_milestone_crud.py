import requests
import json
import time

BASE_URL = "http://localhost:8000"

def get_token():
    # Register/Login user
    username = f"test_ms_user_{int(time.time())}"
    password = "password123"
    
    print(f"Registering {username}...")
    # Register
    r_reg = requests.post(f"{BASE_URL}/api/auth/register", json={"username": username, "password": password})
    if r_reg.status_code != 201:
         # If 400, maybe exists (unlikely with timestamp), try login
         pass
         
    # Login
    print(f"Logging in {username}...")
    response = requests.post(f"{BASE_URL}/api/auth/login", data={"username": username, "password": password})
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} {response.text}")
        return None
    return response.json()["access_token"]

def test_milestone_crud():
    token = get_token()
    if not token:
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Project
    print("Creating Project...")
    p_res = requests.post(f"{BASE_URL}/api/projects", json={
        "title": "Milestone Test Project",
        "description": "Testing milestones"
    }, headers=headers)
    if p_res.status_code != 201:
        print(f"Project creation failed: {p_res.text}")
        return
    project_id = p_res.json()["id"]
    print(f"Project Created: {project_id}")
    
    # 2. Create Milestone
    print("Creating Milestone...")
    m_res = requests.post(f"{BASE_URL}/api/projects/{project_id}/milestones", json={
        "title": "M1",
        "description": "First milestone",
        "is_critical": True
    }, headers=headers)
    if m_res.status_code != 201:
        print(f"Milestone creation failed: {m_res.text}")
        return
    milestone_id = m_res.json()["id"]
    print(f"Milestone Created: {milestone_id}")
    
    # 3. Update Milestone
    print("Updating Milestone...")
    u_res = requests.patch(f"{BASE_URL}/api/projects/{project_id}/milestones/{milestone_id}", json={
        "title": "M1 Updated",
        "description": "Updated desc"
    }, headers=headers)
    if u_res.status_code != 200:
        print(f"Milestone update failed: {u_res.text}")
        return
    print("Milestone Updated:", u_res.json()["title"])
    assert u_res.json()["title"] == "M1 Updated"
    
    # 4. Delete Milestone
    print("Deleting Milestone...")
    d_res = requests.delete(f"{BASE_URL}/api/projects/{project_id}/milestones/{milestone_id}", headers=headers)
    if d_res.status_code != 204:
        print(f"Milestone delete failed: {d_res.status_code} {d_res.text}")
        return
    print("Milestone Deleted")
    
    # 5. Verify Deletion
    get_res = requests.get(f"{BASE_URL}/api/projects/{project_id}/milestones", headers=headers)
    milestones = get_res.json()
    assert len(milestones) == 0
    print("Verification Successful: 0 milestones found.")

if __name__ == "__main__":
    test_milestone_crud()
