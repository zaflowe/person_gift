"""Planner Pydantic schemas."""
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class PlanContext(BaseModel):
    """Context information for planning."""
    timezone: str = "Asia/Shanghai"
    today: str = Field(..., description="Current date in YYYY-MM-DD format")
    active_projects: Optional[List[dict]] = None
    constraints: Optional[dict] = None


class PlanRequest(BaseModel):
    """Request to generate a plan."""
    message: str = Field(..., min_length=1, max_length=2000, description="User's natural language input")
    context: Optional[PlanContext] = None


class PlannedTask(BaseModel):
    """A single planned task."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    due_at: str = Field(..., description="ISO 8601 datetime with timezone")
    evidence_type: str = Field(default="none", pattern="^(none|text|number|image)$")
    tags: Optional[List[str]] = None


class PlannedProject(BaseModel):
    """Planned project information."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None


class PlanResponse(BaseModel):
    """Response containing the generated plan."""
    session_id: str
    plan: dict = Field(..., description="Structured plan with project and tasks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "uuid-here",
                "plan": {
                    "project": {
                        "title": "微积分学习计划",
                        "description": "3个月完成微积分基础"
                    },
                    "tasks": [
                        {
                            "title": "完成极限章节",
                            "description": "阅读教材 + 做练习题50道",
                            "due_at": "2026-02-15T23:59:59+08:00",
                            "evidence_type": "number"
                        }
                    ],
                    "rationale": "分为6个两周周期"
                }
            }
        }


class CommitRequest(BaseModel):
    """Request to commit a plan and create project + tasks."""
    session_id: str
    plan: dict = Field(..., description="The plan data to commit")


class CommitResponse(BaseModel):
    """Response after successfully committing a plan."""
    project_id: str
    task_ids: List[str]
    
    class Config:
        json_schema_extra = {
            "example": {
                "project_id": "proj-uuid",
                "task_ids": ["task1-uuid", "task2-uuid", "task3-uuid"]
            }
        }
