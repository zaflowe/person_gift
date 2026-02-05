"""Schedule schemas for time blocking."""
from typing import List, Optional
from datetime import datetime, date, time
from pydantic import BaseModel


class TimeBlock(BaseModel):
    """A time block for a task."""
    task_id: str
    title: str
    scheduled_time: datetime
    duration: int  # minutes
    status: str
    evidence_type: Optional[str] = None
    project_id: Optional[str] = None


class DueTask(BaseModel):
    """Task due on a specific date (deadline)."""
    task_id: str
    title: str
    status: str
    deadline: datetime
    priority: Optional[str] = None
    project_id: Optional[str] = None


class DailySchedule(BaseModel):
    """Daily schedule with time blocks and due tasks."""
    date: date
    time_blocks: List[TimeBlock]
    due_tasks: List[DueTask] = []
    
    class Config:
        json_schema_extra = {
            "example": {
                "date": "2026-02-02",
                "time_blocks": [
                    {
                        "task_id": "task-uuid",
                        "title": "起床",
                        "scheduled_time": "2026-02-02T07:00:00",
                        "duration": 30,
                        "status": "OPEN",
                        "evidence_type": "none"
                    }
                ]
            }
        }


class WeeklySchedule(BaseModel):
    """Weekly schedule with daily schedules."""
    start_date: date
    end_date: date
    daily_schedules: List[DailySchedule]


class ScheduleTaskRequest(BaseModel):
    """Request to schedule a task."""
    scheduled_date: date
    scheduled_time: time
    duration: int  # minutes


class ScheduleTaskResponse(BaseModel):
    """Response after scheduling a task."""
    task_id: str
    scheduled_time: datetime
    duration: int
    is_time_blocked: bool
