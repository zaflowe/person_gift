"""Exemption models."""
import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Text, Date
from sqlalchemy.orm import relationship

from app.database import Base


class ExemptionQuota(Base):
    """Exemption quota table."""
    __tablename__ = "exemption_quotas"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    week_start = Column(Date, nullable=False, index=True)  # Monday of the week
    day_pass_total = Column(Integer, default=1, nullable=False)
    day_pass_used = Column(Integer, default=0, nullable=False)
    day_pass_date = Column(Date, nullable=True)  # Date when day pass is active
    rule_break_total = Column(Integer, default=2, nullable=False)
    rule_break_used = Column(Integer, default=0, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="exemption_quotas")
    logs = relationship("ExemptionLog", back_populates="quota", cascade="all, delete-orphan")


class ExemptionLog(Base):
    """Exemption log table."""
    __tablename__ = "exemption_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    quota_id = Column(String, ForeignKey("exemption_quotas.id"), nullable=False)
    type = Column(String, nullable=False)  # day_pass/rule_break
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)  # For rule_break
    used_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reason = Column(Text, nullable=True)
    
    # Relationships
    quota = relationship("ExemptionQuota", back_populates="logs")


class JobLock(Base):
    """Job lock table for scheduler."""
    __tablename__ = "job_locks"
    
    job_name = Column(String, primary_key=True)  # e.g., 'weekly_task_generation'
    locked_until = Column(DateTime, nullable=False)
    locked_by = Column(String, nullable=False)  # Container/process ID
    locked_at = Column(DateTime, default=datetime.utcnow, nullable=False)
