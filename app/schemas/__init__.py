"""Schemas package."""
from app.schemas.auth import UserCreate, UserLogin, Token, UserResponse
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskEvidenceSubmit,
    TaskEvidenceResponse,
    PlanTemplateCreate,
    PlanTemplateResponse,
)
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    MilestoneCreate,
    MilestoneResponse,
    ProjectWithMilestones,
)
from app.schemas.exemption import (
    ExemptionQuotaResponse,
    UseDayPass,
    UseRuleBreak,
    ExemptionLogResponse,
)
from app.schemas.metric import (
    MetricEntryCreate,
    MetricEntryResponse,
    WeeklySnapshotResponse,
    DashboardStats,
)
from app.schemas.project_long_task import (
    ProjectLongTaskTemplateCreate,
    ProjectLongTaskTemplateUpdate,
    ProjectLongTaskTemplateResponse,
)

__all__ = [
    "UserCreate",
    "UserLogin",
    "Token",
    "UserResponse",
    "TaskCreate",
    "TaskResponse",
    "TaskEvidenceSubmit",
    "TaskEvidenceResponse",
    "PlanTemplateCreate",
    "PlanTemplateResponse",
    "ProjectCreate",
    "ProjectResponse",
    "MilestoneCreate",
    "MilestoneResponse",
    "ProjectWithMilestones",
    "ExemptionQuotaResponse",
    "UseDayPass",
    "UseRuleBreak",
    "ExemptionLogResponse",
    "MetricEntryCreate",
    "MetricEntryResponse",
    "WeeklySnapshotResponse",
    "DashboardStats",
    "ProjectLongTaskTemplateCreate",
    "ProjectLongTaskTemplateUpdate",
    "ProjectLongTaskTemplateResponse",
]
