"""Project long task template model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import relationship

from app.database import Base


class ProjectLongTaskTemplate(Base):
    """Template for long-term tasks within a project."""
    __tablename__ = "project_long_task_templates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    title = Column(String, nullable=False)

    # Frequency strategy
    # "interval" (every N days) or "specific_days" (Mon, Wed, Fri)
    frequency_mode = Column(String, default="interval", nullable=False)
    interval_days = Column(Integer, default=1, nullable=True)
    days_of_week = Column(String, nullable=True)  # JSON list of integers [0..6]

    # Deadline strategy
    default_due_time = Column(String, nullable=True)  # "HH:MM"
    default_start_time = Column(String, nullable=True)  # "HH:MM"
    default_end_time = Column(String, nullable=True)  # "HH:MM"

    # Evidence configuration
    evidence_type = Column(String, default="none")  # none/image/text/number
    evidence_criteria = Column(Text, nullable=True)

    # Cycle control
    total_cycle_days = Column(Integer, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Visibility (hide only)
    is_hidden = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    tasks = relationship("Task", back_populates="long_task_template")
