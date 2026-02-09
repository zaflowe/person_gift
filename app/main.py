"""Main FastAPI application."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import traceback
from app.dependencies import get_current_user
from app.models.user import User

from app.database import init_db
from app.routers import auth, tasks, projects, exemptions, placeholders, dashboard, planner, conversation, schedule, metrics, study
from app.routers import dashboard_v2, system_tasks, reminder_inject, habits, project_long_tasks
from app.services.scheduler import start_scheduler, stop_scheduler


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Initializes the database and starts the scheduler on startup.
    Stops the scheduler on shutdown.
    """
    logger.info("Application startup: Initializing database and starting scheduler...")
    init_db()
    start_scheduler()
    yield
    logger.info("Application shutdown: Stopping scheduler...")
    stop_scheduler()


# Create FastAPI app
app = FastAPI(
    title="Personal Sovereignty System",
    description="A strong constraint enforcement system for personal task and project management",
    version="1.0.0",
    lifespan=lifespan
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = traceback.format_exc()
    print(f"GLOBAL ERROR: {error_msg}")
    with open("global_error.log", "a", encoding="utf-8") as f:
        f.write(f"ERROR on {request.url}\n{error_msg}\n\n")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "trace": str(exc)},
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # Self
        "http://127.0.0.1:8000", 
        "*"  # Keep wildcard as fallback if specific origins fail (though usually mutually exclusive, FastAPI handles it)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router)
app.include_router(auth.api_router)
app.include_router(system_tasks.router)
app.include_router(tasks.router)
app.include_router(projects.router)
app.include_router(exemptions.router)
app.include_router(dashboard.router)
app.include_router(planner.router)
app.include_router(conversation.router)
app.include_router(conversation.api_router)
app.include_router(schedule.router)
app.include_router(placeholders.content_router)
app.include_router(placeholders.devices_router)
app.include_router(placeholders.tools_router)
app.include_router(metrics.router)
app.include_router(study.router)
app.include_router(dashboard_v2.router)
# app.include_router(system_tasks.router) # Removed duplicate
app.include_router(reminder_inject.router)
app.include_router(habits.router)
app.include_router(project_long_tasks.router)

# API-prefixed aliases for frontend calls
app.include_router(tasks.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(exemptions.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(planner.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(metrics.router, prefix="/api")
app.include_router(study.router, prefix="/api")
app.include_router(system_tasks.router, prefix="/api")
app.include_router(habits.router, prefix="/api")
app.include_router(project_long_tasks.router, prefix="/api")
app.include_router(dashboard_v2.router, prefix="/api")


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "message": "Personal Sovereignty System API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}



if __name__ == "__main__":
    import uvicorn
    # Use string reference for reload to work
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
