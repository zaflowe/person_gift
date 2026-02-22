"""Service for project long task templates and daily generation logic."""
import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.project_long_task import ProjectLongTaskTemplate
from app.models.project import Project
from app.models.task import Task

logger = logging.getLogger(__name__)


class ProjectLongTaskService:
    """Service for project long task generation."""

    def get_templates(
        self,
        db: Session,
        user_id: str,
        project_id: str,
        include_hidden: bool = False,
    ) -> List[ProjectLongTaskTemplate]:
        query = db.query(ProjectLongTaskTemplate).filter(
            ProjectLongTaskTemplate.user_id == user_id,
            ProjectLongTaskTemplate.project_id == project_id,
        )
        if not include_hidden:
            query = query.filter(ProjectLongTaskTemplate.is_hidden == False)
        return query.order_by(ProjectLongTaskTemplate.created_at.desc()).all()

    def create_template(
        self,
        db: Session,
        user_id: str,
        project_id: str,
        data: dict,
    ) -> ProjectLongTaskTemplate:
        template = ProjectLongTaskTemplate(
            user_id=user_id,
            project_id=project_id,
            title=data["title"],
            frequency_mode=data.get("frequency_mode", "interval"),
            interval_days=data.get("interval_days", 1),
            days_of_week=json.dumps(data.get("days_of_week", [])),
            default_due_time=data.get("default_due_time"),
            default_start_time=data.get("default_start_time"),
            default_end_time=data.get("default_end_time"),
            evidence_type=data.get("evidence_type", "none"),
            evidence_criteria=data.get("evidence_criteria"),
            total_cycle_days=data["total_cycle_days"],
            started_at=datetime.utcnow(),
            is_hidden=False,
        )
        db.add(template)
        db.commit()
        db.refresh(template)

        # Attempt to generate today's task only when project is ACTIVE
        project = db.query(Project).filter(Project.id == project_id).first()
        if project and project.status == "ACTIVE":
            self.maybe_generate_today(db, template)
        return template

    def update_template(
        self,
        db: Session,
        user_id: str,
        project_id: str,
        template_id: str,
        updates: dict,
    ) -> Optional[ProjectLongTaskTemplate]:
        template = db.query(ProjectLongTaskTemplate).filter(
            ProjectLongTaskTemplate.id == template_id,
            ProjectLongTaskTemplate.user_id == user_id,
            ProjectLongTaskTemplate.project_id == project_id,
        ).first()
        if not template:
            return None

        for key, value in updates.items():
            if key == "days_of_week" and isinstance(value, list):
                setattr(template, key, json.dumps(value))
            else:
                setattr(template, key, value)

        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template

    def hide_template(
        self,
        db: Session,
        user_id: str,
        project_id: str,
        template_id: str,
    ) -> Optional[ProjectLongTaskTemplate]:
        template = db.query(ProjectLongTaskTemplate).filter(
            ProjectLongTaskTemplate.id == template_id,
            ProjectLongTaskTemplate.user_id == user_id,
            ProjectLongTaskTemplate.project_id == project_id,
        ).first()
        if not template:
            return None
        template.is_hidden = True
        template.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(template)
        return template

    def process_daily_long_tasks(self, db: Session, today: datetime = None) -> int:
        if today is None:
            today = datetime.now()

        # Defensive cleanup for historical duplicates before daily generation.
        self.cleanup_duplicate_generated_tasks(db)

        templates = db.query(ProjectLongTaskTemplate).join(
            Project, Project.id == ProjectLongTaskTemplate.project_id
        ).filter(Project.status == "ACTIVE").all()
        created_count = 0

        for template in templates:
            if not self._within_cycle(template, today):
                continue
            created_count += self._safe_create_for_date(db, template, today)

        return created_count

    def maybe_generate_today(self, db: Session, template: ProjectLongTaskTemplate) -> int:
        project = db.query(Project).filter(Project.id == template.project_id).first()
        if not project or project.status != "ACTIVE":
            return 0
        today = datetime.now()
        if not self._within_cycle(template, today):
            return 0
        return self._safe_create_for_date(db, template, today)

    def cleanup_duplicate_generated_tasks(self, db: Session, template_id: Optional[str] = None) -> int:
        """
        Keep only one task per (long_task_template_id, generated_for_date).
        Prefer earliest created task to keep history stable.
        """
        query = db.query(Task).filter(
            Task.long_task_template_id.isnot(None),
            Task.generated_for_date.isnot(None),
        ).order_by(Task.long_task_template_id.asc(), Task.generated_for_date.asc(), Task.created_at.asc(), Task.id.asc())

        if template_id:
            query = query.filter(Task.long_task_template_id == template_id)

        tasks = query.all()
        seen = set()
        to_delete = []
        for task in tasks:
            key = (task.long_task_template_id, task.generated_for_date)
            if key in seen:
                to_delete.append(task)
            else:
                seen.add(key)

        if not to_delete:
            return 0

        for task in to_delete:
            db.delete(task)
        db.commit()
        logger.warning("Deduplicated %s duplicate long-task generated tasks", len(to_delete))
        return len(to_delete)

    def _within_cycle(self, template: ProjectLongTaskTemplate, today: datetime) -> bool:
        if not template.started_at:
            return True
        days_elapsed = (today.date() - template.started_at.date()).days
        return days_elapsed < template.total_cycle_days

    def _should_create_for_date(self, db: Session, template: ProjectLongTaskTemplate, today: datetime) -> bool:
        should_create = False

        if template.frequency_mode == "specific_days":
            target_days = json.loads(template.days_of_week) if template.days_of_week else []
            if today.weekday() in target_days:
                should_create = True
        else:
            if template.interval_days <= 1:
                should_create = True
            else:
                last_task = db.query(Task).filter(
                    Task.long_task_template_id == template.id
                ).order_by(Task.generated_for_date.desc()).first()

                if not last_task or not last_task.generated_for_date:
                    should_create = True
                else:
                    days_diff = (today.date() - last_task.generated_for_date.date()).days
                    if days_diff >= template.interval_days:
                        should_create = True

        if not should_create:
            return False

        start_of_day = datetime(today.year, today.month, today.day)
        existing = db.query(Task).filter(
            Task.long_task_template_id == template.id,
            Task.generated_for_date == start_of_day,
        ).first()
        return existing is None

    def _safe_create_for_date(self, db: Session, template: ProjectLongTaskTemplate, today: datetime) -> int:
        # Clean historical duplicates for this template first.
        self.cleanup_duplicate_generated_tasks(db, template_id=template.id)

        if not self._should_create_for_date(db, template, today):
            return 0

        try:
            created = self._create_task_for_date(db, template, today)
            if created:
                db.commit()
                # Final guard in case concurrent writers slipped in before commit.
                self.cleanup_duplicate_generated_tasks(db, template_id=template.id)
            return created
        except IntegrityError:
            db.rollback()
            logger.info(
                "Skipped duplicate long task generation for template=%s date=%s due to integrity constraint",
                template.id,
                today.date().isoformat(),
            )
            # Make sure duplicates are collapsed to one if a race happened.
            self.cleanup_duplicate_generated_tasks(db, template_id=template.id)
            return 0

    def _create_task_for_date(self, db: Session, template: ProjectLongTaskTemplate, today: datetime) -> int:
        start_of_day = datetime(today.year, today.month, today.day)

        scheduled_time = None
        deadline = None

        if template.default_start_time:
            try:
                h, m = map(int, template.default_start_time.split(":"))
                scheduled_time = today.replace(hour=h, minute=m, second=0, microsecond=0)
            except Exception:
                pass

        end_str = template.default_end_time or template.default_due_time
        if end_str:
            try:
                h, m = map(int, end_str.split(":"))
                deadline = today.replace(hour=h, minute=m, second=0, microsecond=0)
            except Exception:
                deadline = today.replace(hour=23, minute=59, second=59)
        else:
            deadline = today.replace(hour=23, minute=59, second=59)

        duration = None
        if scheduled_time and deadline:
            diff = (deadline - scheduled_time).total_seconds() / 60
            if diff > 0:
                duration = int(diff)

        new_task = Task(
            user_id=template.user_id,
            project_id=template.project_id,
            title=template.title,
            status="OPEN",
            deadline=deadline,
            scheduled_time=scheduled_time,
            scheduled_date=scheduled_time if scheduled_time else None,
            duration=duration,
            is_time_blocked=bool(scheduled_time),
            evidence_type=template.evidence_type,
            evidence_criteria=template.evidence_criteria,
            long_task_template_id=template.id,
            generated_for_date=start_of_day,
            tags=json.dumps(["长期任务"], ensure_ascii=False),
        )
        db.add(new_task)
        return 1


project_long_task_service = ProjectLongTaskService()
