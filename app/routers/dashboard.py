"""Dashboard and metrics router."""
from typing import List, Optional

from fastapi import APIRouter, Depends, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.metric import (
    MetricEntryCreate,
    MetricEntryResponse,
    WeeklySnapshotResponse,
)
from app.services.metric_service import MetricService

router = APIRouter(tags=["dashboard"]) # /api prefix removed, mounted at root or handled via specific paths if needed. Wait, usually /api implies root. If paths are /stats, then it becomes /stats.


@router.post("/metrics/entries", response_model=MetricEntryResponse, status_code=201)
async def create_metric_entry(
    metric_type: str = Form(..., description="weight/sleep/workout/bodyfat"),
    value: float = Form(0.0),
    unit: str = Form(""),
    task_id: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a metric entry.
    
    If metric_type is 'bodyfat' and an image is uploaded, 
    AI will estimate the bodyfat percentage override the 'value' field.
    """
    data = MetricEntryCreate(
        metric_type=metric_type,
        value=value,
        unit=unit,
        task_id=task_id,
        notes=notes
    )
    
    entry = await MetricService.create_metric_entry(db, current_user, data, image)
    return entry


@router.post("/dashboard/weekly/generate", response_model=WeeklySnapshotResponse)
async def generate_weekly_snapshot(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate this week's dashboard snapshot.
    
    Triggering this will also look for an OPEN task with "Dashboard" or "仪表盘" 
    in the title and mark it as DONE (Weekly Dashboard Update task).
    """
    snapshot = await MetricService.generate_weekly_snapshot(db, current_user)
    return snapshot


@router.get("/dashboard/weekly", response_model=List[WeeklySnapshotResponse])
def get_weekly_snapshots(
    weeks: int = 12,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get history of weekly snapshots."""
    snapshots = MetricService.calc_dashboard_stats(db, current_user, weeks)
    return snapshots
