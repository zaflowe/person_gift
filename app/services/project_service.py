"""Project service for project business logic."""
import hashlib
import json
import logging
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.project import Project, Milestone
from app.models.user import User
from app.schemas.project import ProjectCreate, MilestoneCreate, ProjectUpdate, MilestoneUpdate
from app.services.ai_service import ai_service

logger = logging.getLogger(__name__)


class ProjectService:
    """Project business logic service."""
    
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
            
            logger.info(f"Project {project_id} activated with hash {agreement_hash}")
        
        db.commit()
        db.refresh(project)
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
        
        milestone = Milestone(
            project_id=project.id,
            **milestone_data.dict()
        )
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        return milestone
    
    @staticmethod
    def get_milestones(db: Session, project_id: str, user: User) -> List[Milestone]:
        """Get project milestones."""
        project = ProjectService.get_project(db, project_id, user)
        return db.query(Milestone).filter(
            Milestone.project_id == project.id
        ).all()
        
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
        
        critical_milestones = [m for m in milestones if m.is_critical]
        
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
