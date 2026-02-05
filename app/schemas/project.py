"""Project schemas."""
from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a project."""
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1)
    success_criteria: Optional[str] = None
    failure_criteria: Optional[str] = None
    color: Optional[str] = None  # Add color


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""
    title: Optional[str] = None
    description: Optional[str] = None
    success_criteria: Optional[str] = None
    failure_criteria: Optional[str] = None
    is_strategic: Optional[bool] = None
    schedule_policy: Optional[str] = None  # LOCKED / FLEX_ONCE
    color: Optional[str] = None  # Add color


class ProjectResponse(BaseModel):
    """Schema for project response."""
    id: str
    user_id: str
    title: str
    description: str
    status: str
    success_criteria: Optional[str]
    failure_criteria: Optional[str]
    ai_analysis: Optional[str]
    user_confirmed_at: Optional[datetime]
    ai_confirmed_at: Optional[datetime]
    agreement_hash: Optional[str]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    is_strategic: bool = False
    schedule_policy: str = "LOCKED"
    next_milestone: Optional[str] = None
    color: Optional[str] = None  # Add color
    
    class Config:
        from_attributes = True



class MilestoneCreate(BaseModel):
    """Schema for creating a milestone."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    is_critical: bool = False
    target_date: Optional[date] = None


class MilestoneUpdate(BaseModel):
    """Schema for updating a milestone."""
    title: Optional[str] = None
    description: Optional[str] = None
    is_critical: Optional[bool] = None
    target_date: Optional[date] = None



class MilestoneResponse(BaseModel):
    """Schema for milestone response."""
    id: str
    project_id: str
    title: str
    description: Optional[str]
    is_critical: bool
    status: str
    target_date: Optional[date]
    achieved_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectWithMilestones(ProjectResponse):
    """Schema for project with milestones."""
    milestones: List[MilestoneResponse] = []
