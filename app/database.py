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
        _ensure_conversation_planning_session_id()
        _ensure_tasks_proposal_offset_column()
        _ensure_milestones_proposal_offset_column()
        _dedupe_long_task_generated_tasks()
        _ensure_long_task_daily_unique_index()
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


def _ensure_conversation_planning_session_id():
    inspector = inspect(engine)
    if "conversation_sessions" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("conversation_sessions")]
    if "planning_session_id" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE conversation_sessions ADD COLUMN planning_session_id VARCHAR"))
        else:
            conn.execute(text("ALTER TABLE conversation_sessions ADD COLUMN IF NOT EXISTS planning_session_id VARCHAR"))


def _ensure_tasks_proposal_offset_column():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "proposal_offset_days" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN proposal_offset_days INTEGER"))
        else:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS proposal_offset_days INTEGER"))


def _ensure_milestones_proposal_offset_column():
    inspector = inspect(engine)
    if "milestones" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("milestones")]
    if "proposal_offset_days" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE milestones ADD COLUMN proposal_offset_days INTEGER"))
        else:
            conn.execute(text("ALTER TABLE milestones ADD COLUMN IF NOT EXISTS proposal_offset_days INTEGER"))


def _dedupe_long_task_generated_tasks():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM tasks
            WHERE id IN (
                SELECT id FROM (
                    SELECT
                        id,
                        ROW_NUMBER() OVER (
                            PARTITION BY long_task_template_id, generated_for_date
                            ORDER BY created_at ASC, id ASC
                        ) AS rn
                    FROM tasks
                    WHERE long_task_template_id IS NOT NULL
                      AND generated_for_date IS NOT NULL
                ) ranked
                WHERE ranked.rn > 1
            )
        """))


def _ensure_long_task_daily_unique_index():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    index_name = "uq_tasks_long_template_generated_for_date"
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("tasks")}
    if index_name in existing_indexes:
        return

    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
            "ON tasks (long_task_template_id, generated_for_date)"
        ))
