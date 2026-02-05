"""User model."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    """User table."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    
    # Habit tracking
    last_habit_generation_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    tokens = relationship("UserToken", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("Task", back_populates="user")
    projects = relationship("Project", back_populates="user")
    exemption_quotas = relationship("ExemptionQuota", back_populates="user")
    habit_templates = relationship("HabitTemplate", back_populates="user", cascade="all, delete-orphan")
    fixed_blocks = relationship("FixedBlock", back_populates="user", cascade="all, delete-orphan")
    metrics = relationship("MetricEntry", back_populates="user", cascade="all, delete-orphan")
    weekly_snapshots = relationship("WeeklySnapshot", back_populates="user", cascade="all, delete-orphan")
    planning_sessions = relationship("PlanningSession", back_populates="user", cascade="all, delete-orphan")
    conversation_sessions = relationship("ConversationSession", back_populates="user", cascade="all, delete-orphan")
    study_sessions = relationship("StudySession", back_populates="user", cascade="all, delete-orphan")


class UserToken(Base):
    """User token table."""
    __tablename__ = "user_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tokens")


class DeviceToken(Base):
    """Device token table."""
    __tablename__ = "device_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_pk = Column(String, ForeignKey("devices.id"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=True)  # NULL = permanent
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    device = relationship("Device", back_populates="tokens")
