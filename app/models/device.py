"""Device models (placeholder for future use)."""
import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.orm import relationship

from app.database import Base


class Device(Base):
    """Device table (placeholder)."""
    __tablename__ = "devices"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String, nullable=False, unique=True, index=True)  # Hardware identifier
    type = Column(String, nullable=False)  # esp32/wearable
    name = Column(String, nullable=True)
    last_seen = Column(DateTime, nullable=True)
    status = Column(String, default="offline", nullable=False)  # online/offline
    config = Column(Text, nullable=True)  # JSON config
    
    # Relationships
    tokens = relationship("DeviceToken", back_populates="device")
