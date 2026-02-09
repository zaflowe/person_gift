"""Router for project long task templates."""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.project import Project
from app.models.user import User
from app.schemas.project_long_task import (
    ProjectLongTaskTemplateCreate,
    ProjectLongTaskTemplateUpdate,
    ProjectLongTaskTemplateResponse,
)
from app.services.project_long_task_service import project_long_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["project-long-tasks"])


def _ensure_project(db: Session, project_id: str, user_id: str) -> Project:
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.user_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id}/long-task-templates", response_model=List[ProjectLongTaskTemplateResponse])
def get_long_task_templates(
    project_id: str,
    include_hidden: bool = Query(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project(db, project_id, current_user.id)
    templates = project_long_task_service.get_templates(
        db, current_user.id, project_id, include_hidden=include_hidden
    )
    return templates


@router.post("/{project_id}/long-task-templates", response_model=ProjectLongTaskTemplateResponse, status_code=201)
def create_long_task_template(
    project_id: str,
    data: ProjectLongTaskTemplateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _ensure_project(db, project_id, current_user.id)
    template = project_long_task_service.create_template(
        db, current_user.id, project_id, data.dict()
    )
    return template


@router.patch("/{project_id}/long-task-templates/{template_id}", response_model=ProjectLongTaskTemplateResponse)
def update_long_task_template(
    project_id: str,
    template_id: str,
    updates: ProjectLongTaskTemplateUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _ensure_project(db, project_id, current_user.id)
    if project.status != "PROPOSED":
        raise HTTPException(status_code=400, detail="仅提案中的项目可修改长期任务")
    updated = project_long_task_service.update_template(
        db, current_user.id, project_id, template_id, updates.dict(exclude_unset=True)
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated


@router.post("/{project_id}/long-task-templates/{template_id}/hide", response_model=ProjectLongTaskTemplateResponse)
def hide_long_task_template(
    project_id: str,
    template_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = _ensure_project(db, project_id, current_user.id)
    if project.status != "PROPOSED":
        raise HTTPException(status_code=400, detail="仅提案中的项目可修改长期任务")
    updated = project_long_task_service.hide_template(
        db, current_user.id, project_id, template_id
    )
    if not updated:
        raise HTTPException(status_code=404, detail="Template not found")
    return updated
