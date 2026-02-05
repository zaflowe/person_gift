"""Project models."""
import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, Date
from sqlalchemy.orm import relationship

from app.database import Base


class Project(Base):
    """Project table."""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="PROPOSED")  # PROPOSED/ACTIVE/SUCCESS/FAILURE/ABORTED
    success_criteria = Column(Text, nullable=True)
    failure_criteria = Column(Text, nullable=True)
    ai_analysis = Column(Text, nullable=True)
    user_confirmed_at = Column(DateTime, nullable=True)
    ai_confirmed_at = Column(DateTime, nullable=True)
    agreement_hash = Column(String, nullable=True)  # Required when ACTIVE
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    is_strategic = Column(Boolean, default=False, nullable=False)  # For dashboard strategic projects
    schedule_policy = Column(String, default="LOCKED", nullable=False)  # LOCKED / FLEX_ONCE
    next_milestone = Column(Text, nullable=True)  # Short text for dashboard display
    color = Column(String, nullable=True)  # Custom project color
    
    # Relationships
    user = relationship("User", back_populates="projects")
    milestones = relationship("Milestone", back_populates="project", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="project")
    planning_session = relationship("PlanningSession", back_populates="project", uselist=False)


class Milestone(Base):
    """Milestone table."""
    __tablename__ = "milestones"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_critical = Column(Boolean, default=False, nullable=False)
    status = Column(String, nullable=False, default="PENDING")  # PENDING/ACHIEVED/FAILED
    target_date = Column(Date, nullable=True)
    achieved_at = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="milestones")
