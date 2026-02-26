"""Study session router."""
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel
import json
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.database import get_db
from app.config import settings
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
    is_quick_start: bool = False
    quick_start_action: Optional[str] = None

class SessionResponse(BaseModel):
    id: str
    project_id: Optional[str]
    task_id: Optional[str]
    custom_label: Optional[str]
    duration_sec: int
    created_at: datetime
    status: str
    is_quick_start: bool = False
    quick_start_action: Optional[str] = None
    quick_start_valid: bool = False
    quick_start_task_id: Optional[str] = None
    
    class Config:
        orm_mode = True

class StudyStats(BaseModel):
    today_total_sec: int
    week_total_sec: int
    distribution: List[dict] # This week distribution
    all_time_total_sec: int
    all_time_distribution: List[dict]
    quick_start_today_count: int = 0
    quick_start_week_count: int = 0
    quick_start_month_count: int = 0
    quick_start_all_time_count: int = 0


def _to_task_local_time(dt: datetime) -> datetime:
    """Convert client/UTC session start time into local naive task time for schedule display."""
    try:
        if dt.tzinfo is not None:
            return dt.astimezone(ZoneInfo(settings.timezone)).replace(tzinfo=None)
    except Exception:
        pass
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


def _create_quick_start_task(
    db: Session,
    current_user: User,
    session_in: SessionCreate,
    project_name: Optional[str],
    created_at_dt: datetime,
) -> str:
    """Create a completed task record representing a valid Quick Start session."""
    from app.models.task import Task  # local import to avoid circular init surprises

    local_start_dt = _to_task_local_time(created_at_dt)
    end_dt = local_start_dt + timedelta(seconds=max(session_in.duration_sec, 300))
    fallback_title = f"Quick Start {local_start_dt.strftime('%m/%d %H:%M')}"
    description_lines = ["Quick Start 记录（可补录）"]
    if session_in.quick_start_action:
        description_lines.append(f"最小动作：{session_in.quick_start_action}")
    if project_name:
        description_lines.append(f"来源项目：{project_name}")
    description_lines.append("可在任务详情中补录成果（任务名称）与备注。")
    description = "\n".join(description_lines)

    task = Task(
        user_id=current_user.id,
        title=fallback_title,
        description=description,
        status="DONE",
        evidence_type="none",
        evidence_criteria="quick_start_record",
        tags=json.dumps(["quick_start", "quick_start_pending_fill"], ensure_ascii=False),
        scheduled_date=local_start_dt,
        scheduled_time=local_start_dt,
        deadline=end_dt,
        duration=max(int(session_in.duration_sec // 60), 5),
        is_time_blocked=True,
        project_id=None,  # Quick Start mode intentionally does not bind project/task
        created_at=local_start_dt,
        completed_at=end_dt,
        is_quick_start=True,
        quick_start_action=session_in.quick_start_action,
    )
    db.add(task)
    db.flush()
    return task.id

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

    is_quick_start_valid = bool(
        session_in.is_quick_start
        and session_in.status == SessionStatus.COMPLETED.value
        and session_in.duration_sec >= 5 * 60
    )

    new_session = StudySession(
        user_id=current_user.id,
        project_id=session_in.project_id,
        task_id=session_in.task_id,
        custom_label=session_in.custom_label,
        project_name_snapshot=project_name,
        task_title_snapshot=task_title,
        created_at=session_in.created_at,
        duration_sec=session_in.duration_sec,
        status=session_in.status,
        is_quick_start=session_in.is_quick_start,
        quick_start_action=session_in.quick_start_action,
        quick_start_valid=is_quick_start_valid,
        quick_start_task_id=None,
    )
    
    db.add(new_session)
    db.flush()

    if is_quick_start_valid:
        quick_start_task_id = _create_quick_start_task(
            db=db,
            current_user=current_user,
            session_in=session_in,
            project_name=project_name,
            created_at_dt=session_in.created_at,
        )
        new_session.quick_start_task_id = quick_start_task_id
        created_qs_task = db.query(Task).filter(Task.id == quick_start_task_id).first()
        if created_qs_task:
            created_qs_task.quick_start_session_id = new_session.id

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
    month_start = today_start.replace(day=1)
    
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
    
    quick_start_today_count = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= today_start,
        StudySession.status == "completed",
        StudySession.quick_start_valid.is_(True),
    ).scalar() or 0

    quick_start_week_count = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= week_start,
        StudySession.status == "completed",
        StudySession.quick_start_valid.is_(True),
    ).scalar() or 0

    quick_start_month_count = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == current_user.id,
        StudySession.created_at >= month_start,
        StudySession.status == "completed",
        StudySession.quick_start_valid.is_(True),
    ).scalar() or 0

    quick_start_all_time_count = db.query(func.count(StudySession.id)).filter(
        StudySession.user_id == current_user.id,
        StudySession.status == "completed",
        StudySession.quick_start_valid.is_(True),
    ).scalar() or 0

    return StudyStats(
        today_total_sec=int(today_sec),
        week_total_sec=int(week_sec),
        distribution=distribution,
        all_time_total_sec=int(all_time_sec),
        all_time_distribution=all_time_distribution,
        quick_start_today_count=int(quick_start_today_count),
        quick_start_week_count=int(quick_start_week_count),
        quick_start_month_count=int(quick_start_month_count),
        quick_start_all_time_count=int(quick_start_all_time_count),
    )
