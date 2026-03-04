import logging
import uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import json
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.config import settings
from app.models.user import User
from app.models.task import Task
from app.models.project import Project
from app.models.conversation import ConversationSession
from app.database import SessionLocal

logger = logging.getLogger(__name__)

def generate_daily_reminder_content(db: Session, user: User) -> str:
    """Generate the daily reminder text content."""
    now = datetime.utcnow()
    # Adjust for consistent local time display (assuming UTC+8 for now based on user context)
    # Ideally should use user's timezone setting.
    today_display = (datetime.utcnow() + timedelta(hours=8)).strftime("%m-%d") 
    
    # 1. Incomplete Tasks (Total count)
    base_query = db.query(Task).outerjoin(Project, Task.project_id == Project.id).filter(
        Task.user_id == user.id,
        Task.status != "DONE",
        Task.status != "LOCKED",
        or_(Task.project_id.is_(None), Project.status != "PROPOSED")
    )

    incomplete_count = base_query.count()

    # 2. Overdue Tasks
    overdue_query = base_query.filter(
        Task.deadline < now
    ).order_by(Task.deadline.asc())
    
    overdue_tasks = overdue_query.all()
    overdue_count = len(overdue_tasks)

    # 3. Due Soon (Next 24h)
    tomorrow = now + timedelta(days=1)
    due_soon_query = base_query.filter(
        Task.deadline >= now,
        Task.deadline <= tomorrow
    ).order_by(Task.deadline.asc())
    
    due_soon_tasks = due_soon_query.all()
    due_soon_count = len(due_soon_tasks)

    # Deduplication Helper
    seen_titles = set()
    def get_unique_tasks(tasks, limit=3):
        unique = []
        for t in tasks:
            if t.title not in seen_titles:
                unique.append(t)
                seen_titles.add(t.title)
            if len(unique) >= limit:
                break
        return unique

    # Construct Message - Conversational Style
    lines = []
    
    # Greeting
    lines.append(f"早安 ({today_display}) 🌞")
    
    has_urgent = False
    
    # Serious Stuff First (Overdue)
    if overdue_count > 0:
        has_urgent = True
        unique_overdue = get_unique_tasks(overdue_tasks, limit=3)
        lines.append(f"⚠️ 有 {overdue_count} 个任务已逾期，建议优先处理：")
        for task in unique_overdue:
            dt_str = (task.deadline + timedelta(hours=8)).strftime("%H:%M") if task.deadline else ""
            lines.append(f"- {task.title}")
    
    # Urgent Stuff (Due Soon)
    elif due_soon_count > 0: # Use elif to avoid overwhelming if both exist, unless critical
        has_urgent = True
        unique_soon = get_unique_tasks(due_soon_tasks, limit=3)
        lines.append(f"⚡ 今天有 {due_soon_count} 个任务截止：")
        for task in unique_soon:
            # Simple time display
            dt_str = (task.deadline + timedelta(hours=8)).strftime("%H:%M")
            lines.append(f"- {task.title} ({dt_str})")

    # General Status if no urgent implementation
    if not has_urgent:
        if incomplete_count > 0:
            lines.append(f"目前还有 {incomplete_count} 个待办事项。保持专注！💪")
        else:
            lines.append("全部清空！今天是个自由的好日子 ✨")
    else:
        # Footer for urgent scenarios
        remaining = incomplete_count - overdue_count - due_soon_count
        if remaining > 0:
            lines.append(f"\n还有其他 {remaining} 个待办，不急的话先放放。")

    return "\n".join(lines)


def _has_daily_reminder_for_local_date(history: list, timezone_name: str) -> bool:
    """Return True if a daily reminder already exists for today in local timezone."""
    tz = ZoneInfo(timezone_name)
    today_local = datetime.now(tz).date()

    for msg in reversed(history):
        if msg.get("type") != "daily_reminder":
            continue
        ts = msg.get("timestamp")
        if not ts:
            continue
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        except Exception:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        if dt.astimezone(tz).date() == today_local:
            return True
    return False


def inject_daily_reminder_for_user(db: Session, user: User) -> bool:
    """Inject reminder into user's conversation; returns True if inserted."""
    content = generate_daily_reminder_content(db, user)

    session = db.query(ConversationSession).filter(
        ConversationSession.user_id == user.id
    ).order_by(ConversationSession.created_at.desc()).first()

    if not session:
        session = ConversationSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            stage="intent",
            messages="[]",
            collected_info="{}"
        )
        db.add(session)
        db.commit()

    history = []
    if session.messages:
        try:
            history = json.loads(session.messages)
        except Exception:
            history = []

    if _has_daily_reminder_for_local_date(history, settings.timezone):
        logger.info(f"Skip daily reminder for user {user.id}: already sent today")
        return False

    history.append({
        "role": "assistant",
        "content": content,
        "timestamp": datetime.utcnow().isoformat(),
        "type": "daily_reminder"
    })

    session.messages = json.dumps(history, ensure_ascii=False)
    db.commit()
    logger.info(f"Injected daily reminder for user {user.id}")
    return True


def process_all_daily_reminders():
    """Scheduled job to send reminders to all users."""
    db = SessionLocal()
    try:
        users = db.query(User).all()
        inserted = 0
        for user in users:
            try:
                if inject_daily_reminder_for_user(db, user):
                    inserted += 1
            except Exception as e:
                logger.error(f"Error injecting reminder for user {user.id}: {e}")
        logger.info(f"Daily reminder job completed: {inserted}/{len(users)} inserted")
    finally:
        db.close()
