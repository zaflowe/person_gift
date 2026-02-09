"""Reminder injection endpoint."""
from datetime import datetime
import uuid
import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.conversation import ConversationSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversation", tags=["conversation"])


@router.post("/inject-reminder")
async def inject_reminder(
    reminder_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Inject a daily reminder message into the conversation."""
    try:
        # Get or create conversation
        session = db.query(ConversationSession).filter(
            ConversationSession.user_id == current_user.id
        ).order_by(ConversationSession.created_at.desc()).first()
        
        if not session:
            session = ConversationSession(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                status="active",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(session)
            db.commit()
            db.refresh(session)
        
        # Format reminder message
        data = reminder_data.get("data", {})
        today = datetime.now().strftime("%Y-%m-%d")
        
        message_parts = [f"📋 今日提醒 ({today})\\n"]
        
        # Incomplete tasks
        incomplete = data.get("incomplete_tasks", {})
        if incomplete.get("count", 0) > 0:
            message_parts.append(f"⏰ 未完成任务：{incomplete['count']}条")
            for task in incomplete.get("top_5", []):
                deadline_str = task.get("deadline", "无截止")
                if deadline_str and deadline_str != "无截止":
                    try:
                        dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                        deadline_str = dt.strftime("%m-%d %H:%M")
                    except:
                        pass
                message_parts.append(f"  • {task['title']} (截止：{deadline_str})")
            message_parts.append("")
        
        # Overdue tasks
        overdue = data.get("overdue_tasks", {})
        if overdue.get("count", 0) > 0:
            message_parts.append(f"🔴 逾期任务：{overdue['count']}条")
            for task in overdue.get("top_5", []):
                deadline_str = task.get("deadline", "无截止")
                if deadline_str and deadline_str != "无截止":
                    try:
                        dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                        deadline_str = dt.strftime("%m-%d %H:%M")
                    except:
                        pass
                message_parts.append(f"  • {task['title']} (截止：{deadline_str})")
            message_parts.append("")
        
       # Due soon
        due_soon = data.get("due_soon_tasks", {})
        if due_soon.get("count", 0) > 0:
            message_parts.append(f"⚡ 24h内到期：{due_soon['count']}条")
            for task in due_soon.get("top_5", []):
                deadline_str = task.get("deadline", "无截止")
                if deadline_str and deadline_str != "无截止":
                    try:
                        dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                        deadline_str = dt.strftime("%m-%d %H:%M")
                    except:
                        pass
                message_parts.append(f"  • {task['title']} (截止：{deadline_str})")
            message_parts.append("")
        
        # System task
        system_task = data.get("system_task", {})
        if system_task.get("exists"):
            if system_task.get("completed"):
                message_parts.append("💪 系统周任务：已完成 ✅")
            else:
                deadline_str = system_task.get("deadline", "")
                if deadline_str:
                    try:
                        dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
                        deadline_str = dt.strftime("%m-%d %H:%M")
                    except:
                        pass
                message_parts.append(f"💪 系统周任务：未完成 ⚠️")
                message_parts.append(f"  提醒：{system_task.get('title', '本周体重记录')} (截止：{deadline_str})")
        
        if len(message_parts) == 1:  # Only has the header
            message_parts.append("\\n✨ 太棒了！目前没有紧急待办事项。")
        
        reminder_text = "\\n".join(message_parts)
        
        # Add to conversation history
        if not hasattr(session, 'history') or session.history is None:
            session.history = []
        
        session.history.append({
            "role": "assistant",
            "content": reminder_text,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "daily_reminder"
        })
        
        db.commit()
        
        return {
            "success": True,
            "message": {
                "role": "assistant",
                "content": reminder_text,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
    except Exception as e:
        logger.error(f"Failed to inject reminder: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@router.post("/login-greeting")
async def login_greeting(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Alias for login greeting (for /api prefix)."""
    session = db.query(ConversationSession).filter(
        ConversationSession.user_id == current_user.id
    ).order_by(ConversationSession.created_at.desc()).first()

    if not session:
        session = ConversationSession(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            stage="intent",
            messages="[]",
            collected_info="{}"
        )
        db.add(session)
        db.commit()

    messages = json.loads(session.messages) if session.messages else []

    open_statuses = ["OPEN", "EVIDENCE_SUBMITTED", "OVERDUE"]
    open_count = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status.in_(open_statuses)
    ).count()
    overdue_count = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status == "OVERDUE"
    ).count()
    habits_count = db.query(HabitTemplate).filter(
        HabitTemplate.user_id == current_user.id
    ).count()
    fixed_count = db.query(FixedBlock).filter(
        FixedBlock.user_id == current_user.id
    ).count()
    active_projects = db.query(Project).filter(
        Project.user_id == current_user.id,
        Project.status.in_(["PROPOSED", "ACTIVE"])
    ).count()

    next_task = db.query(Task).filter(
        Task.user_id == current_user.id,
        Task.status.in_(open_statuses),
        Task.deadline.isnot(None)
    ).order_by(Task.deadline.asc()).first()

    templates = [
        "今天也见到你了。待办 {open} 项，逾期 {overdue} 项。先动一个最小任务就能破局。",
        "你的习惯 {habits} 个、固定时间块 {fixed} 个，节奏已经在了。",
        "当前项目 {projects} 个在推进。小步快走就能赢。",
        "我随便说一句：别等完美，先做 10 分钟。待办 {open} 项在排队。",
    ]

    if next_task:
        templates.append(f"最近截止的任务是「{next_task.title}」，先把它处理掉会很爽。")

    import random
    message_text = random.choice(templates).format(
        open=open_count,
        overdue=overdue_count,
        habits=habits_count,
        fixed=fixed_count,
        projects=active_projects
    )

    new_msg = {
        "role": "assistant",
        "content": message_text,
        "type": "login_greeting",
        "timestamp": datetime.utcnow().isoformat()
    }
    messages.append(new_msg)
    session.messages = json.dumps(messages, ensure_ascii=False)
    db.commit()

    return {"message": new_msg}
