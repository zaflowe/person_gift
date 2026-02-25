"""Planner router - AI-powered task planning endpoints."""
import json
import logging
import re
import uuid
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.planning import PlanningSession
from app.models.conversation import ConversationSession
from app.models.project import Project, Milestone
from app.models.project_long_task import ProjectLongTaskTemplate
from app.models.task import Task
from app.schemas.planner import (
    PlanRequest,
    PlanResponse,
    CommitRequest,
    CommitResponse
)
from app.services.planner_service import planner_service
from app.services.project_long_task_service import project_long_task_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/planner", tags=["planner"])

def _looks_like_milestone(title: str) -> bool:
    if not title:
        return False
    if "里程碑" in title or "阶段" in title:
        return True
    return re.search(r"第\\s*\\d+.*周", title) is not None


def _normalize_plan_input(plan: dict) -> dict:
    if not isinstance(plan, dict):
        return {"project": {"title": ""}, "tasks": []}

    if "project" not in plan or not isinstance(plan.get("project"), dict):
        plan["project"] = {}

    if isinstance(plan.get("project"), dict):
        project = plan["project"]
        project["title"] = project.get("title") or plan.get("project_title") or plan.get("title") or ""
        project["description"] = project.get("description") or plan.get("description") or ""

    if "tasks" not in plan or not isinstance(plan.get("tasks"), list):
        plan["tasks"] = []

    for task in plan["tasks"]:
        if isinstance(task, dict) and not task.get("due_at") and task.get("deadline"):
            task["due_at"] = task.get("deadline")

    if "milestones" not in plan or not isinstance(plan.get("milestones"), list):
        plan["milestones"] = []
    else:
        # Flatten nested milestone tasks into top-level tasks while preserving grouping.
        flattened_tasks = []
        for idx, milestone in enumerate(plan["milestones"]):
            if not isinstance(milestone, dict):
                continue
            nested_tasks = milestone.get("tasks")
            if isinstance(nested_tasks, list):
                for task in nested_tasks:
                    if not isinstance(task, dict):
                        continue
                    task_copy = dict(task)
                    task_copy.setdefault("milestone_index", idx)
                    if not task_copy.get("due_at") and task_copy.get("deadline"):
                        task_copy["due_at"] = task_copy.get("deadline")
                    flattened_tasks.append(task_copy)
        if flattened_tasks:
            existing_keys = {
                (
                    (t.get("title") or "").strip(),
                    (t.get("due_at") or t.get("deadline") or "").strip(),
                    t.get("milestone_index"),
                )
                for t in plan["tasks"]
                if isinstance(t, dict)
            }
            for task in flattened_tasks:
                key = (
                    (task.get("title") or "").strip(),
                    (task.get("due_at") or task.get("deadline") or "").strip(),
                    task.get("milestone_index"),
                )
                if key not in existing_keys:
                    plan["tasks"].append(task)
                    existing_keys.add(key)

    if "long_tasks" not in plan or not isinstance(plan.get("long_tasks"), list):
        plan["long_tasks"] = []
    else:
        for lt in plan["long_tasks"]:
            if not isinstance(lt, dict):
                continue
            days_of_week = lt.get("days_of_week")
            if isinstance(days_of_week, str):
                parts = [p.strip() for p in days_of_week.split(",") if p.strip()]
                parsed = []
                for p in parts:
                    try:
                        parsed.append(int(p))
                    except Exception:
                        continue
                lt["days_of_week"] = parsed
            elif isinstance(days_of_week, list):
                parsed = []
                for p in days_of_week:
                    try:
                        parsed.append(int(p))
                    except Exception:
                        continue
                lt["days_of_week"] = parsed

            if "interval_days" in lt:
                try:
                    lt["interval_days"] = int(lt.get("interval_days") or 1)
                except Exception:
                    lt["interval_days"] = 1
            if "total_cycle_days" in lt:
                try:
                    lt["total_cycle_days"] = int(lt.get("total_cycle_days") or 28)
                except Exception:
                    lt["total_cycle_days"] = 28

    if not plan["milestones"] and plan["tasks"]:
        plan["milestones"] = [
            {
                "title": t.get("title"),
                "description": t.get("description", ""),
                "due_at": t.get("due_at") or t.get("deadline"),
            }
            for t in plan["tasks"]
            if isinstance(t, dict) and _looks_like_milestone(t.get("title", ""))
        ]

    return plan


