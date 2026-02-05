"""Exemptions router."""
from typing import List
from datetime import date

from fastapi import APIRouter, Depends, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.exemption import (
    ExemptionQuotaResponse,
    UseDayPass,
    UseRuleBreak,
    ExemptionLogResponse,
)
from app.schemas.task import TaskResponse
from app.services.exemption_service import ExemptionService

router = APIRouter(prefix="/exemptions", tags=["exemptions"])


@router.get("/quota", response_model=ExemptionQuotaResponse)
def get_current_quota(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current week's exemption quota."""
    quota = ExemptionService.get_current_quota(db, current_user)
    return quota


@router.post("/use-day-pass", response_model=ExemptionQuotaResponse)
def use_day_pass(
    data: UseDayPass,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use a Day Pass for a specific date.
    
    Day Pass Rules (V1):
    - Sets day_pass_date to the target date
    - On that date, overdue judgment is paused for 24 hours
    - Does NOT automatically change task statuses
    - Does NOT whitewash task history
    """
    quota = ExemptionService.use_day_pass(db, current_user, data.date, data.reason)
    return quota


@router.post("/use-rule-break", response_model=TaskResponse)
def use_rule_break(
    data: UseRuleBreak,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use a Rule Break to excuse a task.
    
    Rule Break Rules:
    - Transitions task from OPEN/OVERDUE to EXCUSED
    - Consumes 1 rule break quota
    - Must be logged with task_id
    """
    task = ExemptionService.use_rule_break(
        db, current_user, data.task_id, data.reason
    )
    return task


@router.get("/logs", response_model=List[ExemptionLogResponse])
def get_exemption_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get recent exemption logs (last 4 weeks)."""
    logs = ExemptionService.get_exemption_logs(db, current_user)
    return logs
