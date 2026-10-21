"""Personal telemetry models.

These tables are intentionally source-agnostic. Phones, social platforms, future
connectors and GPT can all write into the same small set of primitives.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, String, Text

from app.database import Base


class TelemetryEvent(Base):
    """Immutable-ish raw event captured from an external source."""

    __tablename__ = "telemetry_events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False, index=True)
    kind = Column(String, nullable=False, default="raw", index=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    payload_json = Column(Text, nullable=True)
    occurred_at = Column(DateTime, nullable=True, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed = Column(Boolean, default=False, nullable=False, index=True)


class TelemetryMetric(Base):
    """Numeric time-series point, e.g. followers, play count or spending."""

    __tablename__ = "telemetry_metrics"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source = Column(String, nullable=False, index=True)
    metric = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)
    unit = Column(String, nullable=True)
    dimensions_json = Column(Text, nullable=True)
    observed_at = Column(DateTime, nullable=False, index=True)
    received_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class LifeNote(Base):
    """Human- or GPT-authored semantic life note."""

    __tablename__ = "life_notes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    text = Column(Text, nullable=False)
    tags_json = Column(Text, nullable=True)
    importance = Column(Float, nullable=False, default=0.5)
    source = Column(String, nullable=False, default="gpt", index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


class PersonalState(Base):
    """Latest known value for a named piece of personal state."""

    __tablename__ = "personal_state"

    key = Column(String, primary_key=True)
    value_json = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="gpt")
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
