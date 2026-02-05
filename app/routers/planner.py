"""Planner router - AI-powered task planning endpoints."""
import json
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.planning import PlanningSession
from app.models.project import Project
from app.models.task import Task
from app.schemas.planner import (
    PlanRequest,
    PlanResponse,
    CommitRequest,
    CommitResponse
)
from app.services.planner_service import planner_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["planner"])


@router.post("/plan", response_model=PlanResponse)
async def generate_plan(
    request: PlanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a structured plan based on user's natural language input.
    
    Uses AI to convert free-form text into a structured project + tasks plan.
    The plan is saved to planning_sessions for later commit.
    """
    try:
        # Prepare context
        context = request.context.dict() if request.context else {}
        if "today" not in context:
            context["today"] = datetime.now().strftime("%Y-%m-%d")
        
        # Generate plan using AI
        logger.info(f"User {current_user.username} requesting plan for: {request.message[:50]}...")
        plan = planner_service.generate_plan(request.message, context)
        
        # Save to planning_sessions
        session_id = str(uuid.uuid4())
        planning_session = PlanningSession(
            id=session_id,
            user_id=current_user.id,
            message=request.message,
            plan_json=json.dumps(plan, ensure_ascii=False)
        )
        db.add(planning_session)
        db.commit()
        
        logger.info(f"Plan generated successfully, session_id: {session_id}")
        
        return PlanResponse(
            session_id=session_id,
            plan=plan
        )
    
    except ValueError as e:
        logger.error(f"Plan generation failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error in plan generation: {str(e)}")
        raise HTTPException(status_code=500, detail="规划生成失败，请稍后重试")


@router.post("/commit", response_model=CommitResponse)
async def commit_plan(
    request: CommitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Commit a plan and create Project + Tasks.
    
    Creates:
    - 1 Project (status=PROPOSED)
    - N Tasks (linked to the project)
    - Updates planning_session with project_id
    
    Transaction ensures atomicity: if any step fails, everything rolls back.
    """
    try:
        # Verify planning session exists and belongs to current user
        session = db.query(PlanningSession).filter(
            PlanningSession.id == request.session_id,
            PlanningSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(status_code=404, detail="Planning session not found")
        
        if session.project_id:
            raise HTTPException(status_code=400, detail="This plan has already been committed")
        
        # Validate plan structure
        plan = request.plan
        if "project" not in plan or "tasks" not in plan:
            raise HTTPException(status_code=400, detail="Invalid plan structure")
        
        project_data = plan["project"]
        tasks_data = plan["tasks"]
        
        if not project_data.get("title"):
            raise HTTPException(status_code=400, detail="Project title is required")
        if not tasks_data or len(tasks_data) == 0:
            raise HTTPException(status_code=400, detail="At least one task is required")
        
        logger.info(f"Committing plan {request.session_id} for user {current_user.username}...")
        
        # Start transaction
        try:
            # 1. Create Project (status=PROPOSED)
            project = Project(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                title=project_data["title"],
                description=project_data.get("description", ""),
                status="PROPOSED",  # Critical: not ACTIVE
                success_criteria=plan.get("rationale"),
                created_at=datetime.utcnow()
            )
            db.add(project)
            db.flush()  # Get project.id without committing
            
            logger.debug(f"Created project: {project.id}")
            
            # 2. Create Tasks
            task_ids = []
            for i, task_data in enumerate(tasks_data):
                if not task_data.get("title"):
                    raise ValueError(f"Task {i} is missing title")
                if not task_data.get("due_at"):
                    raise ValueError(f"Task {i} is missing due_at")
                
                # Parse due_at
                try:
                    deadline = datetime.fromisoformat(task_data["due_at"].replace('+08:00', ''))
                except Exception as e:
                    raise ValueError(f"Task {i} has invalid due_at format: {str(e)}")
                
                task = Task(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    project_id=project.id,
                    title=task_data["title"],
                    description=task_data.get("description", ""),
                    deadline=deadline,
                    evidence_type=task_data.get("evidence_type", "none"),
                    status="OPEN",
                    created_at=datetime.utcnow()
                )
                db.add(task)
                db.flush()
                task_ids.append(task.id)
            
            logger.debug(f"Created {len(task_ids)} tasks")
            
            # 3. Update planning_session
            session.project_id = project.id
            
            # 4. Commit transaction
            db.commit()
            
            logger.info(f"Plan committed successfully: project {project.id}, {len(task_ids)} tasks")
            
            return CommitResponse(
                project_id=project.id,
                task_ids=task_ids
            )
        
        except Exception as e:
            db.rollback()
            logger.error(f"Transaction failed, rolled back: {str(e)}")
            raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in commit: {str(e)}")
        raise HTTPException(status_code=500, detail="提交失败，请稍后重试")
