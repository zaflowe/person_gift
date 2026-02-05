"""Exemption schemas."""
from datetime import datetime, date
from typing import Optional, List, Literal

from pydantic import BaseModel


class ExemptionQuotaResponse(BaseModel):
    """Schema for exemption quota response."""
    id: str
    user_id: str
    week_start: date
    day_pass_total: int
    day_pass_used: int
    day_pass_date: Optional[date]
    rule_break_total: int
    rule_break_used: int
    
    class Config:
        from_attributes = True


class UseDayPass(BaseModel):
    """Schema for using day pass."""
    date: date
    reason: Optional[str] = None


class UseRuleBreak(BaseModel):
    """Schema for using rule break."""
    task_id: str
    reason: Optional[str] = None


class ExemptionLogResponse(BaseModel):
    """Schema for exemption log response."""
    id: str
    quota_id: str
    type: str
    task_id: Optional[str]
    used_at: datetime
    reason: Optional[str]
    
    class Config:
        from_attributes = True
