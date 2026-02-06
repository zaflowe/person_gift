"""Project long task template schemas."""
from datetime import datetime
from typing import Optional, Literal, List

from pydantic import BaseModel, Field, field_validator


class ProjectLongTaskTemplateCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    frequency_mode: Literal["interval", "specific_days"] = "interval"
    interval_days: int = Field(1, ge=1, le=3650)
    days_of_week: List[int] = []
    default_due_time: Optional[str] = None
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    evidence_type: Optional[Literal["image", "text", "number", "none"]] = "none"
    evidence_criteria: Optional[str] = None
    total_cycle_days: int = Field(..., ge=1, le=36500)


class ProjectLongTaskTemplateUpdate(BaseModel):
    title: Optional[str] = None
    frequency_mode: Optional[Literal["interval", "specific_days"]] = None
    interval_days: Optional[int] = Field(None, ge=1, le=3650)
    days_of_week: Optional[List[int]] = None
    default_due_time: Optional[str] = None
    default_start_time: Optional[str] = None
    default_end_time: Optional[str] = None
    evidence_type: Optional[Literal["image", "text", "number", "none"]] = None
    evidence_criteria: Optional[str] = None
    total_cycle_days: Optional[int] = Field(None, ge=1, le=36500)


class ProjectLongTaskTemplateResponse(BaseModel):
    id: str
    user_id: str
    project_id: str
    title: str
    frequency_mode: str
    interval_days: Optional[int]
    days_of_week: List[int] = []
    default_due_time: Optional[str]
    default_start_time: Optional[str]
    default_end_time: Optional[str]
    evidence_type: Optional[str]
    evidence_criteria: Optional[str]
    total_cycle_days: int
    started_at: datetime
    is_hidden: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("days_of_week", mode="before")
    @classmethod
    def parse_days_of_week(cls, v):
        if isinstance(v, str):
            try:
                import json
                return json.loads(v)
            except Exception:
                return []
        return v
