"""Planning session models."""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class PlanningSession(Base):
    """
    Planning session record.
    
    Stores the user's original message and the AI-generated plan.
    Links to the created project if committed.
    """
    __tablename__ = "planning_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    message = Column(Text, nullable=False)  # Original user input
    plan_json = Column(Text)  # AI-generated plan (JSON string)
    project_id = Column(String, ForeignKey("projects.id"))  # Set after commit
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="planning_sessions")
    project = relationship("Project", back_populates="planning_session")
