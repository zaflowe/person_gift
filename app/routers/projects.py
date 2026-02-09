"""Projects router."""
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectWithMilestones,
    MilestoneCreate,
    MilestoneResponse,
    ProjectUpdate,
    MilestoneUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[ProjectResponse])
def get_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's projects."""
    projects = ProjectService.get_projects(db, current_user)
    return projects


@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new project in PROPOSED status."""
    project = ProjectService.create_project(db, current_user, project_data)
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str,
    project_update: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update project details."""
    project = ProjectService.update_project(db, project_id, current_user, project_update)
    return project


@router.get("/{project_id}", response_model=ProjectWithMilestones)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project details with milestones."""
    project = ProjectService.get_project(db, project_id, current_user)
    milestones = ProjectService.get_milestones(db, project_id, current_user)
    
    project_dict = {
        **project.__dict__,
        "milestones": milestones
    }
    return project_dict


@router.post("/{project_id}/request-analysis", response_model=ProjectResponse)
async def request_analysis(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Request AI analysis for project breakdown.
    
    Internally calls AI service and writes ai_confirmed_at.
    No separate /ai-confirm endpoint is exposed.
    """
    project = await ProjectService.request_analysis(db, project_id, current_user)
    return project


@router.post("/{project_id}/confirm", response_model=ProjectResponse)
def user_confirm(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User confirms the project breakdown.
    
    Writes user_confirmed_at and agreement_hash.
    If both user and AI confirmed, status becomes ACTIVE.
    """
    project = ProjectService.user_confirm(db, project_id, current_user)
    return project


@router.post("/{project_id}/complete", response_model=ProjectResponse)
def complete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Complete a project when all milestones are achieved.
    """
    project = ProjectService.get_project(db, project_id, current_user)

    milestones = ProjectService.get_milestones(db, project_id, current_user)
    if not milestones:
        raise HTTPException(status_code=400, detail="没有里程碑，无法完成项目")
    if not all(m.status == "ACHIEVED" for m in milestones):
        raise HTTPException(status_code=400, detail="仍有未完成的里程碑")

    project.status = "SUCCESS"
    project.resolved_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


# Milestones

@router.get("/{project_id}/milestones", response_model=List[MilestoneResponse])
def get_milestones(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get project milestones."""
    milestones = ProjectService.get_milestones(db, project_id, current_user)
    return milestones


@router.post("/{project_id}/milestones", response_model=MilestoneResponse, status_code=201)
def create_milestone(
    project_id: str,
    milestone_data: MilestoneCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a milestone for a project."""
    milestone = ProjectService.create_milestone(
        db, project_id, current_user, milestone_data
    )
    return milestone


@router.patch("/{project_id}/milestones/{milestone_id}", response_model=MilestoneResponse)
def update_milestone(
    project_id: str,
    milestone_id: str,
    milestone_update: MilestoneUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a milestone."""
    project = ProjectService.get_project(db, project_id, current_user)
    if project.status != "PROPOSED":
        raise HTTPException(status_code=400, detail="仅提案中的项目可修改里程碑")
    milestone = ProjectService.update_milestone(
        db, project_id, milestone_id, current_user, milestone_update
    )
    return milestone


@router.delete("/{project_id}/milestones/{milestone_id}", status_code=204)
def delete_milestone(
    project_id: str,
    milestone_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a milestone."""
    project = ProjectService.get_project(db, project_id, current_user)
    if project.status != "PROPOSED":
        raise HTTPException(status_code=400, detail="仅提案中的项目可修改里程碑")
    ProjectService.delete_milestone(
        db, project_id, milestone_id, current_user
    )
    return None


@router.post("/{project_id}/milestones/{milestone_id}/mark-achieved", response_model=MilestoneResponse)
def mark_milestone_achieved(
    project_id: str,
    milestone_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Mark a milestone as achieved.
    
    Action-based endpoint, not a direct status PATCH.
    Triggers project status check after milestone update.
    """
    milestone = ProjectService.mark_milestone_achieved(
        db, project_id, milestone_id, current_user
    )
    return milestone
