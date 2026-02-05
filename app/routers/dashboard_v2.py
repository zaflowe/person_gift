"""Dashboard APIs for Phase 6."""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.database import get_db
from app.services import auth_service
from app.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.task import Task

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/projects/strategic")
def get_strategic_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get up to 3 strategic projects for dashboard display."""
    projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.is_strategic == True,
        Project.status.in_(["PROPOSED", "ACTIVE"])
    ).order_by(
        Project.updated_at.desc()
    ).limit(3).all()
    
    result = []
    for project in projects:
        # Calculate simple progress
        total_milestones = len(project.milestones)
        achieved = len([m for m in project.milestones if m.status == "ACHIEVED"])
        progress = int((achieved / total_milestones * 100)) if total_milestones > 0 else 0
        
        result.append({
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "progress": progress,
            "next_milestone": project.next_milestone or f"{achieved}/{total_milestones} milestones",
            "updated_at": project.updated_at.isoformat(),
            "color": project.color
        })
    
    return result


@router.get("/daily-reminder-data")
def get_daily_reminder_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get data for daily reminder message."""
    now = datetime.now()
    tomorrow = now + timedelta(hours=24)
    
    # Get all incomplete tasks
    incomplete_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status.in_(["OPEN", "EVIDENCE_SUBMITTED"])
    ).all()
    
    # Categorize tasks
    overdue = []
    due_soon = []
    all_incomplete = []
    
    for task in incomplete_tasks:
        task_dict = {
            "title": task.title,
            "deadline": task.deadline.isoformat() if task.deadline else None
        }
        all_incomplete.append(task_dict)
        
        if task.deadline:
            if task.deadline < now:
                overdue.append(task_dict)
            elif task.deadline <= tomorrow:
                due_soon.append(task_dict)
    
    # Sort by deadline
    overdue.sort(key=lambda x: x["deadline"] if x["deadline"] else "")
    due_soon.sort(key=lambda x: x["deadline"] if x["deadline"] else "")
    
    # Check for weekly system task
    from datetime import date
    import calendar
    today = date.today()
    year, week, _ = today.isocalendar()
    week_key = f"W{year}-{week:02d}"
    
    system_task = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.title.like(f"%【系统】体重%{week_key}%")
    ).first()
    
    system_task_info = None
    if system_task:
        system_task_info = {
            "exists": True,
            "completed": system_task.status == "DONE",
            "title": system_task.title,
            "deadline": system_task.deadline.isoformat() if system_task.deadline else None
        }
    
    return {
        "incomplete_tasks": {
            "count": len(all_incomplete),
            "top_5": all_incomplete[:5]
        },
        "overdue_tasks": {
            "count": len(overdue),
            "top_5": overdue[:5]
        },
        "due_soon_tasks": {
            "count": len(due_soon),
            "top_5": due_soon[:5]
        },
        "system_task": system_task_info or {"exists": False}
    }
