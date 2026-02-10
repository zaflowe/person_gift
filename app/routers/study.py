"""Study session router."""
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import enum

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.study import StudySession, SessionStatus
from app.models.project import Project
from app.models.task import Task

router = APIRouter(prefix="/study", tags=["study"])

class SessionCreate(BaseModel):
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    custom_label: Optional[str] = None
    created_at: datetime
    duration_sec: int = 0
    status: str = "completed"

class SessionResponse(BaseModel):
    id: str
    project_id: Optional[str]
    task_id: Optional[str]
    custom_label: Optional[str]
    duration_sec: int
    created_at: datetime
    status: str
    
    class Config:
        orm_mode = True

class StudyStats(BaseModel):
    today_total_sec: int
    week_total_sec: int
    distribution: List[dict] # This week distribution
    all_time_total_sec: int
    all_time_distribution: List[dict]

@router.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_in: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a study session."""
    
    # Snapshot names
    project_name = None
    task_title = None
    
    if session_in.project_id:
        p = db.query(Project).filter(Project.id == session_in.project_id).first()
        if p: project_name = p.title
            
    if session_in.task_id:
        t = db.query(Task).filter(Task.id == session_in.task_id).first()
        if t: task_title = t.title

    new_session = StudySession(
        user_id=current_user.id,
        project_id=session_in.project_id,
        task_id=session_in.task_id,
        custom_label=session_in.custom_label,
        project_name_snapshot=project_name,
        task_title_snapshot=task_title,
        created_at=session_in.created_at,
        duration_sec=session_in.duration_sec,
        status=session_in.status
    )
    
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session

@router.get("/stats", response_model=StudyStats)
async def get_study_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get study stats for dashboard."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    # Today Total
    today_sec = db.query(func.sum(StudySession.duration_sec)).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= today_start,
        StudySession.status == "completed"
    ).scalar() or 0
    
    # Week Total
    week_sec = db.query(func.sum(StudySession.duration_sec)).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= week_start,
        StudySession.status == "completed"
    ).scalar() or 0
    
    # Distribution (This Week)
    # Group by Project Name Snapshot (or 'Other')
    # Logic: If project_name_snapshot is null, use custom_label or 'Other'
    
    sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= week_start,
        StudySession.status == "completed"
    ).all()
    
    dist_map = {} # Key: (id, name) -> duration
    
    for s in sessions:
        p_id = s.project_id
        # Use snapshot name, fallback to Title if available, fallback to Other
        name = s.project_name_snapshot or "Other"
        
        # If we have project_id, stick to it. If not (orphaned/deleted), use name as key?
        # Let's use a composite key for grouping
        key = (p_id, name)
        
        if key not in dist_map: dist_map[key] = 0
        dist_map[key] += s.duration_sec
        
    distribution = []
    for (pid, pname), duration in dist_map.items():
        distribution.append({
            "name": pname,
            "value": duration,
            "project_id": pid
        })

    # All-time Total
    all_time_sec = db.query(func.sum(StudySession.duration_sec)).filter(
        StudySession.user_id == current_user.id,
        StudySession.status == "completed"
    ).scalar() or 0

    # Distribution (All Time)
    all_sessions = db.query(StudySession).filter(
        StudySession.user_id == current_user.id,
        StudySession.status == "completed"
    ).all()

    all_dist_map = {}
    for s in all_sessions:
        p_id = s.project_id
        name = s.project_name_snapshot or "Other"
        key = (p_id, name)
        if key not in all_dist_map:
            all_dist_map[key] = 0
        all_dist_map[key] += s.duration_sec

    all_time_distribution = []
    for (pid, pname), duration in all_dist_map.items():
        all_time_distribution.append({
            "name": pname,
            "value": duration,
            "project_id": pid
        })
    
    return StudyStats(
        today_total_sec=int(today_sec),
        week_total_sec=int(week_sec),
        distribution=distribution,
        all_time_total_sec=int(all_time_sec),
        all_time_distribution=all_time_distribution
    )
