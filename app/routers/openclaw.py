from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uuid

# In a real scenario, this would import from app.dependencies or a dedicated OpenClaw auth service
# For MVP, we will simulate a simple API key check for the machine agent.
OPENCLAW_API_KEY = "clw_test_key_123"

router = APIRouter(
    prefix="/openclaw",
    tags=["OpenClaw Automation Desktop Agent"]
)

def verify_openclaw_key(api_key: str):
    """Simple dependency to verify OpenClaw is authorized."""
    if api_key != OPENCLAW_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid OpenClaw API Key"
        )
    return True

# --- Schemas ---

class HeartbeatRequest(BaseModel):
    hostname: str
    os_version: str
    agent_version: str

class HeartbeatResponse(BaseModel):
    status: str
    server_time: datetime

class OpenClawTask(BaseModel):
    id: str
    command: str
    payload: Optional[dict] = None

class EvidenceSubmitRequest(BaseModel):
    task_id: str
    evidence_type: str  # e.g., "screenshot", "app_runtime", "text"
    content: str
    duration_seconds: Optional[int] = None


# --- Endpoints ---

@router.post("/heartbeat", response_model=HeartbeatResponse)
async def openclaw_heartbeat(
    request: HeartbeatRequest,
    api_key: str
):
    """
    Endpoint for OpenClaw to report it is alive.
    The server could register the MAC/hostname to know the desktop agent is online.
    """
    verify_openclaw_key(api_key)
    # Log the heartbeat or update a Redis/DB cache about machine status
    print(f"[{datetime.now()}] ❤️ OpenClaw Heartbeat received from {request.hostname} ({request.os_version})")
    
    return HeartbeatResponse(
        status="acknowledged",
        server_time=datetime.utcnow()
    )


@router.get("/tasks", response_model=List[OpenClawTask])
async def get_openclaw_tasks(
    api_key: str
):
    """
    Endpoint for OpenClaw to fetch pending automation tasks.
    These are tasks specifically designated for the desktop agent (e.g. running a script).
    """
    verify_openclaw_key(api_key)
    
    # Mocking: Currently no tasks in queue.
    # In reality, this queries the DB for Tasks assigned to 'openclaw' queue.
    return []


@router.post("/evidence")
async def submit_machine_evidence(
    request: EvidenceSubmitRequest,
    api_key: str
):
    """
    Endpoint for OpenClaw to silently submit evidence.
    For example: It tracked 1 hour of PDF reading, it creates the evidence and the 
    backend automatically marks the associated Task as DONE.
    """
    verify_openclaw_key(api_key)
    
    print(f"📸 OpenClaw submitted evidence for Task {request.task_id}. Type: {request.evidence_type}")
    
    # 1. Look up Task in DB
    # 2. Insert Evidence record
    # 3. Call AI Service to verify if needed (or trust machine unconditionally)
    # 4. Update Task status to DONE
    
    return {
        "status": "success",
        "message": "Evidence accepted from OpenClaw",
        "processed_at": datetime.utcnow()
    }
