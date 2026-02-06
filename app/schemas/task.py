"""Task schemas."""
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, field_validator


class TaskCreate(BaseModel):
    """Schema for creating a task."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    evidence_type: Optional[Literal["image", "text", "number", "none"]] = "none"
    evidence_criteria: Optional[str] = None
    deadline: Optional[datetime] = None
    project_id: Optional[str] = None
    tags: Optional[list[str]] = []
    
    # Time blocking fields for creation
    scheduled_time: Optional[datetime] = None
    duration: Optional[int] = 60  # Default 60 mins if scheduled



class TaskResponse(BaseModel):
    """Schema for task response."""
    id: str
    user_id: str
    title: str
    description: Optional[str]
    status: str
    evidence_type: Optional[str]
    evidence_criteria: Optional[str]
    deadline: Optional[datetime]
    tags: Optional[list[str]] = []
    project_id: Optional[str]
    plan_template_id: Optional[str]
    long_task_template_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]
    
    # Time blocking fields
    scheduled_date: Optional[datetime] = None
    scheduled_time: Optional[datetime] = None
    duration: Optional[int] = None
    is_time_blocked: bool = False
    
    class Config:
        from_attributes = True

    @field_validator('tags', mode='before')
    @classmethod
    def parse_tags(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except:
                return []
        return v



class TaskEvidenceSubmit(BaseModel):
    """Schema for submitting evidence."""
    evidence_type: Literal["image", "text", "number"]
    content: Optional[str] = None  # For text/number
    # image will be handled via file upload


class TaskEvidenceResponse(BaseModel):
    """Schema for evidence response."""
    id: str
    task_id: str
    evidence_type: str
    content: Optional[str]
    image_path: Optional[str]
    ai_result: Optional[str]
    ai_reason: Optional[str]
    extracted_values: Optional[str]
    submitted_at: datetime
    
    class Config:
        from_attributes = True


class PlanTemplateCreate(BaseModel):
    """Schema for creating a plan template."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    frequency: Literal["daily", "weekly"]
    times_per_week: Optional[int] = Field(None, ge=1, le=7)
    evidence_type: Optional[Literal["image", "text", "number", "none"]] = "none"
    evidence_criteria: Optional[str] = None
    default_deadline_hour: int = Field(23, ge=0, le=23)


class PlanTemplateResponse(BaseModel):
    """Schema for plan template response."""
    id: str
    user_id: str
    title: str
    description: Optional[str]
    frequency: str
    times_per_week: Optional[int]
    evidence_type: Optional[str]
    evidence_criteria: Optional[str]
    default_deadline_hour: int
    timezone: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
