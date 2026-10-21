"""Main FastAPI application."""
import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import init_db
from app.services.scheduler import start_scheduler, stop_scheduler
from app.routers import (
    auth,
    system_tasks,
    tasks,
    projects,
    exemptions,
    dashboard,
    planner,
    conversation,
    schedule,
    placeholders,
    metrics,
    study,
    dashboard_v2,
    habits,
    project_long_tasks,
)
from app.routers import telemetry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application startup: Initializing database and starting scheduler...")
    init_db()
    start_scheduler()
    yield
    logger.info("Application shutdown: Stopping scheduler...")
    stop_scheduler()


app = FastAPI(
    title="Personal Sovereignty System",
    description="A strong constraint enforcement system for personal task and project management",
    version="1.1.0",
    lifespan=lifespan,
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


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
app.mount("/static", StaticFiles(directory="app/static"), name="static")

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
app.include_router(habits.router)
app.include_router(project_long_tasks.router)
app.include_router(telemetry.router)

# API-prefixed aliases for direct backend/frontend calls. In production Caddy
# strips /api before proxying, so /telemetry remains the canonical backend route.
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
app.include_router(telemetry.router, prefix="/api")


@app.get("/")
def root():
    return {
        "message": "Personal Sovereignty System API",
        "version": "1.1.0",
        "docs": "/docs",
        "telemetry": "/telemetry/ping",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
