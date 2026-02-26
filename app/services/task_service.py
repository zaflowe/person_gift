"""Task service for task business logic."""
import json
from datetime import datetime, date, time, timedelta
from typing import List, Optional, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import or_
from fastapi import HTTPException, UploadFile

from app.models.task import Task, TaskEvidence, PlanTemplate
from app.models.project import Project, Milestone
from app.models.user import User
from app.schemas.task import TaskCreate, TaskEvidenceSubmit
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class TaskService:
    """Task business logic service."""

    IN_PROGRESS_LIMIT = 5
    FROZEN_AFTER_DAYS = 14
    TERMINAL_STATUSES = {"DONE", "EXCUSED"}

    @staticmethod
    def _is_task_milestone_unlocked(db: Session, task: Task, project: Optional[Project] = None) -> bool:
        if not task.project_id or not task.milestone_id:
            return True
        proj = project or db.query(Project).filter(Project.id == task.project_id).first()
        if not proj or proj.status != "ACTIVE":
            return True

        milestones = db.query(Milestone).filter(
            Milestone.project_id == task.project_id
        ).order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()
        prior_blocked = False
        for milestone in milestones:
            unlocked = not prior_blocked
            if milestone.id == task.milestone_id:
                return unlocked
            if milestone.status != "ACHIEVED":
                prior_blocked = True
        return True

    @staticmethod
    def _sync_task_locked_state(db: Session, task: Task) -> bool:
        """Synchronize task LOCKED/Open state for active project milestone tasks."""
        if not task.project_id or not task.milestone_id or task.status in TaskService.TERMINAL_STATUSES:
            return False
        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project or project.status != "ACTIVE":
            return False
        unlocked = TaskService._is_task_milestone_unlocked(db, task, project)
        target_status = None
        if unlocked:
            if task.status == "LOCKED":
                target_status = "OPEN"
        else:
            if task.status not in {"LOCKED"}:
                target_status = "LOCKED"
        if target_status is None:
            return False
        # Preserve evidence-submitted only when unlocked
        if unlocked and task.status == "EVIDENCE_SUBMITTED":
            return False
        task.status = target_status
        return True

    @staticmethod
    def _sync_project_milestone_status_from_task(db: Session, task: Task) -> None:
        """Auto-complete milestone and unlock next milestone when all milestone tasks are done."""
        if not task.project_id or not task.milestone_id:
            return

        project = db.query(Project).filter(Project.id == task.project_id).first()
        if not project or project.status != "ACTIVE":
            return

        from app.services.project_service import ProjectService

        milestone = db.query(Milestone).filter(
            Milestone.id == task.milestone_id,
            Milestone.project_id == project.id
        ).first()
        if not milestone:
            return

        milestone_tasks = db.query(Task).filter(Task.milestone_id == milestone.id).all()
        if milestone_tasks and all(t.status in TaskService.TERMINAL_STATUSES for t in milestone_tasks):
            if milestone.status != "ACHIEVED":
                milestone.status = "ACHIEVED"
                milestone.achieved_at = datetime.utcnow()
                ProjectService._unlock_next_milestone_group(db, project, milestone)

        # Inline project status check (avoid nested commits from ProjectService._check_project_status)
        milestones = db.query(Milestone).filter(Milestone.project_id == project.id).all()
        if not milestones:
            return
        critical_milestones = [m for m in milestones if m.is_critical] or milestones
        if any(m.status == "FAILED" for m in critical_milestones):
            project.status = "FAILURE"
            project.resolved_at = datetime.utcnow()
        elif all(m.status == "ACHIEVED" for m in critical_milestones):
            project.status = "SUCCESS"
            project.resolved_at = datetime.utcnow()

    @staticmethod
    def _validate_task_project_milestone(
        db: Session,
        user: User,
        *,
        project_id: Optional[str],
        milestone_id: Optional[str],
    ) -> Optional[Milestone]:
        if milestone_id is None:
            return None

        milestone = db.query(Milestone).join(Project, Milestone.project_id == Project.id).filter(
            Milestone.id == milestone_id,
            Project.user_id == user.id,
        ).first()
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")

        if project_id and milestone.project_id != project_id:
            raise HTTPException(status_code=400, detail="Task milestone does not belong to the selected project")
        return milestone

    @staticmethod
    def _round_up_to_next_hour(now: Optional[datetime] = None) -> datetime:
        current = now or datetime.utcnow()
        rounded = current.replace(minute=0, second=0, microsecond=0)
        if rounded <= current:
            rounded += timedelta(hours=1)
        return rounded

    @staticmethod
    def _normalize_task_window(
        start_at: Optional[datetime],
        deadline_at: Optional[datetime],
        *,
        now: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime]:
        """Ensure each task has both start and deadline timestamps."""
        current = now or datetime.utcnow()
        start = start_at
        deadline = deadline_at

        if start is None and deadline is None:
            start = TaskService._round_up_to_next_hour(current)
            deadline = start + timedelta(hours=1)
        elif start is None and deadline is not None:
            start = deadline - timedelta(hours=1)
        elif start is not None and deadline is None:
            deadline = start + timedelta(hours=1)

        if deadline <= start:
            deadline = start + timedelta(hours=1)

        return start, deadline

    @staticmethod
    def _apply_task_window(task: Task, start_at: Optional[datetime], deadline_at: Optional[datetime]) -> None:
        start_at, deadline_at = TaskService._normalize_task_window(start_at, deadline_at)
        task.scheduled_time = start_at
        task.scheduled_date = start_at
        task.deadline = deadline_at
        task.is_time_blocked = True
        duration_minutes = int((deadline_at - start_at).total_seconds() // 60)
        task.duration = max(duration_minutes, 1)

    @staticmethod
    def cleanup_stale_recurring_instances(
        db: Session,
        user_id: Optional[str] = None,
        now: Optional[datetime] = None,
    ) -> int:
        """
        Delete unfinished recurring-generated tasks from previous days.

        Applies to both habits (template_id) and project long tasks (long_task_template_id).
        """
        current = now or datetime.utcnow()
        start_of_today = datetime(current.year, current.month, current.day)
        query = db.query(Task).filter(
            Task.generated_for_date.isnot(None),
            or_(Task.template_id.isnot(None), Task.long_task_template_id.isnot(None)),
            Task.generated_for_date < start_of_today,
            ~Task.status.in_(list(TaskService.TERMINAL_STATUSES)),
        )
        if user_id:
            query = query.filter(Task.user_id == user_id)

        stale_tasks = query.all()
        if not stale_tasks:
            return 0

        for task in stale_tasks:
            db.delete(task)
        db.commit()
        logger.info("Deleted %s stale unfinished recurring-generated task(s)", len(stale_tasks))
        return len(stale_tasks)

    @staticmethod
    def _task_tags(task: Task) -> list[str]:
        raw = task.tags
        if not raw:
            return []
        if isinstance(raw, list):
            return [str(x) for x in raw]
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    return [str(x) for x in parsed]
            except Exception:
                return []
        return []

    @staticmethod
    def _task_has_metric_hint(task: Task, metric_type: str) -> bool:
        tags = [t.lower() for t in TaskService._task_tags(task)]
        title = (task.title or "").lower()
        desc = (task.description or "").lower()
        criteria = (task.evidence_criteria or "").lower()
        blob = " ".join([title, desc, criteria] + tags)

        if metric_type == "bodyfat":
            keywords = ["bodyfat", "body_fat", "体脂", "身材", "照片", "photo"]
        else:
            keywords = ["weight", "体重", "kg", "公斤"]
        return any(k in blob for k in keywords)

    @staticmethod
    def _upsert_task_metric(
        db: Session,
        *,
        user_id: str,
        task_id: str,
        evidence_id: Optional[str],
        metric_type: str,
        value: float,
        unit: str,
        notes: str,
    ) -> None:
        from app.models.metric import MetricEntry

        existing = db.query(MetricEntry).filter(
            MetricEntry.task_id == task_id,
            MetricEntry.metric_type == metric_type,
        ).order_by(MetricEntry.created_at.desc()).first()

        if existing:
            existing.value = value
            existing.unit = unit
            existing.evidence_id = evidence_id
            existing.notes = notes
            existing.created_at = datetime.utcnow()
            return

        db.add(MetricEntry(
            user_id=user_id,
            metric_type=metric_type,
            value=value,
            unit=unit,
            task_id=task_id,
            evidence_id=evidence_id,
            notes=notes,
        ))

    @staticmethod
    def _apply_proposed_deadline(task: Task, base_date: date | None = None) -> None:
        if task.proposal_offset_days is None:
            return
        base = base_date or date.today()
        target_date = base + timedelta(days=task.proposal_offset_days)
        deadline_time = task.deadline.time() if task.deadline else time(23, 59, 59)
        task.deadline = datetime.combine(target_date, deadline_time)

    @staticmethod
    def _apply_proposed_project_task_chain(db: Session, tasks: List[Task], project: Project, base_date: date | None = None) -> None:
        base = base_date or date.today()
        milestones = db.query(Milestone).filter(
            Milestone.project_id == project.id
        ).order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()

        milestone_anchor_by_id: dict[str, date] = {}
        projected_prev: date | None = None
        for milestone in milestones:
            anchor = projected_prev or base
            milestone_anchor_by_id[milestone.id] = anchor
            if milestone.proposal_offset_days is not None:
                projected_prev = anchor + timedelta(days=milestone.proposal_offset_days)
            elif milestone.target_date:
                projected_prev = milestone.target_date

        for task in tasks:
            if task.proposal_offset_days is None:
                continue
            anchor = milestone_anchor_by_id.get(task.milestone_id) if task.milestone_id else base
            anchor = anchor or base
            target_date = anchor + timedelta(days=task.proposal_offset_days)
            deadline_time = task.deadline.time() if task.deadline else time(23, 59, 59)
            task.deadline = datetime.combine(target_date, deadline_time)

    @staticmethod
    def _proposal_anchor_for_task(db: Session, task: Task, project: Project, base_date: date | None = None) -> date:
        base = base_date or date.today()
        if not task.milestone_id:
            return base

        milestones = db.query(Milestone).filter(
            Milestone.project_id == project.id
        ).order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()
        projected_prev: date | None = None
        for milestone in milestones:
            anchor = projected_prev or base
            if milestone.id == task.milestone_id:
                return anchor
            if milestone.proposal_offset_days is not None:
                projected_prev = anchor + timedelta(days=milestone.proposal_offset_days)
            elif milestone.target_date:
                projected_prev = milestone.target_date
        return base
    
    @staticmethod
    def create_task(db: Session, user: User, task_data: TaskCreate) -> Task:
        """Create a new task."""
        milestone = TaskService._validate_task_project_milestone(
            db, user, project_id=task_data.project_id, milestone_id=task_data.milestone_id
        )
        project_id = task_data.project_id or (milestone.project_id if milestone else None)

        project = None
        proposal_offset_days = None
        if project_id and task_data.deadline:
            project = db.query(Project).filter(
                Project.id == project_id,
                Project.user_id == user.id
            ).first()
            if project and project.status == "PROPOSED":
                if milestone:
                    anchor = TaskService._proposal_anchor_for_task(
                        db,
                        Task(project_id=project_id, milestone_id=milestone.id),
                        project,
                        date.today(),
                    )
                    proposal_offset_days = max((task_data.deadline.date() - anchor).days, 0)
                else:
                    proposal_offset_days = (task_data.deadline.date() - date.today()).days

        normalized_start, normalized_deadline = TaskService._normalize_task_window(
            task_data.scheduled_time,
            task_data.deadline,
        )
        if project_id and proposal_offset_days is None:
            if project is None:
                project = db.query(Project).filter(
                    Project.id == project_id,
                    Project.user_id == user.id
                ).first()
            if project and project.status == "PROPOSED":
                if milestone:
                    anchor = TaskService._proposal_anchor_for_task(
                        db,
                        Task(project_id=project_id, milestone_id=milestone.id),
                        project,
                        date.today(),
                    )
                    proposal_offset_days = max((normalized_deadline.date() - anchor).days, 0)
                else:
                    proposal_offset_days = (normalized_deadline.date() - date.today()).days

        task = Task(
            user_id=user.id,
            title=task_data.title,
            description=task_data.description,
            evidence_type=task_data.evidence_type,
            evidence_criteria=task_data.evidence_criteria,
            deadline=normalized_deadline,
            proposal_offset_days=proposal_offset_days,
            project_id=project_id,
            milestone_id=milestone.id if milestone else None,
            # Schedule fields
            scheduled_time=normalized_start,
            scheduled_date=normalized_start,
            duration=task_data.duration if (task_data.duration and task_data.duration > 0) else int((normalized_deadline - normalized_start).total_seconds() // 60),
            is_time_blocked=True,
            status="OPEN",
            tags=json.dumps(task_data.tags, ensure_ascii=False) if task_data.tags else "[]"
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        logger.info(f"Created task {task.id} for user {user.id}")
        return task
    
    @staticmethod
    def get_tasks(
        db: Session,
        user: User,
        filter_type: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> List[Task]:
        """Get user's tasks with optional filtering."""
        TaskService.cleanup_stale_recurring_instances(db, user.id)
        query = db.query(Task).filter(Task.user_id == user.id)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
        else:
            query = query.outerjoin(Project, Task.project_id == Project.id).filter(
                or_(Task.project_id.is_(None), Project.status != "PROPOSED")
            )
            
        if filter_type == "active":
            # Active: OPEN, EVIDENCE_SUBMITTED, OVERDUE
            # For specific project view, we usually want all unless specified
            query = query.filter(Task.status.in_(["OPEN", "EVIDENCE_SUBMITTED", "OVERDUE"]))
        elif filter_type == "completed":
            # Completed: DONE, EXCUSED
            query = query.filter(Task.status.in_(["DONE", "EXCUSED"]))
        
        tasks = query.order_by(Task.created_at.desc()).all()

        mutated = False
        for task in tasks:
            if TaskService._sync_task_locked_state(db, task):
                mutated = True
            if task.status in TaskService.TERMINAL_STATUSES:
                continue
            if task.deadline is None or task.scheduled_time is None:
                TaskService._apply_task_window(task, task.scheduled_time, task.deadline)
                mutated = True
        if mutated:
            db.commit()

        if project_id:
            project = db.query(Project).filter(
                Project.id == project_id,
                Project.user_id == user.id
            ).first()
            if project and project.status == "PROPOSED":
                TaskService._apply_proposed_project_task_chain(db, tasks, project, date.today())

        return tasks
    
    @staticmethod
    def get_task(db: Session, task_id: str, user: User) -> Task:
        """Get a specific task."""
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.project_id:
            project = db.query(Project).filter(
                Project.id == task.project_id,
                Project.user_id == user.id
            ).first()
            if TaskService._sync_task_locked_state(db, task):
                db.commit()
                db.refresh(task)
            if project and project.status == "PROPOSED":
                TaskService._apply_proposed_project_task_chain(db, [task], project, date.today())
        return task
    
    @staticmethod
    async def complete_task(db: Session, task_id: str, user: User) -> Task:
        """
        Complete a task (only for evidence_type=none).
        
        Enforces: Task can only be completed this way if it doesn't require evidence.
        """
        task = TaskService.get_task(db, task_id, user)
        
        # Only allow direct completion for tasks without evidence requirement
        if task.evidence_type and task.evidence_type != "none":
            raise HTTPException(
                status_code=400,
                detail="此任务需要提交证据，不能直接完成"
            )
        
        if task.status not in ["OPEN", "OVERDUE"]:
            raise HTTPException(
                status_code=400,
                detail=f"任务当前状态 {task.status} 不允许完成"
            )
        
        if task.status == "LOCKED" or not TaskService._is_task_milestone_unlocked(db, task):
            raise HTTPException(status_code=400, detail="Task is locked until the previous milestone is completed")

        task.status = "DONE"
        task.completed_at = datetime.utcnow()
        TaskService._sync_project_milestone_status_from_task(db, task)
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} completed")
        return task

    @staticmethod
    def update_task(db: Session, task_id: str, user: User, updates: dict) -> Task:
        """Update task details (for PROPOSED project tasks)."""
        task = TaskService.get_task(db, task_id, user)

        project = None
        if task.project_id:
            project = db.query(Project).filter(
                Project.id == task.project_id,
                Project.user_id == user.id
            ).first()
            if project and project.status != "PROPOSED":
                restricted_fields = {"title", "description", "evidence_type", "evidence_criteria", "tags", "milestone_id"}
                if any(field in updates for field in restricted_fields):
                    raise HTTPException(status_code=400, detail="Active project tasks only allow scheduling changes")

        pending_start = task.scheduled_time
        pending_deadline = task.deadline

        if "title" in updates and updates["title"] is not None:
            task.title = updates["title"]
        if "description" in updates and updates["description"] is not None:
            task.description = updates["description"]
        if "quick_start_action" in updates:
            task.quick_start_action = updates["quick_start_action"]
        if "evidence_type" in updates and updates["evidence_type"] is not None:
            task.evidence_type = updates["evidence_type"]
        if "evidence_criteria" in updates:
            task.evidence_criteria = updates["evidence_criteria"]
        if "deadline" in updates:
            pending_deadline = updates["deadline"]
            if updates["deadline"] is not None and project and project.status == "PROPOSED":
                anchor = TaskService._proposal_anchor_for_task(db, task, project, date.today())
                task.proposal_offset_days = max((updates["deadline"].date() - anchor).days, 0)
        if "tags" in updates and updates["tags"] is not None:
            task.tags = json.dumps(updates["tags"], ensure_ascii=False)
        if "scheduled_time" in updates:
            pending_start = updates["scheduled_time"]
        if "duration" in updates and updates["duration"] is not None:
            task.duration = updates["duration"]
        if "board_lane" in updates:
            task.board_lane = updates["board_lane"]
            task.board_lane_updated_at = datetime.utcnow() if updates["board_lane"] else None
        if "milestone_id" in updates:
            milestone_id = updates["milestone_id"]
            if milestone_id is None:
                task.milestone_id = None
            else:
                milestone = TaskService._validate_task_project_milestone(
                    db, user, project_id=task.project_id, milestone_id=milestone_id
                )
                task.milestone_id = milestone.id if milestone else None
            if project and project.status == "PROPOSED" and task.deadline:
                anchor = TaskService._proposal_anchor_for_task(db, task, project, date.today())
                task.proposal_offset_days = max((task.deadline.date() - anchor).days, 0)

        if "deadline" in updates or "scheduled_time" in updates:
            TaskService._apply_task_window(task, pending_start, pending_deadline)

        db.commit()
        db.refresh(task)
        logger.info(f"Updated task {task_id}")
        return task
    
    @staticmethod
    async def submit_evidence(
        db: Session,
        task_id: str,
        user: User,
        evidence_data: TaskEvidenceSubmit,
        image_file: Optional[UploadFile] = None
    ) -> TaskEvidence:
        """
        Submit evidence for a task and trigger AI judgment.
        
        This enforces the rule that tasks must go through evidence verification.
        """
        task = TaskService.get_task(db, task_id, user)
        
        if task.status not in ["OPEN", "OVERDUE", "EVIDENCE_SUBMITTED"]:
            raise HTTPException(
                status_code=400,
                detail=f"任务当前状态 {task.status} 不允许提交证据"
            )
        
        if task.status == "LOCKED" or not TaskService._is_task_milestone_unlocked(db, task):
            raise HTTPException(status_code=400, detail="Task is locked until the previous milestone is completed")

        # Handle image upload if provided
        image_path = None
        if image_file and evidence_data.evidence_type == "image":
            import os
            import uuid
            
            # Save image
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_extension = image_file.filename.split(".")[-1]
            image_filename = f"{uuid.uuid4()}.{file_extension}"
            image_path = os.path.join(upload_dir, image_filename)
            
            with open(image_path, "wb") as f:
                content = await image_file.read()
                f.write(content)
        
        # Create evidence record
        evidence = TaskEvidence(
            task_id=task.id,
            evidence_type=evidence_data.evidence_type,
            content=evidence_data.content,
            image_path=image_path
        )
        db.add(evidence)
        db.flush()
        
        # Update task status to EVIDENCE_SUBMITTED
        task.status = "EVIDENCE_SUBMITTED"
        
        # Call AI service to judge evidence
        try:
            ai_result = await ai_service.judge_evidence(
                task_title=task.title,
                evidence_type=evidence_data.evidence_type,
                evidence_criteria=task.evidence_criteria or "",
                evidence_content=evidence_data.content,
                image_path=image_path
            )
            
            evidence.ai_result = ai_result["result"]
            evidence.ai_reason = ai_result["reason"]
            evidence.extracted_values = json.dumps(ai_result.get("extracted_values", {}))
            
            # Update task status based on AI result
            if ai_result["result"] == "pass":
                task.status = "DONE"
                task.completed_at = datetime.utcnow()
                TaskService._sync_project_milestone_status_from_task(db, task)
                logger.info(f"Task {task_id} evidence passed, marked as DONE")
            else:
                task.status = "OPEN"  # Return to OPEN if failed
                logger.info(f"Task {task_id} evidence failed, returned to OPEN")

            # ---------------------------------------------------------
            # Auto-create metrics from AI result / task semantics
            # ---------------------------------------------------------
            if ai_result["result"] == "pass":
                values = ai_result.get("extracted_values") or {}
                created_weight_metric = False
                created_bodyfat_metric = False

                # 1) Structured extraction from AI judgment
                if isinstance(values, dict):
                    if "weight" in values or "kg" in values:
                        try:
                            val = float(values.get("weight") or values.get("kg"))
                            TaskService._upsert_task_metric(
                                db,
                                user_id=user.id,
                                task_id=task.id,
                                evidence_id=evidence.id,
                                metric_type="weight",
                                value=val,
                                unit="kg",
                                notes=f"Auto-extracted from task: {task.title}",
                            )
                            created_weight_metric = True
                        except (TypeError, ValueError):
                            pass

                    if "bodyfat" in values or "body_fat" in values:
                        try:
                            val = float(values.get("bodyfat") or values.get("body_fat"))
                            TaskService._upsert_task_metric(
                                db,
                                user_id=user.id,
                                task_id=task.id,
                                evidence_id=evidence.id,
                                metric_type="bodyfat",
                                value=val,
                                unit="%",
                                notes=f"Auto-extracted from task: {task.title}",
                            )
                            created_bodyfat_metric = True
                        except (TypeError, ValueError):
                            pass

                # 2) Fallback for weight tasks (manual/system text/number entry)
                if (
                    not created_weight_metric
                    and evidence.content
                    and TaskService._task_has_metric_hint(task, "weight")
                ):
                    try:
                        val = float(str(evidence.content).strip())
                        TaskService._upsert_task_metric(
                            db,
                            user_id=user.id,
                            task_id=task.id,
                            evidence_id=evidence.id,
                            metric_type="weight",
                            value=val,
                            unit="kg",
                            notes=f"Weight task fallback parse: {task.title}",
                        )
                        created_weight_metric = True
                    except (TypeError, ValueError):
                        pass

                # 3) Fallback for bodyfat photo tasks (system weekly + dashboard + button-created tasks)
                if (
                    not created_bodyfat_metric
                    and image_path
                    and evidence_data.evidence_type == "image"
                    and TaskService._task_has_metric_hint(task, "bodyfat")
                ):
                    try:
                        fat_result = await ai_service.estimate_bodyfat(image_path, user.username)
                        estimated = fat_result.get("estimated_bodyfat")
                        if estimated is not None:
                            TaskService._upsert_task_metric(
                                db,
                                user_id=user.id,
                                task_id=task.id,
                                evidence_id=evidence.id,
                                metric_type="bodyfat",
                                value=float(estimated),
                                unit="%",
                                notes=f"AI Visual Estimation: {fat_result.get('analysis', '')}",
                            )
                            created_bodyfat_metric = True
                            logger.info("Created bodyfat metric from bodyfat photo task: task_id=%s value=%s", task.id, estimated)
                    except Exception as e:
                        logger.error(f"Failed to estimate bodyfat in task submission: {e}")
            # ---------------------------------------------------------
        
        except Exception as e:
            logger.error(f"Error in AI judgment: {e}")
            evidence.ai_result = "fail"
            evidence.ai_reason = f"AI判定出错: {str(e)}"
            task.status = "OPEN"
        
        db.commit()
        db.refresh(evidence)
        
        return evidence
    
    @staticmethod
    def update_overdue_tasks(db: Session):
        """
        Background job to update overdue tasks.
        Called by scheduler periodically.
        """
        now = datetime.utcnow()
        TaskService.cleanup_stale_recurring_instances(db, now=now)
        
        # Find tasks that are OPEN and past deadline (exclude PROPOSED project tasks)
        overdue_tasks = db.query(Task).outerjoin(Project, Task.project_id == Project.id).filter(
            Task.status == "OPEN",
            Task.deadline.isnot(None),
            Task.deadline < now,
            or_(Task.project_id.is_(None), Project.status != "PROPOSED")
        ).all()
        
        for task in overdue_tasks:
            # Check if day pass is active for this task's user
            from app.services.exemption_service import ExemptionService
            if not ExemptionService.is_day_pass_active(db, task.user_id, now.date()):
                task.status = "OVERDUE"
        
        db.commit()
        logger.info(f"Updated {len(overdue_tasks)} overdue tasks")


class PlanTemplateService:
    """Plan template service."""
    
    @staticmethod
    def create_template(db: Session, user: User, template_data) -> PlanTemplate:
        """Create a plan template."""
        template = PlanTemplate(
            user_id=user.id,
            **template_data.dict()
        )
        db.add(template)
        db.commit()
        db.refresh(template)
        return template
    
    @staticmethod
    def get_templates(db: Session, user: User) -> List[PlanTemplate]:
        """Get user's plan templates."""
        return db.query(PlanTemplate).filter(
            PlanTemplate.user_id == user.id
        ).all()