def _parse_plan_datetime(value):
    if not value:
        return None
    if not isinstance(value, str):
        return None
    raw = value
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")
    try:
        # Keep backward compatibility with old +08:00 stripping behavior.
        return datetime.fromisoformat(raw.replace("+08:00", ""))
    except Exception:
        return None


def _milestone_ordered_list(milestones_data: list[dict]) -> list[tuple[int, dict, datetime | None]]:
    items: list[tuple[int, dict, datetime | None]] = []
    for idx, m in enumerate(milestones_data):
        if not isinstance(m, dict) or not m.get("title"):
            continue
        due_dt = _parse_plan_datetime(m.get("due_at") or m.get("deadline"))
        items.append((idx, m, due_dt))
    return items


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
            # Idempotent: return existing project if already committed
            existing_tasks = db.query(Task.id).filter(
                Task.project_id == session.project_id,
                Task.user_id == current_user.id
            ).all()
            task_ids = [t.id for t in existing_tasks]
            return CommitResponse(
                project_id=session.project_id,
                task_ids=task_ids
            )
        
        # Validate plan structure
        plan = _normalize_plan_input(request.plan)
        if "project" not in plan or "tasks" not in plan:
            raise HTTPException(status_code=400, detail="Invalid plan structure")
        
        project_data = plan["project"]
        tasks_data = plan["tasks"]
        
        if not project_data.get("title"):
            raise HTTPException(status_code=400, detail="Project title is required")
        if (not tasks_data or len(tasks_data) == 0) and not plan.get("milestones") and not plan.get("long_tasks"):
            raise HTTPException(status_code=400, detail="At least one task or milestone is required")
        
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
            
            base_date = date.today()

            # 2. Create Milestones (if provided or inferred)
            milestone_ids = []
            milestone_plan_index_to_row = {}
            milestone_plan_index_to_anchor_date = {}
            milestone_specs = _milestone_ordered_list(plan.get("milestones", []))
            previous_due_date = base_date
            for order_index, (plan_idx, milestone_data, due_dt) in enumerate(milestone_specs):
                if not isinstance(milestone_data, dict):
                    continue
                title = milestone_data.get("title")
                if not title:
                    continue

                target_date = due_dt.date() if due_dt else None
                anchor_date = previous_due_date or base_date
                milestone_plan_index_to_anchor_date[plan_idx] = anchor_date

                proposal_offset_days = None
                if target_date:
                    proposal_offset_days = max((target_date - anchor_date).days, 0)

                milestone = Milestone(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    order_index=order_index,
                    title=title,
                    description=milestone_data.get("description", ""),
                    is_critical=bool(milestone_data.get("is_critical", False)),
                    target_date=target_date,
                    proposal_offset_days=proposal_offset_days,
                    status="PENDING"
                )
                db.add(milestone)
                db.flush()
                milestone_ids.append(milestone.id)
                milestone_plan_index_to_row[plan_idx] = milestone

                if target_date is not None:
                    previous_due_date = target_date

            if milestone_ids:
                logger.debug(f"Created {len(milestone_ids)} milestones")

            # 2.5 Create Tasks
            task_ids = []
            for i, task_data in enumerate(tasks_data):
                if not isinstance(task_data, dict):
                    continue
                if not task_data.get("title"):
                    raise ValueError(f"Task {i} is missing title")
                if not task_data.get("due_at") and not task_data.get("deadline"):
                    raise ValueError(f"Task {i} is missing due_at")

                deadline = _parse_plan_datetime(task_data.get("due_at") or task_data.get("deadline"))
                if deadline is None:
                    raise ValueError(f"Task {i} has invalid due_at format")

                milestone_id = None
                proposal_offset_days = None
                milestone_index_raw = task_data.get("milestone_index")
                milestone_index = None
                if milestone_index_raw is not None:
                    try:
                        milestone_index = int(milestone_index_raw)
                    except Exception:
                        milestone_index = None

                if milestone_index is not None and milestone_index in milestone_plan_index_to_row:
                    milestone_row = milestone_plan_index_to_row[milestone_index]
                    milestone_id = milestone_row.id
                    anchor_date = milestone_plan_index_to_anchor_date.get(milestone_index, base_date)
                    proposal_offset_days = max((deadline.date() - anchor_date).days, 0)
                else:
                    proposal_offset_days = (deadline.date() - base_date).days

                task = Task(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    project_id=project.id,
                    milestone_id=milestone_id,
                    title=task_data["title"],
                    description=task_data.get("description", ""),
                    deadline=deadline,
                    proposal_offset_days=proposal_offset_days,
                    evidence_type=task_data.get("evidence_type", "none"),
                    status="OPEN",
                    created_at=datetime.utcnow()
                )
                db.add(task)
                db.flush()
                task_ids.append(task.id)

            logger.debug(f"Created {len(task_ids)} tasks")

            # 2.6 Create Long Task Templates (if provided)
            new_long_templates = []
            for lt in plan.get("long_tasks", []):
                if not isinstance(lt, dict):
                    continue
                title = lt.get("title")
                if not title:
                    continue

                frequency_mode = lt.get("frequency_mode", "interval")
                interval_days = int(lt.get("interval_days") or 1)
                days_of_week = lt.get("days_of_week") or []
                total_cycle_days = int(lt.get("total_cycle_days") or 28)
                default_start_time = lt.get("default_start_time") or "20:00"
                default_end_time = lt.get("default_end_time") or "21:00"

                template = ProjectLongTaskTemplate(
                    user_id=current_user.id,
                    project_id=project.id,
                    title=title,
                    frequency_mode=frequency_mode,
                    interval_days=interval_days,
                    days_of_week=json.dumps(days_of_week, ensure_ascii=False),
                    default_start_time=default_start_time,
                    default_end_time=default_end_time,
                    evidence_type=lt.get("evidence_type", "none"),
                    evidence_criteria=lt.get("evidence_criteria"),
                    total_cycle_days=total_cycle_days,
                    started_at=datetime.utcnow(),
                    is_hidden=False,
                )
                db.add(template)
                db.flush()
                new_long_templates.append(template)
            
            # 3. Update planning_session
            session.project_id = project.id

            # 3.1 Close related conversation session (stop planning state)
            conv_session = db.query(ConversationSession).filter(
                ConversationSession.user_id == current_user.id,
                ConversationSession.planning_session_id == session.id
            ).order_by(ConversationSession.created_at.desc()).first()
            if conv_session:
                conv_session.stage = "completed"
                conv_session.completed_at = datetime.utcnow()
                conv_session.planning_session_id = None
            
            # 4. Commit transaction
            db.commit()

            # 5. Generate today's long tasks if needed (post-commit)
            for template in new_long_templates:
                try:
                    project_long_task_service.maybe_generate_today(db, template)
                except Exception:
                    # Non-blocking for commit flow
                    pass
            
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
        logger.exception("Unexpected error in commit")
        raise HTTPException(status_code=500, detail=f"提交失败: {str(e)}")


@router.get("/latest", response_model=PlanResponse)
async def get_latest_plan(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the latest planning session for the current user.
    Useful for restoring plan review UI after refresh.
    """
    session = db.query(PlanningSession).filter(
        PlanningSession.user_id == current_user.id,
        PlanningSession.project_id.is_(None)
    ).order_by(PlanningSession.created_at.desc()).first()

    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found")

    try:
        plan = _normalize_plan_input(json.loads(session.plan_json))
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid plan data")

    return PlanResponse(
        session_id=session.id,
        plan=plan
    )


@router.get("/{session_id}", response_model=PlanResponse)
async def get_plan_by_id(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific planning session by id (only if owned by current user).
    """
    session = db.query(PlanningSession).filter(
        PlanningSession.id == session_id,
        PlanningSession.user_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Planning session not found")

    try:
        plan = _normalize_plan_input(json.loads(session.plan_json))
    except Exception:
        raise HTTPException(status_code=500, detail="Invalid plan data")

    return PlanResponse(
        session_id=session.id,
        plan=plan
    )
