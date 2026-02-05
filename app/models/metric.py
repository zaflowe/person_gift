"""Dashboard and Metric models."""
import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Text, Date, Index
from sqlalchemy.orm import relationship

from app.database import Base


class MetricEntry(Base):
    """Raw metric data points."""
    __tablename__ = "metric_entries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    metric_type = Column(String, nullable=False, index=True)  # weight/sleep/workout/bodyfat
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # kg/min/%
    task_id = Column(String, ForeignKey("tasks.id"), nullable=True)
    evidence_id = Column(String, ForeignKey("task_evidence.id"), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="metrics")
    task = relationship("Task")     # Optional association
    evidence = relationship("TaskEvidence") # Optional association


class WeeklySnapshot(Base):
    """Weekly dashboard snapshot."""
    __tablename__ = "weekly_snapshots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    week_start = Column(Date, nullable=False, index=True)
    summary_data = Column(Text, nullable=False)  # JSON string
    ai_analysis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="weekly_snapshots")
