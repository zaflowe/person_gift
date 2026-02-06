"""Service for managing habit templates and daily generation logic."""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.habit import HabitTemplate
from app.models.task import Task
from app.models.user import User

logger = logging.getLogger(__name__)


class HabitService:
    """Service for habit generation."""

    def get_habits(self, db: Session, user_id: str) -> List[HabitTemplate]:
        """Get all habit templates for a user."""
        return db.query(HabitTemplate).filter(HabitTemplate.user_id == user_id).all()

    def create_habit(self, db: Session, habit_data: dict, user_id: str) -> HabitTemplate:
        """Create a new habit template."""
        habit = HabitTemplate(
            user_id=user_id,
            title=habit_data["title"],
            enabled=habit_data.get("enabled", True),
            frequency_mode=habit_data.get("frequency_mode", "interval"),
            interval_days=habit_data.get("interval_days", 1),
            days_of_week=json.dumps(habit_data.get("days_of_week", [])),
            default_due_time=habit_data.get("default_due_time"),
            default_start_time=habit_data.get("default_start_time"),
            default_end_time=habit_data.get("default_end_time"),
            evidence_type=habit_data.get("evidence_type", "none"),
            evidence_schema=habit_data.get("evidence_schema"),
            evidence_criteria=habit_data.get("evidence_criteria")
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit
        
    def update_habit(self, db: Session, habit_id: str, updates: dict, user_id: str) -> Optional[HabitTemplate]:
        """Update a habit template."""
        habit = db.query(HabitTemplate).filter(
            HabitTemplate.id == habit_id, 
            HabitTemplate.user_id == user_id
        ).first()
        
        if not habit:
            return None
            
        for key, value in updates.items():
            if key == "days_of_week" and isinstance(value, list):
                setattr(habit, key, json.dumps(value))
            else:
                setattr(habit, key, value)
                
        habit.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(habit)
        return habit
        
    def delete_habit(self, db: Session, habit_id: str, user_id: str) -> bool:
        """Delete a habit template."""
        habit = db.query(HabitTemplate).filter(
            HabitTemplate.id == habit_id, 
            HabitTemplate.user_id == user_id
        ).first()
        
        if not habit:
            return False
            
        db.delete(habit)
        db.commit()
        return True

    def process_daily_habits(self, db: Session, user_id: str, today: datetime = None) -> int:
        """
        Check and generate daily habits for user.
        Returns number of tasks created.
        """
        if today is None:
            today = datetime.now()
            
        today_date = today.date()
        date_str = today.strftime("%Y-%m-%d")
        
        # 1. Update User's check date first (to avoid spam if we want strict once-per-tick, 
        # but here we rely on task uniqueness per template+date, so multiple calls are safe)
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0
            
        # Optional: Skip if already checked today? 
        # User requested: "If last_habit_generation_date != today -> execute"
        # We can adhere to that, OR we can just run the logic safely (idempotent).
        # Running safely allows adding new habits midday and taking effect.
        # But let's stick to the prompt's request for "Daily Login Trigger".
        # We will update the date AT THE END.
        
        # 2. Get active habits
        habits = db.query(HabitTemplate).filter(
            HabitTemplate.user_id == user_id,
            HabitTemplate.enabled == True
        ).all()
        
        created_count = 0
        
        for habit in habits:
            should_create = False
            
            # Logic: Interval vs Specific Days
            if habit.frequency_mode == "specific_days":
                # Check weekday (Monday=0, Sunday=6)
                target_days = json.loads(habit.days_of_week) if habit.days_of_week else []
                if today.weekday() in target_days:
                    should_create = True
            
            elif habit.frequency_mode == "interval":
                # Check interval
                # If interval=1 (Daily), always true
                if habit.interval_days <= 1:
                    should_create = True
                else:
                    # Check the LAST generated task for this template
                    last_task = db.query(Task).filter(
                        Task.template_id == habit.id
                    ).order_by(Task.generated_for_date.desc()).first()
                    
                    if not last_task:
                        should_create = True
                    else:
                        if last_task.generated_for_date:
                            days_diff = (today_date - last_task.generated_for_date.date()).days
                            if days_diff >= habit.interval_days:
                                should_create = True
                        else:
                            # Fallback if legacy somehow
                            should_create = True
            
            if should_create:
                # 3. Uniqueness Check (Idempotency)
                # Check if task already exists for this template AND this date
                # We need to query purely based on template_id and generated_for_date
                # We assume generated_for_date stores date part or start of day
                start_of_day = datetime(today.year, today.month, today.day)
                
                existing = db.query(Task).filter(
                    Task.template_id == habit.id,
                    Task.generated_for_date == start_of_day
                ).first()
                
                if not existing:
                    # Create Task
                    # Calculate Deadline
                    # Calculate Times
                    scheduled_time = None
                    deadline = None
                    
                    # 1. Start Time
                    if habit.default_start_time:
                        try:
                            h, m = map(int, habit.default_start_time.split(":"))
                            scheduled_time = today.replace(hour=h, minute=m, second=0, microsecond=0)
                        except:
                            pass
                            
                    # 2. End Time (Deadline)
                    # Priority: default_end_time > default_due_time
                    end_str = habit.default_end_time or habit.default_due_time
                    if end_str:
                         try:
                            h, m = map(int, end_str.split(":"))
                            deadline = today.replace(hour=h, minute=m, second=0, microsecond=0)
                         except:
                            deadline = today.replace(hour=23, minute=59)
                    else:
                        deadline = today.replace(hour=23, minute=59, second=59)

                    # Calculate duration if both exist
                    duration = None
                    if scheduled_time and deadline:
                        diff = (deadline - scheduled_time).total_seconds() / 60
                        if diff > 0:
                            duration = int(diff)

                    new_task = Task(
                        user_id=user_id,
                        title=habit.title,
                        status="OPEN",
                        deadline=deadline,
                        scheduled_time=scheduled_time,
                        duration=duration,
                        is_time_blocked=bool(scheduled_time),
                        evidence_type=habit.evidence_type,
                        evidence_criteria=habit.evidence_criteria,
                        template_id=habit.id,
                        generated_for_date=start_of_day,
                        tags=json.dumps(["习惯"]) # Tag as Habit
                    )
                    db.add(new_task)
                    created_count += 1

        # 4. Update User's last check time
        user.last_habit_generation_date = datetime.utcnow()
        db.commit()
        
        return created_count

habit_service = HabitService()
