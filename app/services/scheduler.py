"""Scheduler for recurring tasks and background jobs."""
import logging
import os
import uuid
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.exemption import JobLock
from app.models.task import PlanTemplate, Task
from app.services.task_service import TaskService
from app.services.reminder_service import process_all_daily_reminders

logger = logging.getLogger(__name__)

# Scheduler instance
scheduler = BackgroundScheduler()


def acquire_job_lock(db: Session, job_name: str, lock_duration_minutes: int = 10) -> bool:
    """
    Try to acquire a distributed lock for a job.
    
    Returns True if lock acquired, False otherwise.
    """
    now = datetime.utcnow()
    lock_until = now + timedelta(minutes=lock_duration_minutes)
    lock_by = f"{os.getenv('HOSTNAME', 'unknown')}_{os.getpid()}"
    
    # Try to get existing lock
    existing_lock = db.query(JobLock).filter(JobLock.job_name == job_name).first()
    
    if existing_lock:
        # Check if lock is still valid
        if existing_lock.locked_until > now:
            logger.info(f"Job {job_name} is locked by {existing_lock.locked_by} until {existing_lock.locked_until}")
            return False
        else:
            # Lock expired, update it
            existing_lock.locked_until = lock_until
            existing_lock.locked_by = lock_by
            existing_lock.locked_at = now
    else:
        # Create new lock
        new_lock = JobLock(
            job_name=job_name,
            locked_until=lock_until,
            locked_by=lock_by,
            locked_at=now
        )
        db.add(new_lock)
    
    db.commit()
    logger.info(f"Acquired lock for job {job_name}")
    return True


def generate_weekly_tasks():
    """
    Generate weekly tasks from plan templates.
    
    Runs every Monday at 00:05 Asia/Taipei.
    Uses distributed lock to prevent duplicate generation.
    """
    db = SessionLocal()
    try:
        # Try to acquire lock
        if not acquire_job_lock(db, "weekly_task_generation"):
            logger.info("Skipping weekly task generation - already running")
            return
        
        logger.info("Starting weekly task generation")
        
        # Get timezone
        tz = ZoneInfo(settings.timezone)
        now = datetime.now(tz)
        
        # Get all active weekly templates
        templates = db.query(PlanTemplate).filter(
            PlanTemplate.is_active == True,
            PlanTemplate.frequency == "weekly"
        ).all()
        
        tasks_created = 0
        
        # Calculate week start (Monday)
        days_since_monday = now.weekday()
        week_start = now - timedelta(days=days_since_monday)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        # Convert to UTC for DB query if needed, but SQLite stores naive usually? 
        # Models use datetime.utcnow for defaults. Let's ensure we compare correctly.
        # Simplest: Check task created after "Today 00:00" if running on Mon, or "Last 24h"
        # Ideally: Check if any task with this template_id was created "This Week".
        
        week_start_utc = week_start.astimezone(ZoneInfo("UTC")).replace(tzinfo=None)

        for template in templates:
            # CHECK FOR DUPLICATES
            # If any task was created from this template since the start of this week, skip.
            # This logic assumes the job runs ONCE per week.
            existing = db.query(Task).filter(
                Task.plan_template_id == template.id,
                Task.created_at >= week_start_utc
            ).first()
            
            if existing:
                logger.info(f"Skipping template {template.id} ({template.title}): Tasks already generated for this week.")
                continue

            # Generate N tasks for this week
            times_to_generate = template.times_per_week or 1
            
            for i in range(times_to_generate):
                # Calculate deadline
                deadline_hour = template.default_deadline_hour
                deadline_time = time(hour=deadline_hour, minute=59, second=59)
                
                # Deadline is today + deadline_hour
                deadline_date = now.date()
                deadline_datetime = datetime.combine(deadline_date, deadline_time)
                deadline_datetime = deadline_datetime.replace(tzinfo=tz)
                
                # Formatting title to include Weekly ID e.g. (W2026-06)
                week_num = now.isocalendar()[1]
                year_num = now.year
                week_id = f"W{year_num}-{week_num:02d}"
                
                # Check duplication by Title as well just in case
                task_title = f"{template.title} ({week_id})"
                if times_to_generate > 1:
                    task_title = f"{template.title} {i+1}/{times_to_generate} ({week_id})"
                
                # Create task
                task = Task(
                    user_id=template.user_id,
                    title=task_title,
                    description=template.description,
                    evidence_type=template.evidence_type,
                    evidence_criteria=template.evidence_criteria,
                    deadline=deadline_datetime.astimezone(ZoneInfo("UTC")).replace(tzinfo=None),
                    plan_template_id=template.id,
                    status="OPEN"
                )
                db.add(task)
                tasks_created += 1
        
        db.commit()
        logger.info(f"Weekly task generation completed: {tasks_created} tasks created")
        
    except Exception as e:
        logger.error(f"Error in weekly task generation: {e}")
        db.rollback()
    finally:
        db.close()


def update_overdue_tasks():
    """
    Update tasks that are past their deadline to OVERDUE status.
    
    Runs every hour.
    Respects day pass exemptions.
    """
    db = SessionLocal()
    try:
        TaskService.update_overdue_tasks(db)
    except Exception as e:
        logger.error(f"Error updating overdue tasks: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start the background scheduler."""
    # Weekly task generation: Monday 00:05 Asia/Taipei
    scheduler.add_job(
        generate_weekly_tasks,
        trigger=CronTrigger(
            day_of_week='mon',
            hour=0,
            minute=5,
            timezone=settings.timezone
        ),
        id='generate_weekly_tasks',
        name='Generate weekly tasks',
        replace_existing=True
    )
    
    # Overdue task update: Every hour
    scheduler.add_job(
        update_overdue_tasks,
        trigger=CronTrigger(
            minute=0,  # Run at the top of every hour
            timezone=settings.timezone
        ),
        id='update_overdue_tasks',
        name='Update overdue tasks',
        replace_existing=True
    )
    
    # Daily Reminder: Every day at 09:00
    scheduler.add_job(
        process_all_daily_reminders,
        trigger=CronTrigger(
            hour=9,
            minute=0,
            timezone=settings.timezone
        ),
        id='daily_reminder',
        name='Daily Reminder',
        replace_existing=True
    )
    
    scheduler.start()

    logger.info("Scheduler started")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")
