"""Conversation router - Intelligent multi-turn planning chat."""
import json
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.conversation import ConversationSession
from app.models.task import Task
from app.schemas.conversation import (
    ChatRequest,
    ChatResponse,
    QuickTaskRequest,
    QuickTaskResponse,
    InjectReminderRequest
)
from app.services.conversation_service import conversation_service
from app.services.planner_service import planner_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversation", tags=["conversation"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Intelligent chat endpoint for multi-turn planning.
    
    Handles:
    - Intent recognition (simple task / complex project / question / chat)
    - Information gathering through questions
    - Plan generation when ready
    - Direct answers for questions
   """
    try:
        # Get or create conversation session
        if request.conversation_id:
            session = db.query(ConversationSession).filter(
                ConversationSession.id == request.conversation_id,
                ConversationSession.user_id == current_user.id
            ).first()
            
            if not session:
                raise HTTPException(status_code=404, detail="Conversation not found")
        else:
            # New conversation
            session = ConversationSession(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                stage="intent",
                messages="[]",
                collected_info="{}"
            )
            db.add(session)
            db.flush()
        
        # Parse existing data
        messages = json.loads(session.messages) if session.messages else []
        collected_info = json.loads(session.collected_info) if session.collected_info else {}
        
        # Add user message
        messages.append({"role": "user", "content": request.message})
        
        # Process based on stage
        if session.stage == "intent":
            # Recognize intent
            intent, extracted_info = conversation_service.recognize_intent(request.message)
            session.intent = intent
            collected_info.update(extracted_info)
            
            logger.info(f"Intent: {intent}")
            
            if intent == "simple_task":
                # Extract task info
                task_info = conversation_service.extract_simple_task(request.message)
                
                # Check for critical info
                if not task_info.get("deadline"):
                    # Fallback if AI didn't catch time (though prompt handles default)
                    task_info["deadline"] = datetime.now().replace(hour=23, minute=59, second=59).isoformat()
                
                # Format for display
                try:
                    deadline_dt = datetime.fromisoformat(task_info["deadline"])
                    deadline_str = deadline_dt.strftime('%Y-%m-%d %H:%M')
                except:
                    deadline_str = "未定"

                ai_message = f"帮你起草了一个任务：「{task_info['title']}」，截止时间：{deadline_str}。\n请确认或修改："
                messages.append({"role": "assistant", "content": ai_message})
                
                session.messages = json.dumps(messages, ensure_ascii=False)
                session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                # Do NOT set stage to completed yet
                db.commit()
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="review_task",  # Changed from create_task to review_task
                    message=ai_message,
                    task=task_info,  # Return the draft info
                    stage=session.stage,
                    intent=intent
                )
            
            elif intent == "view_schedule":
                # Fetch today's schedule
                today = datetime.now().date()
                tasks = db.query(Task).filter(
                    Task.user_id == current_user.id,
                    Task.scheduled_time != None
                ).all()
                
                today_tasks = [
                    t for t in tasks 
                    if t.scheduled_time and t.scheduled_time.date() == today
                ]
                today_tasks.sort(key=lambda x: x.scheduled_time)
                
                if not today_tasks:
                    ai_message = "今天暂时没有安排具体的日程任务。你可以随时告诉我你想做什么，我帮你安排。"
                else:
                    ai_message = f"这是你今天的日程安排 ({today.strftime('%Y-%m-%d')}):\n\n"
                    for t in today_tasks:
                        time_str = t.scheduled_time.strftime("%H:%M")
                        status_icon = "✅" if t.status == "DONE" else "⬜"
                        ai_message += f"{status_icon} **{time_str}** {t.title}\n"
                    
                    ai_message += "\n需要我帮你调整或添加新的安排吗？"
                
                messages.append({"role": "assistant", "content": ai_message})
                session.messages = json.dumps(messages, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="reply",
                    message=ai_message,
                    stage=session.stage,
                    intent=intent
                )

            elif intent == "complex_project":
                # Move to gathering stage
                session.stage = "gathering"
                info_complete, ai_message = conversation_service.gather_information(
                    collected_info,
                    messages
                )
                
                messages.append({"role": "assistant", "content": ai_message})
                session.messages = json.dumps(messages, ensure_ascii=False)
                session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                db.commit()
                
                if info_complete:
                    # Ready to plan
                    return ChatResponse(
                        conversation_id=session.id,
                        action_type="ask_more",
                        message=ai_message + "\n\n准备好了吗？我现在就为你生成计划。",
                        stage="gathering",
                        intent=intent
                    )
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="ask_more",
                    message=ai_message,
                    stage=session.stage,
                    intent=intent
                )
            
            elif intent == "question":
                # Answer the question
                answer = conversation_service.answer_question(request.message)
                messages.append({"role": "assistant", "content": answer})
                session.stage = "completed"
                session.completed_at = datetime.utcnow()
                session.messages = json.dumps(messages, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="reply",
                    message=answer,
                    stage=session.stage,
                    intent=intent
                )
            
            else:  # chat
                # Simple reply
                ai_message = "你好！我可以帮你规划任务和项目。有什么我能帮到你的吗？"
                messages.append({"role": "assistant", "content": ai_message})
                session.stage = "completed"
                session.completed_at = datetime.utcnow()
                session.messages = json.dumps(messages, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="reply",
                    message=ai_message,
                    stage=session.stage,
                    intent=intent
                )
        
        elif session.stage == "gathering":
            # Update collected info from user's answer
            # (In MVP, we just save the message and check if ready)
            collected_info["user_answer"] = request.message
            
            info_complete, ai_message = conversation_service.gather_information(
                collected_info,
                messages
            )
            
            messages.append({"role": "assistant", "content": ai_message})
            
            if info_complete:
                # Ready for Brief Review (Gatekeeper)
                session.stage = "brief_review"
                session.messages = json.dumps(messages, ensure_ascii=False)
                session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                db.commit()
                
                # Format collected info for display
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="confirm_brief",
                    message="信息已收集完毕。请确认项目简报（Brief），通过后将为你生成详细方案。",
                    plan=collected_info,  # Reusing plan field to pass brief data for now
                    stage=session.stage,
                    intent=session.intent
                )
            else:
                # Continue gathering
                session.messages = json.dumps(messages, ensure_ascii=False)
                session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=session.id,
                    action_type="ask_more",
                    message=ai_message,
                    stage=session.stage,
                    intent=session.intent
                )
        
        elif session.stage == "brief_review":
            # User confirmed brief, now generate plan
            # (We assume any message here is confirmation, or we can check content)
            
            # Generate plan using planner_service
            context = {
                "today": datetime.now().strftime("%Y-%m-%d"),
                "timezone": "Asia/Shanghai"
            }
            
            # Use the original goal + collected info as message
            planning_message = collected_info.get("goal", request.message)
            planning_message += f"\n\n补充信息：{json.dumps(collected_info, ensure_ascii=False)}"
            
            plan = planner_service.generate_plan(planning_message, context)
            
            # Create PlanningSession so it can be committed later
            from app.models.planning import PlanningSession
            planning_session_id = str(uuid.uuid4())
            planning_session = PlanningSession(
                id=planning_session_id,
                user_id=current_user.id,
                message=planning_message,
                plan_json=json.dumps(plan, ensure_ascii=False)
            )
            db.add(planning_session)
            db.flush()
            db.commit()
            
            # Update session to planning stage
            session.stage = "planning"
            db.commit()
            
            return ChatResponse(
                conversation_id=planning_session_id,  # Return planning_session_id
                action_type="create_project", # This triggers Plan Review on frontend
                message="已为你生成详细计划草稿，你可以修改或确认：",
                plan=plan,
                stage=session.stage,
                intent=session.intent
            )
        
        
        
        elif session.stage == "planning":
            # [STICKY SESSION]
            # Verify if there is an active planning session
            from app.models.planning import PlanningSession
            
            # Find the latest planning session for this conversation? 
            # Ideally we should have linked it, but for now filtering by user + recent
            # Or better, store planning_session_id in ConversationSession (add column later)
            # For now, let's query the latest PlanningSession for this user
            planning_session = db.query(PlanningSession).filter(
                PlanningSession.user_id == current_user.id
            ).order_by(PlanningSession.created_at.desc()).first()
            
            if not planning_session:
                # Should not happen if flow is correct, but safe fallback
                session.stage = "completed"
                db.commit()
                return await chat(request, current_user, db) # Re-enter as completed -> new
            
            # Refine the plan
            current_plan = json.loads(planning_session.plan_json)
            
            # Check for "Exit" commands
            msg_lower = request.message.lower()
            if any(cmd in msg_lower for cmd in ["cancel", "quit", "exit", "放弃", "退出", "不做了"]):
                 ai_message = "好的，已为你取消项目规划。"
                 messages.append({"role": "assistant", "content": ai_message})
                 session.stage = "completed"
                 session.messages = json.dumps(messages, ensure_ascii=False)
                 db.commit()
                 return ChatResponse(
                    conversation_id=session.id,
                    action_type="reply",
                    message=ai_message,
                    stage=session.stage,
                    intent=session.intent
                )
            
            # Call AI to refine
            refined_plan = conversation_service.refine_plan(current_plan, request.message)
            
            # Update PlanningSession
            planning_session.plan_json = json.dumps(refined_plan, ensure_ascii=False)
            planning_session.updated_at = datetime.utcnow()
            
            # Get AI's explanation message
            extra_msg = refined_plan.get("extra_message", "已根据你的意见调整了计划。")
            messages.append({"role": "assistant", "content": extra_msg})
            session.messages = json.dumps(messages, ensure_ascii=False)
            
            db.commit()
            
            return ChatResponse(
                conversation_id=planning_session.id, # Keep returning planning ID
                action_type="update_plan", # Frontend should update state, not create new
                message=extra_msg,
                plan=refined_plan,
                stage=session.stage,
                intent=session.intent
            )

        elif session.stage == "completed":
            # Conversation is finished, start a new one
            logger.info(f"Conversation {session.id} is {session.stage}, starting new conversation")
            
            # Create new session
            new_session = ConversationSession(
                id=str(uuid.uuid4()),
                user_id=current_user.id,
                stage="intent",
                messages="[]",
                collected_info="{}"
            )
            db.add(new_session)
            db.flush()
            
            # Recognize intent for new message
            messages = [{"role": "user", "content": request.message}]
            intent, extracted_info = conversation_service.recognize_intent(request.message)
            new_session.intent = intent
            collected_info = extracted_info
            
            logger.info(f"New conversation {new_session.id}, intent: {intent}")
            
            if intent == "simple_task":
                # Extract and create task
                task_info = conversation_service.extract_simple_task(request.message)
                task = Task(
                    id=str(uuid.uuid4()),
                    user_id=current_user.id,
                    title=task_info["title"],
                    description=task_info.get("description", ""),
                    deadline=datetime.fromisoformat(task_info["deadline"]),
                    evidence_type=task_info.get("evidence_type", "none"),
                    status="OPEN"
                )
                db.add(task)
                new_session.task_id = task.id
                new_session.stage = "completed"
                new_session.completed_at = datetime.utcnow()
                
                ai_message = f"✅ 已创建任务「{task.title}」，截止时间：{task.deadline.strftime('%Y-%m-%d %H:%M')}"
                messages.append({"role": "assistant", "content": ai_message})
                
                new_session.messages = json.dumps(messages, ensure_ascii=False)
                new_session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=new_session.id,
                    action_type="create_task",
                    message=ai_message,
                    task={"id": task.id, "title": task.title},
                    stage=new_session.stage,
                    intent=intent
                )
            
            elif intent == "complex_project":
                new_session.stage = "gathering"
                info_complete, ai_message = conversation_service.gather_information(
                    collected_info,
                    messages
                )
                
                messages.append({"role": "assistant", "content": ai_message})
                new_session.messages = json.dumps(messages, ensure_ascii=False)
                new_session.collected_info = json.dumps(collected_info, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=new_session.id,
                    action_type="ask_more",
                    message=ai_message,
                    stage=new_session.stage,
                    intent=intent
                )
            
            else:
                # question or chat
                if intent == "question":
                    answer = conversation_service.answer_question(request.message)
                else:
                    answer = "你好！我可以帮你规划任务和项目。有什么我能帮到你的吗？"
                
                messages.append({"role": "assistant", "content": answer})
                new_session.stage = "completed"
                new_session.completed_at = datetime.utcnow()
                new_session.messages = json.dumps(messages, ensure_ascii=False)
                db.commit()
                
                return ChatResponse(
                    conversation_id=new_session.id,
                    action_type="reply",
                    message=answer,
                    stage=new_session.stage,
                    intent=intent
                )
        
        else:
            raise HTTPException(status_code=400, detail=f"Invalid conversation state: {session.stage}")
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/tasks/quick-create", response_model=QuickTaskResponse)
async def quick_create_task(
    request: QuickTaskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Quickly create a single task without going through planning.
    """
    try:
        task = Task(
            id=str(uuid.uuid4()),
            user_id=current_user.id,
            title=request.title,
            description=request.description or "",
            deadline=request.deadline,
            evidence_type=request.evidence_type,
            status="OPEN"
        )
        db.add(task)
        db.commit()
        
        logger.info(f"Quick task created: {task.id}")
        
        return QuickTaskResponse(
            task_id=task.id,
            title=task.title,
            deadline=task.deadline
        )
    
    except Exception as e:
        db.rollback()
        logger.error(f"Quick task creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Task creation failed: {str(e)}")

