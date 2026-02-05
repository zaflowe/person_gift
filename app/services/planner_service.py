"""Planner service for AI-powered task planning."""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

from app.config import settings

logger = logging.getLogger(__name__)


# Prompt for Gemini to generate structured plans
PLAN_SYSTEM_PROMPT = """你是一个任务规划助手。用户会告诉你一个目标或想法，你需要：
1. 生成一个 Project（项目）
2. 将项目拆分为多个 Task（任务），每个任务都要有明确的截止时间
3. 输出必须是**有效的 JSON 格式**，不要有任何额外文字

输出格式示例：
{
  "project": {
    "title": "项目名称（简短）",
    "description": "项目描述（1-2句话）"
  },
  "tasks": [
    {
      "title": "任务名称",
      "description": "任务描述（可选）",
      "due_at": "2026-02-15T23:59:59+08:00",
      "evidence_type": "none"
    }
  ],
  "rationale": "为什么这样规划（1句话）"
}

规则：
- 所有文本用中文
- Task 截止时间必须合理分布（不要都在同一天）
- 默认生成 3-7 个任务（最小闭环）
- due_at 格式：ISO 8601 with timezone (例如: 2026-02-15T23:59:59+08:00)
- evidence_type 可选值：none, text, number, image
- 任务要具体可执行，避免空话
"""


class PlannerService:
    """AI-powered task planner service."""
    
    def __init__(self):
        """Initialize planner service."""
        # Use the shared AI service with auto-switching
        from app.services.ai_service import ai_service
        self.ai_service = ai_service
        self.mock_mode = ai_service.mock_mode
        
        logger.info("Planner service initialized using AIService with auto-switching")
    
    def generate_plan(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a structured plan based on user message.
        
        Args:
            message: User's natural language input
            context: Optional context (timezone, today, etc.)
        
        Returns:
            Dict with project and tasks structure
        
        Raises:
            ValueError: If plan generation or validation fails
        """
        if self.mock_mode:
            return self._generate_mock_plan(message, context)
        
        # Prepare context
        ctx = context or {}
        timezone = ctx.get("timezone", "Asia/Shanghai")
        today = ctx.get("today", datetime.now().strftime("%Y-%m-%d"))
        
        # Construct user prompt
        user_prompt = f"""用户输入：{message}

当前日期：{today}
时区：{timezone}

请生成任务计划（JSON 格式）。"""
        
        # Combine system prompt and user prompt
        full_prompt = PLAN_SYSTEM_PROMPT + "\n\n" + user_prompt
        
        # Try to generate plan with retry
        for attempt in range(2):
            try:
                logger.info(f"Generating plan (attempt {attempt + 1}/2) for: {message[:50]}...")
                
                # Call AI with auto-switching
                response_text = self.ai_service._call_ai(full_prompt)
                logger.debug(f"AI response: {response_text[:200]}...")
                
                # Try to extract JSON from response
                plan = self._extract_and_parse_json(response_text)
                
                # Validate plan structure
                self._validate_plan(plan)
                
                logger.info("Plan generated and validated successfully")
                return plan
            
            except json.JSONDecodeError as e:
                logger.warning(f"JSON parsing failed (attempt {attempt + 1}): {str(e)}")
                
                if attempt == 0:
                    # Retry with explicit format request
                    user_prompt = f"""上次输出格式错误，请严格按照 JSON 格式返回，不要有任何额外文字：

原始需求：{message}
当前日期：{today}
时区：{timezone}

请返回有效的 JSON。"""
                    full_prompt = PLAN_SYSTEM_PROMPT + "\n\n" + user_prompt
                    continue
                else:
                    raise ValueError(f"AI 返回的内容无法解析为 JSON: {str(e)}")
            
            except Exception as e:
                logger.error(f"Plan generation failed: {str(e)}")
                # If it's a rate limit error and we have mock mode, fall back
                if "429" in str(e) or "quota" in str(e).lower():
                    logger.warning("AI quota exceeded, falling back to mock plan")
                    return self._generate_mock_plan(message, context)
                raise
        
        raise ValueError("Plan generation failed after 2 attempts")
    
    def _extract_and_parse_json(self, text: str) -> Dict[str, Any]:
        """
        Extract and parse JSON from text.
        
        Handles cases where AI returns JSON wrapped in markdown code blocks.
        """
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Parse JSON
        return json.loads(text)
    
    def _validate_plan(self, plan: Dict[str, Any]) -> None:
        """
        Validate plan structure.
        
        Raises:
            ValueError: If plan is invalid
        """
        # Check required keys
        if "project" not in plan:
            raise ValueError("Plan must contain 'project' key")
        if "tasks" not in plan:
            raise ValueError("Plan must contain 'tasks' key")
        
        # Validate project
        project = plan["project"]
        if not isinstance(project, dict):
            raise ValueError("'project' must be a dictionary")
        if "title" not in project or not project["title"]:
            raise ValueError("Project must have a non-empty 'title'")
        
        # Validate tasks
        tasks = plan["tasks"]
        if not isinstance(tasks, list):
            raise ValueError("'tasks' must be an array")
        if len(tasks) == 0:
            raise ValueError("At least one task is required")
        
        # Validate each task
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                raise ValueError(f"Task {i} must be a dictionary")
            if "title" not in task or not task["title"]:
                raise ValueError(f"Task {i} must have a non-empty 'title'")
            if "due_at" not in task or not task["due_at"]:
                raise ValueError(f"Task {i} must have a 'due_at' field")
            
            # Validate evidence_type if present
            if "evidence_type" in task:
                valid_types = ["none", "text", "number", "image"]
                if task["evidence_type"] not in valid_types:
                    task["evidence_type"] = "none"
        
        logger.debug("Plan structure validated successfully")
    
    def _generate_mock_plan(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate a mock plan for testing."""
        logger.info(f"Generating MOCK plan for: {message[:50]}...")
        
        ctx = context or {}
        today = ctx.get("today", datetime.now().strftime("%Y-%m-%d"))
        today_dt = datetime.fromisoformat(today)
        
        # Simple mock plan
        return {
            "project": {
                "title": f"完成「{message[:20]}」",
                "description": "AI 生成的示例计划（Mock Mode）"
            },
            "tasks": [
                {
                    "title": "第一步：准备阶段",
                    "description": "收集资料，制定详细计划",
                    "due_at": (today_dt + timedelta(days=7)).isoformat() + "+08:00",
                    "evidence_type": "text"
                },
                {
                    "title": "第二步：执行阶段",
                    "description": "按计划推进核心工作",
                    "due_at": (today_dt + timedelta(days=14)).isoformat() + "+08:00",
                    "evidence_type": "text"
                },
                {
                    "title": "第三步：总结复盘",
                    "description": "整理成果，进行总结",
                    "due_at": (today_dt + timedelta(days=21)).isoformat() + "+08:00",
                    "evidence_type": "text"
                }
            ],
            "rationale": "这是一个 3 周的示例计划，包含准备、执行、总结三个阶段。"
        }


# Global instance
planner_service = PlannerService()
