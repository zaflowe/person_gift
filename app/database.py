"""Database configuration and session management."""
from datetime import timedelta

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
print(f"Connecting to database: {settings.database_url}")
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
        _ensure_tasks_board_lane_columns()
        _ensure_milestone_order_column()
        _ensure_task_milestone_column()
        _ensure_study_quick_start_columns()
        _ensure_task_quick_start_columns()
        _backfill_task_time_windows()
        _backfill_milestone_order()
        _dedupe_long_task_generated_tasks()
        _dedupe_habit_generated_tasks()
        _ensure_long_task_daily_unique_index()
        _ensure_habit_daily_unique_index()
    except Exception as e:
        print(f"Migration warning: {e}")


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


def _ensure_tasks_board_lane_columns():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("tasks")]
    with engine.begin() as conn:
        if "board_lane" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE tasks ADD COLUMN board_lane VARCHAR"))
            else:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS board_lane VARCHAR"))
        if "board_lane_updated_at" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE tasks ADD COLUMN board_lane_updated_at DATETIME"))
            else:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS board_lane_updated_at TIMESTAMP"))


def _ensure_milestone_order_column():
    inspector = inspect(engine)
    if "milestones" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("milestones")]
    if "order_index" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE milestones ADD COLUMN order_index INTEGER DEFAULT 0"))
        else:
            conn.execute(text("ALTER TABLE milestones ADD COLUMN IF NOT EXISTS order_index INTEGER DEFAULT 0"))


def _ensure_task_milestone_column():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("tasks")]
    if "milestone_id" in columns:
        return

    with engine.begin() as conn:
        if settings.database_url.startswith("sqlite"):
            conn.execute(text("ALTER TABLE tasks ADD COLUMN milestone_id VARCHAR"))
        else:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS milestone_id VARCHAR"))


def _ensure_study_quick_start_columns():
    inspector = inspect(engine)
    if "study_sessions" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("study_sessions")]
    with engine.begin() as conn:
        if "is_quick_start" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN is_quick_start BOOLEAN DEFAULT 0"))
            else:
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS is_quick_start BOOLEAN DEFAULT FALSE"))
        if "quick_start_action" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN quick_start_action VARCHAR"))
            else:
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS quick_start_action VARCHAR"))
        if "quick_start_valid" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN quick_start_valid BOOLEAN DEFAULT 0"))
            else:
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS quick_start_valid BOOLEAN DEFAULT FALSE"))
        if "quick_start_task_id" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN quick_start_task_id VARCHAR"))
            else:
                conn.execute(text("ALTER TABLE study_sessions ADD COLUMN IF NOT EXISTS quick_start_task_id VARCHAR"))


def _ensure_task_quick_start_columns():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    columns = [col["name"] for col in inspector.get_columns("tasks")]
    with engine.begin() as conn:
        if "is_quick_start" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE tasks ADD COLUMN is_quick_start BOOLEAN DEFAULT 0"))
            else:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS is_quick_start BOOLEAN DEFAULT FALSE"))
        if "quick_start_action" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE tasks ADD COLUMN quick_start_action TEXT"))
            else:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS quick_start_action TEXT"))
        if "quick_start_session_id" not in columns:
            if settings.database_url.startswith("sqlite"):
                conn.execute(text("ALTER TABLE tasks ADD COLUMN quick_start_session_id VARCHAR"))
            else:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN IF NOT EXISTS quick_start_session_id VARCHAR"))


def _backfill_task_time_windows():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, created_at, scheduled_time, deadline FROM tasks "
            "WHERE scheduled_time IS NULL OR deadline IS NULL"
        )).mappings().all()

        for row in rows:
            created_at = row["created_at"]
            if isinstance(created_at, str):
                created_at = created_at.replace("Z", "+00:00")
                try:
                    from datetime import datetime as _dt
                    created_at = _dt.fromisoformat(created_at)
                except Exception:
                    continue
            scheduled_time = row["scheduled_time"]
            deadline = row["deadline"]

            if scheduled_time is None and deadline is None:
                scheduled_time = created_at
                deadline = created_at + timedelta(hours=1)
            elif scheduled_time is None and deadline is not None:
                scheduled_time = deadline - timedelta(hours=1)
            elif scheduled_time is not None and deadline is None:
                deadline = scheduled_time + timedelta(hours=1)

            if deadline <= scheduled_time:
                deadline = scheduled_time + timedelta(hours=1)

            conn.execute(
                text(
                    "UPDATE tasks SET "
                    "scheduled_time = :scheduled_time, "
                    "scheduled_date = COALESCE(scheduled_date, :scheduled_time), "
                    "deadline = :deadline, "
                    "duration = COALESCE(duration, :duration), "
                    "is_time_blocked = 1 "
                    "WHERE id = :id"
                ),
                {
                    "id": row["id"],
                    "scheduled_time": scheduled_time,
                    "deadline": deadline,
                    "duration": max(int((deadline - scheduled_time).total_seconds() // 60), 1),
                }
            )


def _backfill_milestone_order():
    inspector = inspect(engine)
    if "milestones" not in inspector.get_table_names():
        return

    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, project_id, target_date
            FROM milestones
        """)).mappings().all()
        grouped = {}
        for row in rows:
            grouped.setdefault(row["project_id"], []).append(row)

        for project_rows in grouped.values():
            project_rows.sort(key=lambda r: ((r["target_date"] is None), r["target_date"], r["id"]))
            for order, row in enumerate(project_rows):
                conn.execute(
                    text("UPDATE milestones SET order_index = :order_index WHERE id = :id AND (order_index IS NULL OR order_index = 0)"),
                    {"id": row["id"], "order_index": order},
                )


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


def _dedupe_habit_generated_tasks():
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
                            PARTITION BY template_id, generated_for_date
                            ORDER BY created_at ASC, id ASC
                        ) AS rn
                    FROM tasks
                    WHERE template_id IS NOT NULL
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


def _ensure_habit_daily_unique_index():
    inspector = inspect(engine)
    if "tasks" not in inspector.get_table_names():
        return

    index_name = "uq_tasks_habit_template_generated_for_date"
    existing_indexes = {idx["name"] for idx in inspector.get_indexes("tasks")}
    if index_name in existing_indexes:
        return

    with engine.begin() as conn:
        conn.execute(text(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {index_name} "
            "ON tasks (template_id, generated_for_date)"
        ))
