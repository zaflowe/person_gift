"""Conversation session model for multi-turn planning."""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class ConversationSession(Base):
    """
    Conversation session for multi-turn planning dialogue.
    
    Tracks the conversation state, intent, and collected information.
    """
    __tablename__ = "conversation_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Conversation state
    stage = Column(String, nullable=False, default="intent")  # intent/gathering/planning/completed
    intent = Column(String)  # simple_task/complex_project/question/chat
    
    # Conversation history (JSON string)
    messages = Column(Text)  # List of {role, content}
    
    # Collected information (JSON string)
    collected_info = Column(Text)  # Dict with goal, deadline, resources, etc.
    
    # Result
    planning_session_id = Column(String, ForeignKey("planning_sessions.id"))
    task_id = Column(String, ForeignKey("tasks.id"))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="conversation_sessions")
    planning_session = relationship("PlanningSession")
    task = relationship("Task")
