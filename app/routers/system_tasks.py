"""Weekly system task management."""
from datetime import datetime, timedelta, date
from typing import Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import auth_service
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task

router = APIRouter(prefix="/system-tasks", tags=["system-tasks"])


@router.post("/weekly-check")
def weekly_system_task_check(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if this week's system task exists, create if not."""
    try:
        print(f"DEBUG: Entering weekly_system_task_check with user {current_user.id}")
        # Calculate week key
        today = date.today()
        year, week, _ = today.isocalendar()
        week_key = f"W{year}-{week:02d}"
        
        # Check if task already exists
        existing_task = db.query(Task).filter(
            Task.user_id == current_user.id,
            Task.title.like(f"%【系统】体重%{week_key}%")
        ).first()
        
        if existing_task:
            return {
                "created": False,
                "task": {
                    "id": existing_task.id,
                    "title": existing_task.title,
                    "status": existing_task.status,
                    "deadline": existing_task.deadline.isoformat() if existing_task.deadline else None
                }
            }
        
        # Create new system task
        deadline = datetime.now() + timedelta(hours=24)
        new_task = Task(
            user_id=current_user.id,
            title=f"【系统】体重 + 上半身照片 ({week_key})",
            description=f"本周体重记录任务\n\n要求：\n1. 提交当前体重（kg）\n2. 提交一张上半身照片\n\n请在24小时内完成。",
            deadline=deadline,
            status="OPEN",
            evidence_type="image",  # Require photo evidence
            evidence_criteria="提交一张上半身照片"
        )
        
        db.add(new_task)
        db.commit()
        db.refresh(new_task)
        
        return {
            "created": True,
            "task": {
                "id": new_task.id,
                "title": new_task.title,
                "status": new_task.status,
                "deadline": new_task.deadline.isoformat()
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "created": False,
            "error": "Internal Error",
            "detail": str(e) 
        }
