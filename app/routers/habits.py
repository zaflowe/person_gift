"""Router for habits and fixed blocks."""
import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.models.habit import HabitTemplate, FixedBlock
from app.models.project import Project
from app.models.project_long_task import ProjectLongTaskTemplate
from app.services.habit_service import habit_service
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/habits", tags=["habits"])

# Pydantic Schemas
class HabitCreate(BaseModel):
    title: str
    enabled: bool = True
    frequency_mode: str = "interval" # interval, specific_days
    interval_days: int = 1
    days_of_week: List[int] = []
    default_due_time: Optional[str] = None
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    evidence_type: str = "none"
    evidence_schema: Optional[str] = None
    evidence_criteria: Optional[str] = None

class HabitUpdate(BaseModel):
    title: Optional[str] = None
    enabled: Optional[bool] = None
    frequency_mode: Optional[str] = None
    interval_days: Optional[int] = None
    days_of_week: Optional[List[int]] = None
    default_due_time: Optional[str] = None
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    evidence_type: Optional[str] = None
    evidence_schema: Optional[str] = None
    evidence_criteria: Optional[str] = None

class FixedBlockCreate(BaseModel):
    title: str
    start_time: str
    end_time: str
    days_of_week: List[int] = []
    color: Optional[str] = None

# --- Habit Template Routes ---

@router.get("/templates")
def get_habit_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all habit templates."""
    habits = habit_service.get_habits(db, current_user.id)
    # Convert JSON string to list for response? 
    # Or just return as is and let frontend parse?
    # Better to parse for cleaner API
    result = []
    for h in habits:
        h_dict = h.__dict__.copy()
        if 'days_of_week' in h_dict and isinstance(h_dict['days_of_week'], str):
             try:
                 h_dict['days_of_week'] = json.loads(h_dict['days_of_week'])
             except:
                 h_dict['days_of_week'] = []
        # remove sqlalchemy state
        if '_sa_instance_state' in h_dict:
            del h_dict['_sa_instance_state']
        result.append(h_dict)
    return result

@router.post("/templates")
def create_habit_template(
    habit: HabitCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new habit template."""
    return habit_service.create_habit(db, habit.dict(), current_user.id)

@router.patch("/templates/{habit_id}")
def update_habit_template(
    habit_id: str,
    updates: HabitUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a habit template."""
    updated = habit_service.update_habit(db, habit_id, updates.dict(exclude_unset=True), current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Habit not found")
    return updated

@router.delete("/templates/{habit_id}")
def delete_habit_template(
    habit_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a habit template."""
    success = habit_service.delete_habit(db, habit_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Habit not found")
    return {"message": "Deleted successfully"}


# --- Fixed Block Routes ---

@router.get("/fixed-blocks")
def get_fixed_blocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all fixed blocks plus active-project long-task schedule projections."""
    blocks = db.query(FixedBlock).filter(FixedBlock.user_id == current_user.id).all()
    # Parse json days
    result = []
    for b in blocks:
        b_dict = b.__dict__.copy()
        if 'days_of_week' in b_dict and isinstance(b_dict['days_of_week'], str):
             try:
                 b_dict['days_of_week'] = json.loads(b_dict['days_of_week'])
             except:
                 b_dict['days_of_week'] = []
        if '_sa_instance_state' in b_dict:
            del b_dict['_sa_instance_state']
        b_dict["source_type"] = "fixed_block"
        b_dict["readonly"] = False
        result.append(b_dict)

    projected_long_tasks = db.query(ProjectLongTaskTemplate, Project).join(
        Project, Project.id == ProjectLongTaskTemplate.project_id
    ).filter(
        ProjectLongTaskTemplate.user_id == current_user.id,
        Project.status == "ACTIVE",
        ProjectLongTaskTemplate.is_hidden == False,
    ).all()

    for template, project in projected_long_tasks:
        # Only show templates that have a visible time window for the fixed-time panel.
        start_time = template.default_start_time
        end_time = template.default_end_time or template.default_due_time
        if not start_time or not end_time:
            continue
        try:
            days = json.loads(template.days_of_week) if template.days_of_week else []
        except Exception:
            days = []
        if template.frequency_mode == "interval" and not days:
            # Fixed-time panel expects weekday display. Daily interval -> all days.
            if (template.interval_days or 1) == 1:
                days = [0, 1, 2, 3, 4, 5, 6]

        result.append({
            "id": f"project_long_task:{template.id}",
            "title": template.title,
            "start_time": start_time,
            "end_time": end_time,
            "days_of_week": days,
            "color": None,
            "source_type": "project_long_task",
            "readonly": True,
            "project_id": project.id,
            "project_title": project.title,
            "template_id": template.id,
            "frequency_mode": template.frequency_mode,
            "interval_days": template.interval_days,
        })

    result.sort(key=lambda item: (item.get("start_time") or "99:99", item.get("title") or ""))
    return result

@router.post("/fixed-blocks")
def create_fixed_block(
    block: FixedBlockCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new fixed block."""
    new_block = FixedBlock(
        user_id=current_user.id,
        title=block.title,
        start_time=block.start_time,
        end_time=block.end_time,
        days_of_week=json.dumps(block.days_of_week),
        color=block.color
    )
    db.add(new_block)
    db.commit()
    db.refresh(new_block)
    return new_block

@router.delete("/fixed-blocks/{block_id}")
def delete_fixed_block(
    block_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a fixed block."""
    block = db.query(FixedBlock).filter(
        FixedBlock.id == block_id,
        FixedBlock.user_id == current_user.id
    ).first()
    if not block:
        raise HTTPException(status_code=404, detail="Block not found")
    
    db.delete(block)
    db.commit()
    return {"message": "Deleted successfully"}


# --- Trigger Logic ---

@router.post("/check-today")
def check_daily_habits(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Trigger daily habit generation."""
    count = habit_service.process_daily_habits(db, current_user.id)
    return {"message": "Checked daily habits", "created_count": count}
