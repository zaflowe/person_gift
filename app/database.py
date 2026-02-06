"""Database configuration and session management."""
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from app.config import settings

# Create SQLAlchemy engine
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.database_url,
    connect_args=connect_args
)
print(f"🔥 Connecting to database: {settings.database_url}")
# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables."""
    from app.models import user, task, project, exemption, device, metric, conversation, study, project_long_task
    Base.metadata.create_all(bind=engine)

    # Lightweight, non-destructive migration for new columns in existing DBs.
    try:
        _ensure_tasks_long_template_column()
        _ensure_habit_evidence_criteria_column()
    except Exception as e:
        print(f"⚠️ Migration warning: {e}")


def _ensure_tasks_long_template_column():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "long_task_template_id" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN long_task_template_id VARCHAR"))
        else:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS long_task_template_id VARCHAR"))


def _ensure_habit_evidence_criteria_column():
    inspector = inspect(engine)
    if "habit_templates" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("habit_templates")]
    if "evidence_criteria" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE habit_templates ADD COLUMN evidence_criteria TEXT"))
        else:
            conn.execute(text("ALTER TABLE habit_templates ADD COLUMN IF NOT EXISTS evidence_criteria TEXT"))
