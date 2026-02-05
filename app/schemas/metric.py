"""Dashboard and Metric schemas."""
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class MetricEntryCreate(BaseModel):
    """Schema for creating a metric entry."""
    metric_type: str = Field(..., description="weight/sleep/workout/bodyfat")
    value: float
    unit: str
    task_id: Optional[str] = None
    notes: Optional[str] = None


class MetricEntryResponse(BaseModel):
    """Schema for metric entry response."""
    id: str
    user_id: str
    metric_type: str
    value: float
    unit: str
    task_id: Optional[str]
    evidence_id: Optional[str]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WeeklySnapshotResponse(BaseModel):
    """Schema for weekly snapshot response."""
    id: str
    user_id: str
    week_start: date
    summary_data: str  # JSON string
    ai_analysis: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class DashboardStats(BaseModel):
    """Aggregated stats for the dashboard."""
    weight_trend: List[Dict[str, Any]]
    sleep_avg: float
    workout_total_mins: float
    bodyfat_latest: Optional[float]
    week_start: date
    
    class Config:
        from_attributes = True
