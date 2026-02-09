"""Tasks router."""
from typing import List, Optional

from fastapi import APIRouter, Depends, File, UploadFile, Query, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskEvidenceSubmit,
    TaskEvidenceResponse,
    TaskUpdate,
    PlanTemplateCreate,
    PlanTemplateResponse,
)
from app.services.task_service import TaskService, PlanTemplateService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=List[TaskResponse])
def get_tasks(
    filter: Optional[str] = Query(None, description="Filter: active/completed"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's tasks.
    
    - **active**: OPEN, EVIDENCE_SUBMITTED, OVERDUE
    - **completed**: DONE, EXCUSED
    - **project_id**: Filter by specific project
    """
    tasks = TaskService.get_tasks(db, current_user, filter, project_id)
    return tasks


@router.post("", response_model=TaskResponse, status_code=201)
def create_task(
    task_data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new task."""
    task = TaskService.create_task(db, current_user, task_data)
    return task


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get task details."""
    task = TaskService.get_task(db, task_id, current_user)
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    updates: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a task (only allowed for PROPOSED project tasks)."""
    task = TaskService.update_task(db, task_id, current_user, updates.dict(exclude_unset=True))
    return task


@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete a task (only for evidence_type=none).
    
    This is an action-based endpoint, not a direct status PATCH.
    """
    task = await TaskService.complete_task(db, task_id, current_user)
    return task


@router.post("/{task_id}/submit-evidence", response_model=TaskEvidenceResponse)
async def submit_evidence(
    task_id: str,
    evidence_type: str = Form(...),
    content: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit evidence for a task.
    
    Triggers AI judgment and updates task status accordingly.
    - pass -> DONE
    - fail -> OPEN
    """
    evidence_data = TaskEvidenceSubmit(
        evidence_type=evidence_type,
        content=content
    )
    evidence = await TaskService.submit_evidence(
        db, task_id, current_user, evidence_data, image
    )
    return evidence


# Plan Templates

@router.get("/templates", response_model=List[PlanTemplateResponse])
def get_plan_templates(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's plan templates."""
    templates = PlanTemplateService.get_templates(db, current_user)
    return templates


@router.post("/templates", response_model=PlanTemplateResponse, status_code=201)
def create_plan_template(
    template_data: PlanTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a plan template for recurring tasks."""
    template = PlanTemplateService.create_template(db, current_user, template_data)
    return template
