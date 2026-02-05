"""Metric and Dashboard service."""
import json
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.models.metric import MetricEntry, WeeklySnapshot
from app.models.task import Task
from app.models.user import User
from app.schemas.metric import MetricEntryCreate
from app.services.ai_service import ai_service
from app.services.task_service import TaskService

logger = logging.getLogger(__name__)


class MetricService:
    """Metric business logic service."""
    
    @staticmethod
    async def create_metric_entry(
        db: Session,
        user: User,
        data: MetricEntryCreate,
        image_file: Optional[UploadFile] = None
    ) -> MetricEntry:
        """
        Create a raw metric entry.
        
        If metric_type is 'bodyfat' and image is provided,
        use AI to estimate value and override data.value.
        """
        value = data.value
        notes = data.notes
        
        # Handle bodyfat AI estimation
        if data.metric_type == "bodyfat" and image_file:
            import os
            import uuid
            
            # Save image
            upload_dir = "uploads"
            os.makedirs(upload_dir, exist_ok=True)
            file_extension = image_file.filename.split(".")[-1]
            image_filename = f"bodyfat_{uuid.uuid4()}.{file_extension}"
            image_path = os.path.join(upload_dir, image_filename)
            
            with open(image_path, "wb") as f:
                content = await image_file.read()
                f.write(content)
            
            # Call AI
            ai_result = await ai_service.estimate_bodyfat(image_path, user.username)
            
            if "estimated_bodyfat" in ai_result:
                value = float(ai_result["estimated_bodyfat"])
                notes = (notes or "") + f"\nAI Analysis: {ai_result.get('analysis', '')}"
                logger.info(f"AI estimated bodyfat: {value}%")
        
        entry = MetricEntry(
            user_id=user.id,
            metric_type=data.metric_type,
            value=value,
            unit=data.unit,
            task_id=data.task_id,
            notes=notes
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
    
    @staticmethod
    def calc_dashboard_stats(db: Session, user: User, weeks: int = 12) -> List[Any]:
        """
        Get weekly snapshots for dashboard.
        """
        snapshots = db.query(WeeklySnapshot).filter(
            WeeklySnapshot.user_id == user.id
        ).order_by(WeeklySnapshot.week_start.desc()).limit(weeks).all()
        return snapshots
    
    @staticmethod
    async def generate_weekly_snapshot(db: Session, user: User) -> WeeklySnapshot:
        """
        Generate a weekly snapshot and complete the 'Weekly Dashboard' task if it exists.
        """
        # Calculate week start (last Monday)
        today = datetime.utcnow().date()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        
        # Check if snapshot already exists
        existing = db.query(WeeklySnapshot).filter(
            WeeklySnapshot.user_id == user.id,
            WeeklySnapshot.week_start == week_start
        ).first()
        
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"本周 ({week_start}) 仪表盘快照已生成"
            )
        
        # Aggregate data for the week
        week_end = week_start + timedelta(days=6)
        
        entries = db.query(MetricEntry).filter(
            MetricEntry.user_id == user.id,
            func.date(MetricEntry.created_at) >= week_start,
            func.date(MetricEntry.created_at) <= week_end
        ).all()
        
        # Calculate stats
        weight_entries = [e.value for e in entries if e.metric_type == "weight"]
        sleep_entries = [e.value for e in entries if e.metric_type == "sleep"]
        workout_entries = [e.value for e in entries if e.metric_type == "workout"]
        
        stats = {
            "weight_avg": sum(weight_entries) / len(weight_entries) if weight_entries else None,
            "sleep_avg_mins": sum(sleep_entries) / len(sleep_entries) if sleep_entries else None,
            "workout_total_mins": sum(workout_entries),
            "entries_count": len(entries)
        }
        
        # Create Snapshot
        snapshot = WeeklySnapshot(
            user_id=user.id,
            week_start=week_start,
            summary_data=json.dumps(stats),
            ai_analysis="本周数据汇总完成。"  # Placeholder, can be enhanced with AI later
        )
        db.add(snapshot)
        db.commit()
        
        # Link logic: Find and complete "Weekly Dashboard Update" task
        # We look for a task with a title containing "仪表盘" or "Dashboard" that is OPEN
        task = db.query(Task).filter(
            Task.user_id == user.id,
            Task.status == "OPEN",
            (Task.title.ilike("%仪表盘%") | Task.title.ilike("%dashboard%"))
        ).first()
        
        if task:
            try:
                # We can reuse complete_task logic, but we need to bypass the evidence check
                # or assume this generation IS the evidence.
                # Since this is a system-triggered completion, we update directly.
                task.status = "DONE"
                task.completed_at = datetime.utcnow()
                task.evidence_type = "system_generated"
                task.evidence_criteria = f"Snapshot generated for week {week_start}"
                db.commit()
                logger.info(f"Auto-completed task {task.id} after snapshot generation")
            except Exception as e:
                logger.error(f"Failed to auto-complete task: {e}")
        
        return snapshot
