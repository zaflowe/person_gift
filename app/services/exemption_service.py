"""Exemption service for managing exemption quotas and usage."""
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.exemption import ExemptionQuota, ExemptionLog
from app.models.task import Task
from app.models.user import User

logger = logging.getLogger(__name__)


class ExemptionService:
    """Exemption business logic service."""
    
    @staticmethod
    def get_or_create_weekly_quota(db: Session, user: User, target_date: date = None) -> ExemptionQuota:
        """
        Get or create exemption quota for the week containing target_date.
        
        Week starts on Monday.
        """
        if not target_date:
            target_date = datetime.utcnow().date()
        
        # Calculate Monday of the week
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        
        # Try to find existing quota
        quota = db.query(ExemptionQuota).filter(
            ExemptionQuota.user_id == user.id,
            ExemptionQuota.week_start == week_start
        ).first()
        
        if not quota:
            # Create new weekly quota
            quota = ExemptionQuota(
                user_id=user.id,
                week_start=week_start,
                day_pass_total=1,
                day_pass_used=0,
                rule_break_total=2,
                rule_break_used=0
            )
            db.add(quota)
            db.commit()
            db.refresh(quota)
            logger.info(f"Created weekly quota for user {user.id}, week {week_start}")
        
        return quota
    
    @staticmethod
    def get_current_quota(db: Session, user: User) -> ExemptionQuota:
        """Get current week's exemption quota."""
        return ExemptionService.get_or_create_weekly_quota(db, user)
    
    @staticmethod
    def use_day_pass(db: Session, user: User, target_date: date, reason: Optional[str] = None):
        """
        Use a day pass for the specified date.
        
        Day Pass V1 Rules:
        - Sets day_pass_date to the target date
        - On that date, overdue judgment is paused for 24 hours
        - Does NOT automatically change task statuses
        - Does NOT whitewash task history
        """
        quota = ExemptionService.get_or_create_weekly_quota(db, user, target_date)
        
        # Check if day pass is available
        if quota.day_pass_used >= quota.day_pass_total:
            raise HTTPException(
                status_code=400,
                detail=f"本周 Day Pass 已用完 ({quota.day_pass_used}/{quota.day_pass_total})"
            )
        
        # Check if day pass already used for this date
        if quota.day_pass_date == target_date:
            raise HTTPException(
                status_code=400,
                detail=f"Day Pass 已在 {target_date} 使用过"
            )
        
        # Use day pass
        quota.day_pass_used += 1
        quota.day_pass_date = target_date
        
        # Log the usage
        log = ExemptionLog(
            quota_id=quota.id,
            type="day_pass",
            reason=reason
        )
        db.add(log)
        
        db.commit()
        logger.info(f"Day pass used for user {user.id} on {target_date}")
        
        return quota
    
    @staticmethod
    def is_day_pass_active(db: Session, user_id: str, check_date: date) -> bool:
        """
        Check if day pass is active for a specific date.
        
        Used by overdue checking logic to skip penalty on day pass dates.
        """
        # Calculate Monday of the week
        days_since_monday = check_date.weekday()
        week_start = check_date - timedelta(days=days_since_monday)
        
        quota = db.query(ExemptionQuota).filter(
            ExemptionQuota.user_id == user_id,
            ExemptionQuota.week_start == week_start
        ).first()
        
        if not quota:
            return False
        
        return quota.day_pass_date == check_date
    
    @staticmethod
    def use_rule_break(
        db: Session,
        user: User,
        task_id: str,
        reason: Optional[str] = None
    ) -> Task:
        """
        Use a rule break to excuse a task.
        
        Rule Break Rules:
        - Transitions task from OPEN/OVERDUE to EXCUSED
        - Consumes 1 rule break quota
        - Must be logged with task_id
        """
        quota = ExemptionService.get_current_quota(db, user)
        
        # Check if rule break is available
        if quota.rule_break_used >= quota.rule_break_total:
            raise HTTPException(
                status_code=400,
                detail=f"本周 Rule Break 已用完 ({quota.rule_break_used}/{quota.rule_break_total})"
            )
        
        # Get the task
        task = db.query(Task).filter(
            Task.id == task_id,
            Task.user_id == user.id
        ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Only allow rule break for OPEN/OVERDUE tasks
        if task.status not in ["OPEN", "OVERDUE"]:
            raise HTTPException(
                status_code=400,
                detail=f"任务状态 {task.status} 不允许使用 Rule Break"
            )
        
        # Use rule break
        quota.rule_break_used += 1
        task.status = "EXCUSED"
        task.completed_at = datetime.utcnow()
        
        # Log the usage
        log = ExemptionLog(
            quota_id=quota.id,
            type="rule_break",
            task_id=task.id,
            reason=reason
        )
        db.add(log)
        
        db.commit()
        db.refresh(task)
        
        logger.info(f"Rule break used for task {task_id}")
        return task
    
    @staticmethod
    def get_exemption_logs(db: Session, user: User, weeks: int = 4):
        """Get recent exemption logs."""
        # Get logs from recent weeks
        cutoff_date = datetime.utcnow().date() - timedelta(weeks=weeks)
        
        logs = db.query(ExemptionLog).join(ExemptionQuota).filter(
            ExemptionQuota.user_id == user.id,
            ExemptionQuota.week_start >= cutoff_date
        ).order_by(ExemptionLog.used_at.desc()).all()
        
        return logs
