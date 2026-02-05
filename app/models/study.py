"""Study session models."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Enum
from sqlalchemy.orm import relationship
import enum

from app.database import Base

class SessionStatus(str, enum.Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"

class StudySession(Base):
    """
    Study session model for Pomodoro/Focus tracking.
    """
    __tablename__ = "study_sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Context (Optional Project/Task)
    # If both are null, it's a "Free Focus" session (categorized as Other)
    project_id = Column(String, ForeignKey("projects.id"), nullable=True) 
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)

    # Snapshots (Prevent data loss if project/task is deleted)
    project_name_snapshot = Column(String, nullable=True)
    task_title_snapshot = Column(String, nullable=True)
    custom_label = Column(String, nullable=True) # For "Free Focus" path

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False) # Start time
    ended_at = Column(DateTime, nullable=True)
    duration_sec = Column(Integer, default=0, nullable=False) # Actual focus seconds (excluding pause)
    
    status = Column(String, default=SessionStatus.COMPLETED.value) # completed/abandoned

    # Relationships
    user = relationship("User", back_populates="study_sessions")
    project = relationship("Project")
    task = relationship("Task")
