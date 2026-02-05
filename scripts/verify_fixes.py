
import requests
import sys
import uuid

BASE_URL = "http://localhost:8000/api"
USERNAME = f"testuser_{uuid.uuid4().hex[:8]}"
PASSWORD = "password"

def login():
    try:
        # Check if auth/login is correct from auth.py
        resp = requests.post(f"{BASE_URL}/auth/login", data={"username": USERNAME, "password": PASSWORD})
        if resp.status_code != 200:
            print("Login failed, trying registration...")
            # Check auth/register
            reg_resp = requests.post(f"{BASE_URL}/auth/register", json={"username": USERNAME, "password": PASSWORD})
            if reg_resp.status_code == 201:
                return login()
            else:
                print(f"Registration failed: {reg_resp.status_code} {reg_resp.text}")
                sys.exit(1)
        return resp.json()["access_token"]
    except Exception as e:
        print(f"Connection error: {e}")
        sys.exit(1)

def verify_fixes():
    token = login()
    headers = {"Authorization": f"Bearer {token}"}

    print("1. Verifying Project Confirm Endpoint...")
    # Get a project
    projects = requests.get(f"{BASE_URL}/projects", headers=headers).json()
    if not projects:
        # Create one
        p = requests.post(f"{BASE_URL}/projects", json={"title": "Test Project", "description": "Test"}, headers=headers).json()
        project_id = p["id"]
    else:
        project_id = projects[0]["id"]
    
    print(f"   Target Project ID: {project_id}")
    
    # Try confirm (mock hash)
    confirm_url = f"{BASE_URL}/projects/{project_id}/confirm"
    resp = requests.post(confirm_url, json={"agreement_hash": "test"}, headers=headers)
    
    if resp.status_code == 404:
        print("❌ FAILED: Confirm returned 404 Not Found")
    elif resp.status_code in [200, 400, 422]: # 400/422 is fine, meaning endpoint exists
        print(f"✅ SUCCESS: Confirm returned {resp.status_code} (Endpoint exists)")
    else:
        print(f"❓ ALL: Confirm returned {resp.status_code}")

    print("\n2. Verifying Task Filtering...")
    # Create a task for this project
    requests.post(f"{BASE_URL}/tasks", json={"title": "Project Task", "project_id": project_id}, headers=headers)
    
    # Fetch with filter
    filter_url = f"{BASE_URL}/tasks?project_id={project_id}"
    tasks = requests.get(filter_url, headers=headers).json()
    
    # Check if all tasks belong to project
    all_match = True
    for t in tasks:
        if t.get("project_id") != project_id:
            all_match = False
            print(f"   ❌ Found non-matching task: {t['title']} ({t['project_id']})")
    
    if all_match:
        print(f"✅ SUCCESS: All {len(tasks)} tasks match project_id {project_id}")
    else:
        print("❌ FAILED: Filtering did not work")

if __name__ == "__main__":
    verify_fixes()
