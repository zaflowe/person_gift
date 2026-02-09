"""Task models."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Task(Base):
    """Task table."""
    __tablename__ = "tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="OPEN")  # OPEN/EVIDENCE_SUBMITTED/DONE/EXCUSED/OVERDUE/LOCKED
    evidence_type = Column(String, nullable=True)  # image/text/number/none
    evidence_criteria = Column(Text, nullable=True)
    deadline = Column(DateTime, nullable=True)
    proposal_offset_days = Column(Integer, nullable=True)
    tags = Column(String, default="[]", nullable=False)  # JSON list of strings
    
    # Time blocking fields
    scheduled_date = Column(DateTime, nullable=True)  # Which day this task is scheduled
    scheduled_time = Column(DateTime, nullable=True)  # What time it starts
    duration = Column(Integer, nullable=True)  # Duration in minutes
    is_time_blocked = Column(Boolean, default=False, nullable=False)  # Has time been allocated
    
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    plan_template_id = Column(String, ForeignKey("plan_templates.id"), nullable=True)
    long_task_template_id = Column(String, ForeignKey("project_long_task_templates.id"), nullable=True)
    
    # Habit fields
    template_id = Column(String, ForeignKey("habit_templates.id"), nullable=True)
    generated_for_date = Column(DateTime, nullable=True) # Which date (YYYY-MM-DD) this was generated for
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    project = relationship("Project", back_populates="tasks")
    plan_template = relationship("PlanTemplate", back_populates="tasks")
    habit_template = relationship("HabitTemplate", back_populates="tasks")
    long_task_template = relationship("ProjectLongTaskTemplate", back_populates="tasks")
    evidences = relationship("TaskEvidence", back_populates="task", cascade="all, delete-orphan")



class PlanTemplate(Base):
    """Plan template table for recurring tasks."""
    __tablename__ = "plan_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    frequency = Column(String, nullable=False)  # daily/weekly
    times_per_week = Column(Integer, nullable=True)  # For weekly frequency
    evidence_type = Column(String, nullable=True)
    evidence_criteria = Column(Text, nullable=True)
    default_deadline_hour = Column(Integer, default=23, nullable=False)  # 0-23
    timezone = Column(String, default="Asia/Taipei", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tasks = relationship("Task", back_populates="plan_template")


class TaskEvidence(Base):
    """Task evidence table."""
    __tablename__ = "task_evidence"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False)
    evidence_type = Column(String, nullable=False)  # image/text/number
    content = Column(Text, nullable=True)  # For text/number
    image_path = Column(String, nullable=True)  # For image
    ai_result = Column(String, nullable=True)  # pass/fail
    ai_reason = Column(Text, nullable=True)
    extracted_values = Column(Text, nullable=True)  # JSON string
    submitted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    task = relationship("Task", back_populates="evidences")
