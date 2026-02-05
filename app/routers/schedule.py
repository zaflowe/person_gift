"""Schedule router for time blocking."""
import logging
from datetime import datetime, date, timedelta, time as dt_time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.task import Task
from app.schemas.schedule import (
    DailySchedule,
    WeeklySchedule,
    TimeBlock,
    DueTask,
    ScheduleTaskRequest,
    ScheduleTaskResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/schedule", tags=["schedule"])


@router.get("/today", response_model=DailySchedule)
async def get_today_schedule(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get today's schedule with all time-blocked tasks."""
    today = datetime.now().date()
    
    # Get all tasks scheduled for today
    # Note: Only get tasks where scheduled_time is not None (meaning they have a time block)
    tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.scheduled_time != None
    ).all()
    
    # Filter for today
    today_tasks = [
        task for task in tasks
        if task.scheduled_time and task.scheduled_time.date() == today
    ]
    
    # Convert to TimeBlocks
    time_blocks = []
    for task in today_tasks:
        time_blocks.append(TimeBlock(
            task_id=task.id,
            title=task.title,
            scheduled_time=task.scheduled_time,
            duration=task.duration or 60,
            status=task.status,
            evidence_type=task.evidence_type,
            project_id=task.project_id
        ))
    
    # Sort by time
    time_blocks.sort(key=lambda x: x.scheduled_time)

    # Get tasks due today (deadline is today)
    # Note: deadline is DateTime, compare date part
    # We query all tasks with deadline, then filter for today in code 
    # (SQLite date comparison can be tricky if not stored consistently)
    # Optimization: Filter by range in DB if possible, but python filter is safer for now
    due_today_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.deadline != None,
        Task.status.in_(["OPEN", "EVIDENCE_SUBMITTED"])
    ).all()

    due_tasks = []
    for task in due_today_tasks:
        if task.deadline and task.deadline.date() == today:
            due_tasks.append(DueTask(
                task_id=task.id,
                title=task.title,
                status=task.status,
                deadline=task.deadline,
                # priority=getattr(task, "priority", None), # Task model doesn't have priority yet? 
                # Wait, I removed priority from system_tasks.py because it was missing.
                # So I should handle that.
                project_id=task.project_id
            ))
    
    return DailySchedule(
        date=today,
        time_blocks=time_blocks,
        due_tasks=due_tasks
    )


@router.get("/week", response_model=WeeklySchedule)
async def get_week_schedule(
    start_date: Optional[date] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get 7-day schedule.
    
    If start_date is not provided, starts from today.
    """
    if not start_date:
        start_date = datetime.now().date()
    
    end_date = start_date + timedelta(days=6)
    
    # Get all time-blocked tasks in range
    scheduled_tasks = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.scheduled_time >= datetime.combine(start_date, dt_time.min),
        Task.scheduled_time <= datetime.combine(end_date, dt_time.max)
    ).all()

    # Get all due tasks in range (for right sidebar)
    due_tasks_query = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.deadline >= datetime.combine(start_date, dt_time.min),
        Task.deadline <= datetime.combine(end_date, dt_time.max),
        Task.status.in_(["OPEN", "EVIDENCE_SUBMITTED"]) # Only show open tasks
    ).all()
    
    # Group by date
    daily_schedules = []
    for day_offset in range(7):
        current_date = start_date + timedelta(days=day_offset)
        
        # Filter scheduled tasks for this day
        day_scheduled = [
            task for task in scheduled_tasks
            if task.scheduled_time and task.scheduled_time.date() == current_date
        ]
        
        # Filter due tasks for this day
        day_due = [
            task for task in due_tasks_query
            if task.deadline and task.deadline.date() == current_date
        ]

        # Convert to TimeBlocks
        time_blocks = []
        for task in day_scheduled:
            time_blocks.append(TimeBlock(
                task_id=task.id,
                title=task.title,
                scheduled_time=task.scheduled_time,
                duration=task.duration or 60,
                status=task.status,
                evidence_type=task.evidence_type,
                project_id=task.project_id
            ))
        
        # Sort by time
        time_blocks.sort(key=lambda x: x.scheduled_time)

        # Convert to DueTasks
        current_due_tasks = []
        for task in day_due:
            current_due_tasks.append(DueTask(
                task_id=task.id,
                title=task.title,
                status=task.status,
                deadline=task.deadline,
                project_id=task.project_id
            ))
        
        current_due_tasks.sort(key=lambda x: x.deadline)
        
        daily_schedules.append(DailySchedule(
            date=current_date,
            time_blocks=time_blocks,
            due_tasks=current_due_tasks
        ))
        

    
    return WeeklySchedule(
        start_date=start_date,
        end_date=end_date,
        daily_schedules=daily_schedules
    )


@router.post("/tasks/{task_id}/schedule", response_model=ScheduleTaskResponse)
async def schedule_task(
    task_id: str,
    request: ScheduleTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Schedule a task to a specific time block."""
    # Get task
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Combine date and time
    scheduled_datetime = datetime.combine(request.scheduled_date, request.scheduled_time)
    
    # Update task
    task.scheduled_date = scheduled_datetime
    task.scheduled_time = scheduled_datetime
    task.duration = request.duration
    task.is_time_blocked = True
    
    db.commit()
    
    logger.info(f"Task {task_id} scheduled to {scheduled_datetime}")
    
    return ScheduleTaskResponse(
        task_id=task.id,
        scheduled_time=task.scheduled_time,
        duration=task.duration,
        is_time_blocked=task.is_time_blocked
    )


@router.delete("/tasks/{task_id}/schedule")
async def unschedule_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove time block from a task."""
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.user_id == current_user.id
    ).first()
    
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Clear scheduling
    task.scheduled_date = None
    task.scheduled_time = None
    task.duration = None
    task.is_time_blocked = False
    
    db.commit()
    
    logger.info(f"Task {task_id} unscheduled")
    
    return {"message": "Task unscheduled successfully"}