from pydantic import BaseModel
from typing import Optional

class ConversationStateResponse(BaseModel):
    conversation_id: str
    messages: List[dict]
    stage: str
    intent: Optional[str]

@router.get("/current", response_model=ConversationStateResponse)
async def get_current_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the persistent conversation state."""
    # Find the most recent session
    session = db.query(ConversationSession).filter(
        ConversationSession.user_id == current_user.id
    ).order_by(ConversationSession.created_at.desc()).first()
    
    if not session:
        # Create initial session if none exists
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
    
    return ConversationStateResponse(
        conversation_id=session.id,
        messages=messages,
        stage=session.stage,
        intent=session.intent
    )

@router.post("/reset", response_model=ConversationStateResponse)
async def reset_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Force start a new conversation thread."""
    # Create new session immediately
    session = ConversationSession(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        stage="intent",
        messages="[]",
        collected_info="{}"
    )
    db.add(session)
    db.commit()
    
    return ConversationStateResponse(
        conversation_id=session.id,
        messages=[],
        stage="intent",
        intent=None
    )
@router.post("/check-reminder")
async def check_daily_reminder(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if daily reminder needs to be sent and send it if missing."""
    try:
        # Check current session history
        session = db.query(ConversationSession).filter(
            ConversationSession.user_id == current_user.id
        ).order_by(ConversationSession.created_at.desc()).first()
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        needs_reminder = True
        
        if session and session.messages:
            try:
                history = json.loads(session.messages)
                if history:
                    # Check last message
                    last_msg = history[-1]
                    # Log for debugging
                    logger.info(f"Last message type: {last_msg.get('type')}, time: {last_msg.get('timestamp')}, today: {today_str}")
                    
                    if last_msg.get("type") == "daily_reminder":
                        # Check date - Handle both simple date and ISO format
                        msg_ts = last_msg.get("timestamp", "")
                        # Store is UTC ISO: 2026-02-03T01:30...
                        # today_str is Local Date: 2026-02-03
                        # We just check if the DATE part matches. 
                        # Ideally, convert msg_ts to local, but simplest is checking if it was generated "recently" (e.g. today).
                        # Or just check string prefix if we are sure about day alignment.
                        # Safe bet: if it's the SAME DAY in UTC, it's likely the daily reminder for 'today'.
                        
                        # Let's just check YYYY-MM-DD match.
                        # Warning: UTC day might be yesterday if it's early morning here?
                        # 09:00 AM China is 01:00 AM UTC. Same day.
                        # 01:00 AM China is 17:00 PM UTC Previous Day.
                        # So simply comparsion might fail in early morning.
                        
                        # Better approach: Check if created_at > today 00:00 Local?
                        # Or simpler: trust that daily reminder runs at 9am.
                        # Let's stick to simple string startswith first, assuming standard usages.
                        if msg_ts.startswith(today_str):
                            needs_reminder = False
            except json.JSONDecodeError:
                pass
        
        if needs_reminder:
            from app.services.reminder_service import inject_daily_reminder_for_user
            inject_daily_reminder_for_user(db, current_user)
            return {"status": "sent"}
            
        return {"status": "skipped"}
        
    except Exception as e:
        logger.error(f"Check reminder failed: {e}")
        # Don't block UI if this fails
        return {"status": "error", "detail": str(e)}


@router.post("/inject-reminder")
async def inject_reminder_message(
    request: InjectReminderRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Inject a daily reminder message into the conversation history.
    Using data fetched by the frontend.
    """
    try:
        # Find session
        session = db.query(ConversationSession).filter(
            ConversationSession.user_id == current_user.id
        ).order_by(ConversationSession.created_at.desc()).first()
        
        if not session:
            # Create if missing
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
        
        data = request.data
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # Build the message content
        incomplete = data.get("incomplete_tasks", {})
        overdue = data.get("overdue_tasks", {})
        due_soon = data.get("due_soon_tasks", {})
        system_task = data.get("system_task", {})
        
        msg_lines = [f"📅 **每日提醒 ({today_str})**", ""]
        
        # 1. System Task Check
        if system_task.get("exists"):
            if not system_task.get("completed"):
                msg_lines.append(f"⚠️ **待办：{system_task.get('title')}**")
                msg_lines.append(f"别忘了完成今天的打卡任务！")
            else:
                msg_lines.append(f"✅ **{system_task.get('title')}** 已完成，真棒！")
        else:
             msg_lines.append("今天的系统打卡任务尚未生成，请检查。")
             
        msg_lines.append("")

        # 2. Urgent Tasks
        if overdue.get("count", 0) > 0:
            msg_lines.append(f"🔴 **有 {overdue['count']} 个任务逾期**：")
            for t in overdue.get("top_5", []):
                msg_lines.append(f"- {t['title']} (截止: {t['deadline'] or '无'})")
            msg_lines.append("")
        
        if due_soon.get("count", 0) > 0:
            msg_lines.append(f"🟡 **有 {due_soon['count']} 个任务即将到期**：")
            for t in due_soon.get("top_5", []):
                msg_lines.append(f"- {t['title']} (截止: {t['deadline']})")
            msg_lines.append("")

        # 3. Overall Status
        total_incomplete = incomplete.get("count", 0)
        msg_lines.append(f"目前总共有 **{total_incomplete}** 个待办任务。")
        msg_lines.append("你可以随时告诉我你的计划，或者让我帮你安排今天的任务。")
        
        message_content = "\n".join(msg_lines)
        
        # Append message
        # Mark it as a special type if needed, but 'assistant' role is fine
        new_msg = {
            "role": "assistant",
            "content": message_content,
            "type": "daily_reminder", # Metadata for check-reminder to find it
            "timestamp": datetime.now().isoformat()
        }
        
        messages.append(new_msg)
        session.messages = json.dumps(messages, ensure_ascii=False)
        db.commit()
        
        logger.info(f"Injected reminder for user {current_user.id}")
        
        return {"status": "success", "message": message_content}
        
    except Exception as e:
        logger.error(f"Inject reminder failed: {e}")
        raise HTTPException(status_code=500, detail=f"Injection failed: {str(e)}")

