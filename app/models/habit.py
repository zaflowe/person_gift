"""Habit and fixed block models."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base


class HabitTemplate(Base):
    """Template for recurring habit tasks."""
    __tablename__ = "habit_templates"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    enabled = Column(Boolean, default=True, nullable=False)
    
    # Frequency strategy
    # "interval" (every N days) or "specific_days" (Mon, Wed, Fri)
    frequency_mode = Column(String, default="interval", nullable=False)
    
    # For "interval" mode: 1 = Daily, 2 = Every other day...
    interval_days = Column(Integer, default=1, nullable=True)
    
    # For "specific_days" mode: JSON list of integers [0, 1, ... 6] (0=Monday)
    days_of_week = Column(String, nullable=True) 
    
    # Deadline strategy
    default_due_time = Column(String, nullable=True)  # "HH:MM", e.g. "22:00"
    default_start_time = Column(String, nullable=True) # "HH:MM", e.g. "09:00"
    default_end_time = Column(String, nullable=True)   # "HH:MM", e.g. "10:00"
    
    # Evidence configuration
    evidence_type = Column(String, default="none") # none/image/text/number
    evidence_schema = Column(String, nullable=True) # e.g. unit for number

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="habit_templates")
    tasks = relationship("Task", back_populates="habit_template")


class FixedBlock(Base):
    """Fixed time block for sidebar visibility."""
    __tablename__ = "fixed_blocks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    
    # Time window (HH:MM string)
    start_time = Column(String, nullable=False) # "09:00"
    end_time = Column(String, nullable=False)   # "18:00"
    
    # JSON list of days [0, 1, 2, 3, 4] for Weekdays
    days_of_week = Column(String, nullable=True)
    
    color = Column(String, nullable=True) # Hex code or preset name
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="fixed_blocks")
