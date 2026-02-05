"""Placeholder routers for future modules."""
from fastapi import APIRouter

# Content system (placeholder)
content_router = APIRouter(prefix="/content", tags=["content"])

@content_router.get("/")
def get_content_placeholder():
    """Placeholder for content system."""
    return {"message": "Content system - coming soon"}


# Devices system (placeholder)
devices_router = APIRouter(prefix="/devices", tags=["devices"])

@devices_router.get("/")
def get_devices_placeholder():
    """Placeholder for devices system."""
    return {"message": "Devices system - coming soon"}


# Tools system (placeholder)
tools_router = APIRouter(prefix="/tools", tags=["tools"])

@tools_router.get("/")
def get_tools_placeholder():
    """Placeholder for tools system."""
    return {"message": "Tools system - coming soon"}
