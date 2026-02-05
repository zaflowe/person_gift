import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"

def get_token():
    username = f"test_sched_user_{int(time.time())}"
    password = "password123"
    requests.post(f"{BASE_URL}/api/auth/register", json={"username": username, "password": password})
    response = requests.post(f"{BASE_URL}/api/auth/login", data={"username": username, "password": password})
    if response.status_code != 200:
        return None
    return response.json()["access_token"]

def test_schedule_due():
    token = get_token()
    if not token:
        print("Login failed")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Create Task Due Today
    today_iso = datetime.now().isoformat()
    # Add task
    print("Creating Task due today...")
    t_res = requests.post(f"{BASE_URL}/api/tasks", json={
        "title": "Due Task 1",
        "description": "Due today",
        "status": "OPEN",
        "deadline": today_iso
    }, headers=headers)
    if t_res.status_code not in [200, 201]: # Tasks create returns 200 or 201
        print(f"Task creation failed: {t_res.status_code} {t_res.text}")
        return
    task_id = t_res.json()["id"]
    print(f"Task Created: {task_id}")
    
    # 2. Get Today Schedule
    print("Fetching Schedule...")
    s_res = requests.get(f"{BASE_URL}/api/schedule/today", headers=headers)
    if s_res.status_code != 200:
        print(f"Schedule fetch failed: {s_res.text}")
        return
    
    schedule = s_res.json()
    # Verify due_tasks
    due_tasks = schedule.get("due_tasks", [])
    print(f"Due Tasks Found: {len(due_tasks)}")
    
    found = False
    for t in due_tasks:
        if t["task_id"] == task_id:
            found = True
            print("Found created task in due_tasks!")
            break
            
    if not found:
        print("Task NOT found in due_tasks.")
        print("Due Tasks:", json.dumps(due_tasks, indent=2))
    else:
        print("Verification Successful.")

if __name__ == "__main__":
    test_schedule_due()
