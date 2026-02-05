"""Metric router."""
from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.metric import MetricEntry

router = APIRouter(prefix="/metrics", tags=["metrics"])

class MetricEntryBase(BaseModel):
    metric_type: str  # weight, bodyfat
    value: float
    unit: str
    notes: Optional[str] = None

class MetricEntryCreate(MetricEntryBase):
    pass

class MetricEntryResponse(MetricEntryBase):
    id: str
    created_at: datetime
    
    class Config:
        orm_mode = True

@router.get("/history", response_model=List[MetricEntryResponse])
async def get_metric_history(
    metric_type: str,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get metric history for the specified type."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    
    entries = db.query(MetricEntry).filter(
        MetricEntry.user_id == current_user.id,
        MetricEntry.metric_type == metric_type,
        MetricEntry.created_at >= cutoff
    ).order_by(MetricEntry.created_at.asc()).all()
    
    return entries

@router.post("/entry", response_model=MetricEntryResponse)
async def create_metric_entry(
    entry: MetricEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new metric entry."""
    new_entry = MetricEntry(
        user_id=current_user.id,
        metric_type=entry.metric_type,
        value=entry.value,
        unit=entry.unit,
        notes=entry.notes
    )
    
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry
