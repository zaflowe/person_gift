"""Service for managing habit templates and daily generation logic."""
import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.habit import HabitTemplate
from app.models.task import Task
from app.models.user import User
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class HabitService:
    """Service for habit generation."""

    def get_habits(self, db: Session, user_id: str) -> List[HabitTemplate]:
        return db.query(HabitTemplate).filter(HabitTemplate.user_id == user_id).all()

    def create_habit(self, db: Session, habit_data: dict, user_id: str) -> HabitTemplate:
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
            evidence_criteria=habit_data.get("evidence_criteria"),
        )
        db.add(habit)
        db.commit()
        db.refresh(habit)
        return habit

    def update_habit(self, db: Session, habit_id: str, updates: dict, user_id: str) -> Optional[HabitTemplate]:
        habit = db.query(HabitTemplate).filter(
            HabitTemplate.id == habit_id,
            HabitTemplate.user_id == user_id,
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
        habit = db.query(HabitTemplate).filter(
            HabitTemplate.id == habit_id,
            HabitTemplate.user_id == user_id,
        ).first()
        if not habit:
            return False

        db.delete(habit)
        db.commit()
        return True

    def cleanup_duplicate_generated_tasks(self, db: Session, user_id: Optional[str] = None) -> int:
        """Keep only one habit-generated task per (template_id, generated_for_date)."""
        query = db.query(Task).filter(
            Task.template_id.isnot(None),
            Task.generated_for_date.isnot(None),
        ).order_by(Task.template_id.asc(), Task.generated_for_date.asc(), Task.created_at.asc(), Task.id.asc())
        if user_id:
            query = query.filter(Task.user_id == user_id)

        seen = set()
        to_delete: list[Task] = []
        for task in query.all():
            key = (task.template_id, task.generated_for_date)
            if key in seen:
                to_delete.append(task)
            else:
                seen.add(key)

        if not to_delete:
            return 0

        for task in to_delete:
            from app.models.study import StudySession
            from app.models.metric import MetricEntry
            
            db.query(StudySession).filter(StudySession.task_id == task.id).update(
                {"task_id": None}, synchronize_session=False
            )
            db.query(StudySession).filter(StudySession.quick_start_task_id == task.id).update(
                {"quick_start_task_id": None}, synchronize_session=False
            )
            db.query(MetricEntry).filter(MetricEntry.task_id == task.id).update(
                {"task_id": None}, synchronize_session=False
            )
            db.delete(task)
        db.commit()
        logger.warning("Deduplicated %s duplicate habit-generated tasks", len(to_delete))
        return len(to_delete)

    def process_daily_habits(self, db: Session, user_id: str, today: datetime = None) -> int:
        """
        Check and generate daily habits for user.
        Returns number of tasks created.
        """
        if today is None:
            today = datetime.now()

        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0

        # Cleanup unfinished recurring instances from previous days and historical duplicates.
        TaskService.cleanup_stale_recurring_instances(db, user_id=user_id, now=today)
        self.cleanup_duplicate_generated_tasks(db, user_id=user_id)

        today_date = today.date()
        habits = db.query(HabitTemplate).filter(
            HabitTemplate.user_id == user_id,
            HabitTemplate.enabled == True,
        ).all()

        created_count = 0
        for habit in habits:
            should_create = False

            if habit.frequency_mode == "specific_days":
                target_days = json.loads(habit.days_of_week) if habit.days_of_week else []
                should_create = today.weekday() in target_days
            elif habit.frequency_mode == "interval":
                if habit.interval_days <= 1:
                    should_create = True
                else:
                    last_task = db.query(Task).filter(
                        Task.template_id == habit.id
                    ).order_by(Task.generated_for_date.desc()).first()
                    if not last_task or not last_task.generated_for_date:
                        should_create = True
                    else:
                        days_diff = (today_date - last_task.generated_for_date.date()).days
                        should_create = days_diff >= habit.interval_days

            if not should_create:
                continue

            created_count += self._safe_create_for_date(db, habit, user_id, today)

        user.last_habit_generation_date = datetime.utcnow()
        db.commit()
        return created_count

    def _safe_create_for_date(self, db: Session, habit: HabitTemplate, user_id: str, today: datetime) -> int:
        start_of_day = datetime(today.year, today.month, today.day)

        existing = db.query(Task).filter(
            Task.template_id == habit.id,
            Task.generated_for_date == start_of_day,
        ).first()
        if existing:
            return 0

        try:
            self._create_task_for_date(db, habit, user_id, today, start_of_day)
            db.commit()
            return 1
        except IntegrityError:
            db.rollback()
            logger.info(
                "Skipped duplicate habit generation for template=%s date=%s due to integrity constraint",
                habit.id,
                today.date().isoformat(),
            )
            self.cleanup_duplicate_generated_tasks(db, user_id=user_id)
            return 0

    def _create_task_for_date(
        self,
        db: Session,
        habit: HabitTemplate,
        user_id: str,
        today: datetime,
        start_of_day: datetime,
    ) -> None:
        scheduled_time = None
        deadline = None

        if habit.default_start_time:
            try:
                h, m = map(int, habit.default_start_time.split(":"))
                scheduled_time = today.replace(hour=h, minute=m, second=0, microsecond=0)
            except Exception:
                scheduled_time = None

        end_str = habit.default_end_time or habit.default_due_time
        if end_str:
            try:
                h, m = map(int, end_str.split(":"))
                deadline = today.replace(hour=h, minute=m, second=0, microsecond=0)
            except Exception:
                deadline = None

        scheduled_time, deadline = TaskService._normalize_task_window(scheduled_time, deadline, now=today)
        duration = max(int((deadline - scheduled_time).total_seconds() // 60), 1)

        db.add(Task(
            user_id=user_id,
            title=habit.title,
            status="OPEN",
            deadline=deadline,
            scheduled_time=scheduled_time,
            scheduled_date=scheduled_time,
            duration=duration,
            is_time_blocked=True,
            evidence_type=habit.evidence_type,
            evidence_criteria=habit.evidence_criteria,
            template_id=habit.id,
            generated_for_date=start_of_day,
            tags=json.dumps(["习惯"], ensure_ascii=False),
        ))


habit_service = HabitService()
