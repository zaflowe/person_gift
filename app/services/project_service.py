"""Project service for project business logic."""
import hashlib
import json
import logging
from datetime import datetime, date, timedelta, time
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project, Milestone
from app.models.task import Task
from app.models.project_long_task import ProjectLongTaskTemplate
from app.models.user import User
from app.schemas.project import ProjectCreate, MilestoneCreate, ProjectUpdate, MilestoneUpdate
from app.services.ai_service import ai_service
from app.services.project_long_task_service import project_long_task_service

logger = logging.getLogger(__name__)


class ProjectService:
    """Project business logic service."""

    @staticmethod
    def _ordered_milestones(db: Session, project_id: str) -> List[Milestone]:
        return db.query(Milestone).filter(
            Milestone.project_id == project_id
        ).order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()

    @staticmethod
    def _milestone_unlock_flags(milestones: List[Milestone]) -> dict[str, bool]:
        flags: dict[str, bool] = {}
        prior_blocked = False
        for m in sorted(milestones, key=lambda x: (x.order_index or 0, x.id)):
            flags[m.id] = not prior_blocked
            if m.status != "ACHIEVED":
                prior_blocked = True
        return flags

    @staticmethod
    def _apply_proposed_target_date(milestone: Milestone, base_date: date | None = None) -> None:
        if milestone.proposal_offset_days is None:
            return
        base = base_date or date.today()
        milestone.target_date = base + timedelta(days=milestone.proposal_offset_days)

    @staticmethod
    def _apply_proposed_milestone_chain(milestones: List[Milestone], base_date: date | None = None) -> None:
        """Project proposal dates for sequential milestones using relative offsets."""
        anchor = base_date or date.today()
        projected_prev: date | None = None
        for milestone in sorted(milestones, key=lambda x: (x.order_index or 0, x.id)):
            if milestone.proposal_offset_days is None:
                continue
            chain_base = projected_prev or anchor
            milestone.target_date = chain_base + timedelta(days=milestone.proposal_offset_days)
            projected_prev = milestone.target_date

    @staticmethod
    def _schedule_task_from_offset(task: Task, base_date: date) -> None:
        if task.proposal_offset_days is None:
            return
        target_date = base_date + timedelta(days=task.proposal_offset_days)
        deadline_time = task.deadline.time() if task.deadline else time(23, 59, 59)
        task.deadline = datetime.combine(target_date, deadline_time)

        # Preserve planned duration while aligning start to target date.
        if task.scheduled_time:
            start_time = task.scheduled_time.time()
        elif task.deadline:
            start_time = (task.deadline - timedelta(minutes=task.duration or 60)).time()
        else:
            start_time = time(0, 0, 0)

        task.scheduled_time = datetime.combine(target_date, start_time)
        task.scheduled_date = task.scheduled_time
        if task.duration and task.duration > 0:
            calc_deadline = task.scheduled_time + timedelta(minutes=task.duration)
            if calc_deadline > task.deadline:
                task.deadline = calc_deadline
        task.proposal_offset_days = None

    @staticmethod
    def _schedule_milestone_group(db: Session, milestone: Milestone, base_date: date) -> None:
        if milestone.proposal_offset_days is not None:
            milestone.target_date = base_date + timedelta(days=milestone.proposal_offset_days)
            milestone.proposal_offset_days = None
        elif milestone.target_date is None:
            milestone.target_date = base_date

        tasks = db.query(Task).filter(Task.milestone_id == milestone.id).all()
        for task in tasks:
            ProjectService._schedule_task_from_offset(task, base_date)
            if task.status == "LOCKED":
                task.status = "OPEN"
            elif task.status not in {"DONE", "EXCUSED"} and not task.status:
                task.status = "OPEN"

    @staticmethod
    def _lock_future_milestone_groups(db: Session, milestones: List[Milestone], unlocked_order: int) -> None:
        future_ids = [m.id for m in milestones if (m.order_index or 0) > unlocked_order]
        if not future_ids:
            return
        future_tasks = db.query(Task).filter(Task.milestone_id.in_(future_ids)).all()
        for task in future_tasks:
            if task.status not in {"DONE", "EXCUSED"}:
                task.status = "LOCKED"

    @staticmethod
    def _activate_project_items(db: Session, project: Project) -> None:
        base_dt = project.user_confirmed_at or datetime.utcnow()
        base_date = base_dt.date()

        tasks = db.query(Task).filter(Task.project_id == project.id, Task.milestone_id.is_(None)).all()
        for task in tasks:
            ProjectService._schedule_task_from_offset(task, base_date)

        ordered_milestones = ProjectService._ordered_milestones(db, project.id)
        if ordered_milestones:
            first_pending = next((m for m in ordered_milestones if m.status == "PENDING"), None)
            if first_pending:
                ProjectService._schedule_milestone_group(db, first_pending, base_date)
                ProjectService._lock_future_milestone_groups(db, ordered_milestones, first_pending.order_index or 0)

        templates = db.query(ProjectLongTaskTemplate).filter(
            ProjectLongTaskTemplate.project_id == project.id
        ).all()
        for template in templates:
            template.started_at = base_dt
            template.updated_at = datetime.utcnow()

    @staticmethod
    def _unlock_next_milestone_group(db: Session, project: Project, achieved_milestone: Milestone) -> None:
        milestones = ProjectService._ordered_milestones(db, project.id)
        next_milestone = next(
            (m for m in milestones if (m.order_index or 0) > (achieved_milestone.order_index or 0) and m.status == "PENDING"),
            None
        )
        if not next_milestone:
            return
        base_date = (achieved_milestone.achieved_at or datetime.utcnow()).date()
        ProjectService._schedule_milestone_group(db, next_milestone, base_date)
        ProjectService._lock_future_milestone_groups(db, milestones, next_milestone.order_index or 0)
    
    @staticmethod
    def create_project(db: Session, user: User, project_data: ProjectCreate) -> Project:
        """Create a new project in PROPOSED status."""
        project = Project(
            user_id=user.id,
            title=project_data.title,
            description=project_data.description,
            success_criteria=project_data.success_criteria,
            failure_criteria=project_data.failure_criteria,
            status="PROPOSED",
            color=project_data.color
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        logger.info(f"Created project {project.id} for user {user.id}")
        return project

    @staticmethod
    def update_project(db: Session, project_id: str, user: User, update_data: "ProjectUpdate") -> Project:
        """Update project details."""
        project = ProjectService.get_project(db, project_id, user)
        
        # Apply updates
        if update_data.title is not None:
            project.title = update_data.title
        if update_data.description is not None:
            project.description = update_data.description
        if update_data.success_criteria is not None:
            project.success_criteria = update_data.success_criteria
        if update_data.failure_criteria is not None:
            project.failure_criteria = update_data.failure_criteria
        if update_data.is_strategic is not None:
            project.is_strategic = update_data.is_strategic
        if update_data.color is not None:
            project.color = update_data.color
            
        db.commit()
        db.refresh(project)
        logger.info(f"Updated project {project.id}")
        return project
    
    @staticmethod
    def get_projects(db: Session, user: User) -> List[Project]:
        """Get user's projects."""
        return db.query(Project).filter(
            Project.user_id == user.id
        ).order_by(Project.created_at.desc()).all()
    
    @staticmethod
    def get_project(db: Session, project_id: str, user: User) -> Project:
        """Get a specific project."""
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user.id
        ).first()
        
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return project
    
    @staticmethod
    async def request_analysis(db: Session, project_id: str, user: User) -> Project:
        """
        Request AI analysis for project breakdown.
        
        This internally calls AI service and writes ai_confirmed_at.
        Does NOT expose a separate /ai-confirm public endpoint.
        """
        project = ProjectService.get_project(db, project_id, user)
        
        if project.status != "PROPOSED":
            raise HTTPException(
                status_code=400,
                detail="只有 PROPOSED 状态的项目可以请求分析"
            )
        
        # Call AI service
        analysis_result = await ai_service.analyze_project(
            title=project.title,
            description=project.description,
            success_criteria=project.success_criteria,
            failure_criteria=project.failure_criteria
        )
        
        # Store AI analysis
        project.ai_analysis = json.dumps(analysis_result, ensure_ascii=False)
        project.ai_confirmed_at = datetime.utcnow()  # AI confirms internally
        
        # Create suggested milestones
        for milestone_data in analysis_result.get("suggested_milestones", []):
            milestone = Milestone(
                project_id=project.id,
                title=milestone_data["title"],
                description=milestone_data.get("description"),
                is_critical=milestone_data.get("is_critical", False)
            )
            db.add(milestone)
        
        db.commit()
        db.refresh(project)
        
        logger.info(f"Project {project_id} analyzed by AI")
        return project
    
    @staticmethod
    def user_confirm(db: Session, project_id: str, user: User) -> Project:
        """
        User confirms the project breakdown.
        
        This writes user_confirmed_at and agreement_hash.
        If both user and AI have confirmed, status becomes ACTIVE.
        """
        project = ProjectService.get_project(db, project_id, user)
        
        if project.status != "PROPOSED":
            raise HTTPException(
                status_code=400,
                detail="只有 PROPOSED 状态的项目可以确认"
            )
        
        # Set user confirmation
        project.user_confirmed_at = datetime.utcnow()
        
        # Auto-confirm AI if missing (to ensure activation)
        if not project.ai_confirmed_at:
            project.ai_confirmed_at = datetime.utcnow()
        
        # Generate agreement hash if both are confirmed
        if project.user_confirmed_at and project.ai_confirmed_at:
            # Create canonical representation for hashing
            milestones = db.query(Milestone).filter(
                Milestone.project_id == project.id
            ).all()
            
            canonical_data = {
                "title": project.title,
                "description": project.description,
                "success_criteria": project.success_criteria or "",
                "failure_criteria": project.failure_criteria or "",
                "milestones": [
                    {
                        "title": m.title,
                        "is_critical": m.is_critical
                    } for m in milestones
                ]
            }
            
            canonical_json = json.dumps(canonical_data, sort_keys=True, ensure_ascii=False)
            agreement_hash = hashlib.sha256(canonical_json.encode()).hexdigest()
            
            project.agreement_hash = agreement_hash
            project.status = "ACTIVE"
            ProjectService._activate_project_items(db, project)
            
            logger.info(f"Project {project_id} activated with hash {agreement_hash}")
        
        db.commit()
        db.refresh(project)

        if project.status == "ACTIVE":
            templates = db.query(ProjectLongTaskTemplate).filter(
                ProjectLongTaskTemplate.project_id == project.id
            ).all()
            for template in templates:
                try:
                    project_long_task_service.maybe_generate_today(db, template)
                except Exception:
                    pass

        return project
    
    @staticmethod
    def create_milestone(
        db: Session,
        project_id: str,
        user: User,
        milestone_data: MilestoneCreate
    ) -> Milestone:
        """Create a milestone for a project."""
        project = ProjectService.get_project(db, project_id, user)
        proposal_offset_days = None
        if project.status == "PROPOSED" and milestone_data.target_date:
            proposal_offset_days = (milestone_data.target_date - date.today()).days

        payload = milestone_data.dict()
        requested_order = payload.pop("order_index", None)
        if requested_order is None:
            max_order = db.query(Milestone).filter(Milestone.project_id == project.id).count()
            requested_order = max_order

        milestone = Milestone(
            project_id=project.id,
            proposal_offset_days=proposal_offset_days,
            order_index=requested_order,
            **payload
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone
    
    @staticmethod
    def get_milestones(db: Session, project_id: str, user: User) -> List[Milestone]:
        """Get project milestones."""
        project = ProjectService.get_project(db, project_id, user)
        milestones = db.query(Milestone).filter(
            Milestone.project_id == project.id
        ).order_by(Milestone.order_index.asc(), Milestone.id.asc()).all()

        if project.status == "PROPOSED":
            ProjectService._apply_proposed_milestone_chain(milestones, date.today())

        unlock_flags = ProjectService._milestone_unlock_flags(milestones)
        for milestone in milestones:
            milestone.is_unlocked = unlock_flags.get(milestone.id, True)

        return milestones
        
    @staticmethod
    def update_milestone(
        db: Session,
        project_id: str,
        milestone_id: str,
        user: User,
        update_data: "MilestoneUpdate"
    ) -> Milestone:
        """Update a milestone."""
        project = ProjectService.get_project(db, project_id, user)
        
        milestone = db.query(Milestone).filter(
            Milestone.id == milestone_id,
            Milestone.project_id == project.id
        ).first()
        
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
            
        if update_data.title is not None:
            milestone.title = update_data.title
        if update_data.description is not None:
            milestone.description = update_data.description
        if update_data.is_critical is not None:
            milestone.is_critical = update_data.is_critical
        if update_data.target_date is not None:
            milestone.target_date = update_data.target_date
            if project.status == "PROPOSED":
                milestone.proposal_offset_days = (update_data.target_date - date.today()).days
        if update_data.order_index is not None:
            milestone.order_index = update_data.order_index
            
        db.commit()
        db.refresh(milestone)
        logger.info(f"Updated milestone {milestone.id}")
        return milestone

    @staticmethod
    def delete_milestone(
        db: Session,
        project_id: str,
        milestone_id: str,
        user: User
    ):
        """Delete a milestone."""
        project = ProjectService.get_project(db, project_id, user)
        
        milestone = db.query(Milestone).filter(
            Milestone.id == milestone_id,
            Milestone.project_id == project.id
        ).first()
        
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
            
        db.delete(milestone)
        db.commit()
        logger.info(f"Deleted milestone {milestone_id}")
    
    @staticmethod
    def mark_milestone_achieved(
        db: Session,
        project_id: str,
        milestone_id: str,
        user: User
    ) -> Milestone:
        """
        Mark a milestone as achieved (only for evidence_type=none).
        
        This is an action-based interface, not a direct status PATCH.
        Triggers project status check after milestone update.
        """
        project = ProjectService.get_project(db, project_id, user)
        
        milestone = db.query(Milestone).filter(
            Milestone.id == milestone_id,
            Milestone.project_id == project.id
        ).first()
        
        if not milestone:
            raise HTTPException(status_code=404, detail="Milestone not found")
        
        if milestone.status != "PENDING":
            raise HTTPException(
                status_code=400,
                detail=f"里程碑当前状态 {milestone.status} 不允许标记为达成"
            )
        
        milestone.status = "ACHIEVED"
        milestone.achieved_at = datetime.utcnow()

        ProjectService._unlock_next_milestone_group(db, project, milestone)
        db.commit()
        
        # Check if project should transition to SUCCESS or remain ACTIVE
        ProjectService._check_project_status(db, project)
        
        db.refresh(milestone)
        logger.info(f"Milestone {milestone_id} marked as achieved")
        return milestone
    
    @staticmethod
    def _check_project_status(db: Session, project: Project):
        """
        Internal method to check and update project status based on milestones.
        
        SUCCESS: All critical milestones are ACHIEVED
        FAILURE: Any critical milestone is FAILED
        """
        if project.status != "ACTIVE":
            return
        
        milestones = db.query(Milestone).filter(
            Milestone.project_id == project.id
        ).all()

        if not milestones:
            return

        critical_milestones = [m for m in milestones if m.is_critical]
        if not critical_milestones:
            critical_milestones = milestones
        
        # Check for failure
        if any(m.status == "FAILED" for m in critical_milestones):
            project.status = "FAILURE"
            project.resolved_at = datetime.utcnow()
            logger.info(f"Project {project.id} marked as FAILURE")
        
        # Check for success
        elif all(m.status == "ACHIEVED" for m in critical_milestones):
            project.status = "SUCCESS"
            project.resolved_at = datetime.utcnow()
            logger.info(f"Project {project.id} marked as SUCCESS")
        
        db.commit()
