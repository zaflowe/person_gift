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
    """Check if this week's system tasks exist, create if not."""
    try:
        print(f"DEBUG: Entering weekly_system_task_check with user {current_user.id}")
        today = date.today()
        year, week, _ = today.isocalendar()
        week_key = f"W{year}-{week:02d}"
        
        created_count = 0
        tasks_info = []

        # ------------------------------------------------------------------
        # Helper: Ensure Single Task
        # ------------------------------------------------------------------
        def ensure_single_task(title: str, description: str, evidence_type: str, evidence_criteria: str):
            # Find all tasks with this exact title
            existing = db.query(Task).filter(
                Task.user_id == current_user.id,
                Task.title == title
            ).order_by(Task.created_at.asc()).all()
            
            if not existing:
                # Create new
                deadline = datetime.now() + timedelta(hours=24)
                new_task = Task(
                    user_id=current_user.id,
                    title=title,
                    description=description,
                    deadline=deadline,
                    status="OPEN",
                    evidence_type=evidence_type,
                    evidence_criteria=evidence_criteria
                )
                db.add(new_task)
                return True, {"id": new_task.id, "title": new_task.title, "action": "created"}
            
            elif len(existing) > 1:
                # Cleanup duplicates
                print(f"DEBUG: Found {len(existing)} duplicates for '{title}', cleaning up...")
                # Keep the first one (oldest), delete the rest
                keep = existing[0]
                for dup in existing[1:]:
                    db.delete(dup)
                return True, {"id": keep.id, "title": keep.title, "action": "cleaned_duplicates"}
            
            return False, None

        # ------------------------------------------------------------------
        # Task 1: Weight Record (Number)
        # ------------------------------------------------------------------
        created_w, info_w = ensure_single_task(
            title=f"【系统】本周体重记录 ({week_key})",
            description=f"记录本周体重。\n\n请输入数字（单位 kg）。",
            evidence_type="number",
            evidence_criteria="提交当前体重 (kg)"
        )
        if created_w:
            if info_w["action"] == "created": created_count += 1
            tasks_info.append(info_w)

        # ------------------------------------------------------------------
        # Task 2: Body Photo Record (Image)
        # ------------------------------------------------------------------
        created_p, info_p = ensure_single_task(
            title=f"【系统】本周身材记录 ({week_key})",
            description=f"记录本周身材变化。\n\n请上传一张上半身或全身照片，系统将自动估算体脂率。",
            evidence_type="image",
            evidence_criteria="提交一张上半身或全身照片"
        )
        if created_p:
            if info_p["action"] == "created": created_count += 1
            tasks_info.append(info_p)
        
        if created_count > 0 or len(tasks_info) > 0:
            db.commit()
            return {
                "created": created_count > 0,
                "count": created_count,
                "tasks": tasks_info,
                "message": "Tasks checked/cleaned."
            }
        
        return {
            "created": False,
            "message": "All system tasks for this week verified."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "created": False,
            "error": "Internal Error",
            "detail": str(e) 
        }
