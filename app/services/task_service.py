"""Task service for task business logic."""
import json
from datetime import datetime
from typing import List, Optional
import logging

from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.models.task import Task, TaskEvidence, PlanTemplate
from app.models.user import User
from app.schemas.task import TaskCreate, TaskEvidenceSubmit
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class TaskService:
    """Task business logic service."""
    
    @staticmethod
    def create_task(db: Session, user: User, task_data: TaskCreate) -> Task:
        """Create a new task."""
        task = Task(
            user_id=user.id,
            title=task_data.title,
            description=task_data.description,
            evidence_type=task_data.evidence_type,
            evidence_criteria=task_data.evidence_criteria,
            deadline=task_data.deadline,
            project_id=task_data.project_id,
            # Schedule fields
            scheduled_time=task_data.scheduled_time,
            scheduled_date=task_data.scheduled_time if task_data.scheduled_time else None,
            duration=task_data.duration,
            is_time_blocked=True if task_data.scheduled_time else False,
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
        query = db.query(Task).filter(Task.user_id == user.id)
        
        if project_id:
            query = query.filter(Task.project_id == project_id)
            
        if filter_type == "active":
            # Active: OPEN, EVIDENCE_SUBMITTED, OVERDUE
            # For specific project view, we usually want all unless specified
            query = query.filter(Task.status.in_(["OPEN", "EVIDENCE_SUBMITTED", "OVERDUE"]))
        elif filter_type == "completed":
            # Completed: DONE, EXCUSED
            query = query.filter(Task.status.in_(["DONE", "EXCUSED"]))
        
        return query.order_by(Task.created_at.desc()).all()
    
    @staticmethod
    def get_task(db: Session, task_id: str, user: User) -> Task:
        """Get a specific task."""
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
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
        
        task.status = "DONE"
        task.completed_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        
        logger.info(f"Task {task_id} completed")
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
                logger.info(f"Task {task_id} evidence passed, marked as DONE")
            else:
                task.status = "OPEN"  # Return to OPEN if failed
                logger.info(f"Task {task_id} evidence failed, returned to OPEN")

            # ---------------------------------------------------------
            # NEW: Auto-create Metrics from AI Result
            # ---------------------------------------------------------
            if ai_result["result"] == "pass" and "extracted_values" in ai_result:
                values = ai_result["extracted_values"]
                
                # Check for Weight (kg)
                if "weight" in values or "kg" in values:
                    try:
                        val = float(values.get("weight") or values.get("kg"))
                        from app.models.metric import MetricEntry
                        metric = MetricEntry(
                            user_id=user.id,
                            metric_type="weight",
                            value=val,
                            unit="kg",
                            task_id=task.id,
                            evidence_id=evidence.id,
                            notes=f"Auto-extracted from task: {task.title}"
                        )
                        db.add(metric)
                    except ValueError:
                        pass
                
                # Check for Body Fat (%)
                if "bodyfat" in values or "body_fat" in values:
                    try:
                        val = float(values.get("bodyfat") or values.get("body_fat"))
                        from app.models.metric import MetricEntry
                        metric = MetricEntry(
                            user_id=user.id,
                            metric_type="bodyfat",
                            value=val,
                            unit="%",
                            task_id=task.id,
                            evidence_id=evidence.id,
                            notes=f"Auto-extracted from task: {task.title}"
                        )
                        db.add(metric)
                    except ValueError:
                        pass

                # Special Handling: Task 1 - "System Weight"
                if task.title.startswith("【系统】本周体重记录") and "weight" not in values and "kg" not in values:
                    # If AI didn't parse it (unlikely for 'number' type), try to use raw content
                    try:
                        val = float(evidence.content)
                        from app.models.metric import MetricEntry
                        metric = MetricEntry(
                            user_id=user.id,
                            metric_type="weight",
                            value=val,
                            unit="kg",
                            task_id=task.id,
                            evidence_id=evidence.id,
                            notes=f"System Task: Weight Record"
                        )
                        db.add(metric)
                    except ValueError:
                        pass

                # Special Handling: Task 2 - "System Body Photo"
                if task.title.startswith("【系统】本周身材记录") and image_path:
                    try:
                        # Call specialized bodyfat estimation
                        fat_result = await ai_service.estimate_bodyfat(image_path, user.username)
                        if "estimated_bodyfat" in fat_result:
                            from app.models.metric import MetricEntry
                            metric = MetricEntry(
                                user_id=user.id,
                                metric_type="bodyfat",
                                value=float(fat_result["estimated_bodyfat"]),
                                unit="%",
                                task_id=task.id,
                                evidence_id=evidence.id,
                                notes=f"AI Visual Estimation: {fat_result.get('analysis', '')}"
                            )
                            db.add(metric)
                    except Exception as e:
                        logger.error(f"Failed to estimate bodyfat in task submission: {e}")
            # ---------------------------------------------------------
        
        except Exception as e:
            logger.error(f"Error in AI judgment: {e}")
            evidence.ai_result = "fail"
            evidence.ai_reason = f"AI判定出错: {str(e)}"
            task.status = "OPEN"
        
        db.add(evidence)
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
        
        # Find tasks that are OPEN and past deadline
        overdue_tasks = db.query(Task).filter(
            Task.status == "OPEN",
            Task.deadline.isnot(None),
            Task.deadline < now
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
