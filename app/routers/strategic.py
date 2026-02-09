"""Strategic projects/tasks endpoints for dashboard."""
import logging
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["strategic"])


# Response schemas
class StrategicTaskResponse(BaseModel):
    id: str
    title: str
    deadline: str | None
    status: str
    project_id: str | None
    project_name: str | None
    
    class Config:
        from_attributes = True


class StrategicProjectResponse(BaseModel):
    id: str
    name: str
    progress: str | None  # Could be calculated or stored
    next_milestone: str | None
    
    class Config:
        from_attributes = True


@router.get("/tasks/from-strategic-projects", response_model=List[StrategicTaskResponse])
def get_tasks_from_strategic_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[StrategicTaskResponse]:
    """
    Get tasks belonging to strategic projects.
    Filters out completed tasks, limits to 6.
    """
    # Get strategic project IDs
    strategic_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.is_strategic == True
    ).all()
    
    strategic_project_ids = [p.id for p in strategic_projects]
    project_names = {p.id: p.title for p in strategic_projects}
    
    if not strategic_project_ids:
        return []
    
    # Get tasks from these projects
    tasks = db.query(Task).join(Project, Task.project_id == Project.id).filter(
        Task.user_id == current_user.id,
        Task.project_id.in_(strategic_project_ids),
        Task.status != "DONE",
        Project.status != "PROPOSED"
    ).order_by(Task.deadline.asc()).limit(6).all()
    
    # Format response
    return [
        StrategicTaskResponse(
            id=t.id,
            title=t.title,
            deadline=t.deadline.isoformat() if t.deadline else None,
            status=t.status,
            project_id=t.project_id,
            project_name=project_names.get(t.project_id)
        )
        for t in tasks
    ]


@router.get("/projects/strategic", response_model=List[StrategicProjectResponse])
def get_strategic_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[StrategicProjectResponse]:
    """
    Get strategic projects (is_strategic = true).
    Limits to 5 projects.
    """
    projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.is_strategic == True
    ).limit(5).all()
    
    # Calculate progress (simple: count of done tasks vs total tasks)
    results = []
    for project in projects:
        total_tasks = len(project.tasks)
        done_tasks = len([t for t in project.tasks if t.status == "DONE"])
        progress = f"{done_tasks}/{total_tasks}" if total_tasks > 0 else "0/0"
        
        results.append(StrategicProjectResponse(
            id=project.id,
            name=project.title,
            progress=progress,
            next_milestone=project.next_milestone
        ))
    
    return results
