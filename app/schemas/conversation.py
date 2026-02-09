"""Conversation schemas for multi-turn planning."""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single message in the conversation."""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    """Request to continue a conversation."""
    conversation_id: Optional[str] = None  # None for new conversation
    message: str = Field(..., min_length=1, max_length=2000)


class ChatResponse(BaseModel):
    """Response from the chat endpoint."""
    conversation_id: str
    action_type: str = Field(..., pattern="^(ask_more|create_task|create_project|reply|review_task|confirm_brief|update_plan)$")
    message: str  # AI's response message
    
    # Optional fields depending on action_type
    plan: Optional[Dict[str, Any]] = None  # For create_project
    task: Optional[Dict[str, Any]] = None  # For create_task
    planning_session_id: Optional[str] = None  # For plan commit/restore
    
    # Metadata
    stage: str  # current conversation stage
    intent: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "conversation_id": "conv-uuid",
                "action_type": "ask_more",
                "message": "好的！为了帮你制定合理的计划，我需要了解：\n1. 期望多久完成？\n2. 每天能投入多少时间？",
                "stage": "gathering",
                "intent": "complex_project"
            }
        }


class QuickTaskRequest(BaseModel):
    """Request to quickly create a single task."""
    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    deadline: datetime
    evidence_type: str = Field(default="none", pattern="^(none|text|number|image)$")


class QuickTaskResponse(BaseModel):
    """Response after creating a quick task."""
    task_id: str
    title: str
    deadline: datetime


class InjectReminderRequest(BaseModel):
    """Request to inject a reminder message into the conversation."""
    data: Dict[str, Any]

