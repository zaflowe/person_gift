"""Personal telemetry models.

Source-agnostic primitives for device notifications, social metrics and GPT-authored
life context. Raw inputs are retained so parsers can be improved later.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False, index=True)
    kind = Column(String, nullable=False, default="raw", index=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    normalized_json = Column(Text, nullable=True)
    dedupe_key = Column(String, nullable=True, unique=True, index=True)
    occurred_at = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed = Column(Boolean, default=False, nullable=False, index=True)

    analysis = relationship("TelemetryEventAnalysis", uselist=False, lazy="selectin", viewonly=True)


class TelemetryEventAnalysis(Base):
    """AI proposals and user-confirmed corrections never replace raw events."""
    __tablename__ = "telemetry_event_analyses"

    event_id = Column(String, ForeignKey("telemetry_events.id"), primary_key=True)
    status = Column(String, nullable=False, default="queued", index=True)
    result_json = Column(Text, nullable=True)
    correction_json = Column(Text, nullable=True)
    context_json = Column(Text, nullable=True)
    usage_json = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)
    error_code = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TelemetryAnalysisJob(Base):
    __tablename__ = "telemetry_analysis_jobs"

    event_id = Column(String, ForeignKey("telemetry_events.id"), primary_key=True)
    status = Column(String, nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    next_attempt_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    lease_until = Column(DateTime, nullable=True)
    claim_token = Column(String, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class TelemetryAnalysisFeedback(Base):
    """Append-only history of explicit user corrections."""
    __tablename__ = "telemetry_analysis_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("telemetry_events.id"), nullable=False, index=True)
    correction_json = Column(Text, nullable=False)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)


class TelemetryMetric(Base):
    __tablename__ = "telemetry_metrics"
    __table_args__ = (
        UniqueConstraint("source", "metric", "observed_at", "dimensions_json", name="uq_telemetry_metric_point"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False, index=True)
    metric = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    dimensions_json = Column(Text, nullable=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class LifeNote(Base):
    __tablename__ = "life_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=True)
    importance = Column(Float, nullable=False, default=0.5)
    source = Column(String, nullable=False, default="gpt", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class PersonalState(Base):
    __tablename__ = "personal_state"

    key = Column(String, primary_key=True)
    value_json = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="gpt")
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
