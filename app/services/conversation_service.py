"""Conversation service for intelligent multi-turn planning."""
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union

from app.config import settings

logger = logging.getLogger(__name__)


# System prompts for different stages
# System prompts with "Yan Yan" Persona

YAN_YAN_CORE_IDENTITY = """你叫"研言" (Yan Yan)，一位顶级的"人类工程师"。
你的核心理念：人生成长就像驾驶一艘船，你需要辅助用户通过结构化的数据和清晰的规划来掌控方向。

**人设特征**：
- **阶段**：沉稳的中年专家，兼具年轻时的阳光活力。
- **风格**：高情商、逻辑严密、结构化思维、引导式沟通。
- **原则**：
  1. **不盲从**：如果用户的想法不切实际，婉转提出挑战和建议。
  2. **门控机制**：信息不足时绝不瞎编计划。
  3. **草稿意识**：始终强调你生成的是"建议"或"草稿"，决定权在用户。
"""

INTENT_RECOGNITION_PROMPT = f"""{YAN_YAN_CORE_IDENTITY}
用户向你发送消息，请识别其意图。

**意图分类**：
1. **simple_task** - 简单待办：**创建新的**待办事项，如"明天7点健身" (注意："查看"、"查询"不是创建任务)。
2. **complex_project** - 项目规划：大目标或模糊想法，如"想学微积分"、"减肥"。
3. **view_schedule** - 查看日程：用户想看**已有的**安排，关键词：日程、安排、今天做什么、查看。
4. **question** - 咨询建议：询问方法论或寻求建议。
5. **chat** - 闲聊：不涉及具体工作的社交。

请返回 JSON 格式：
{{
  "intent": "simple_task|complex_project|view_schedule|question|chat",
  "confidence": 0.0-1.0,
  "extracted_info": {{
    "goal": "...",
    "deadline": "..."
  }}
}}
"""


INFORMATION_GATHERING_PROMPT = f"""{YAN_YAN_CORE_IDENTITY}
用户想要规划一个项目，请作为"人类工程师"进行诊断。

已知信息：
{{collected_info}}

**你需要确认的关键要素**（如果缺失则追问）：
1. **终极目标** (Goal)：做成什么样的具体结果？
2. **截止时间** (Deadline)：什么时候必须完成？
3. **资源投入** (Inputs)：每天能花多少时间？有什么基础？
4. **动机验证** (Why)：为什么现在做？(挖掘深层动力)

**返回规则**：
- 只要核心目标 (Goal) 和大概的时间预期明确，或者用户表现出想尽快开始的意愿，**请立即返回 "info_complete": true**。
- 不要追求完美的信息收集。草稿可以在生成后由用户调整。
- 只有在信息极度匮乏（如只说了"我想学习"）时才追问。最多追问 2 轮。

返回 JSON 格式：
{{{{
  "info_complete": true/false,
  "questions": ["问题1", "问题2"],
  "message": "自然流畅的回复文本，体现你的专业引导风格"
}}}}
"""

SIMPLE_TASK_EXTRACTION_PROMPT = f"""{YAN_YAN_CORE_IDENTITY}
用户想创建一个简单任务，请提取关键要素生成"任务草稿"。

用户消息：{{message}}
当前时间：{{current_time}}

请返回 JSON 格式（只返回JSON）：
{{{{
  "title": "任务标题（动宾结构，简洁有力）",
  "description": "补充说明（可选）",
  "deadline": "YYYY-MM-DDTHH:MM:SS",
  "evidence_type": "none"
}}}}

**时间解析规则（精确到分钟）**：
- "两点" -> 今天14:00
- "明天7点" -> 明天07:00
- 默认时间：23:59:59
"""

QUESTION_ANSWER_PROMPT = f"""{YAN_YAN_CORE_IDENTITY}
用户正在咨询问题。请给出简练、本质的回答。

**回答要求**：
- 一针见血：直击问题本质。
- 结构化：如果内容多，使用1/2/3条理列出。
- 鼓励行动：结尾给出一个立即能做的小建议。

用户问题：{{message}}
"""

PLAN_REFINEMENT_PROMPT = f"""{YAN_YAN_CORE_IDENTITY}
用户正在审阅你生成的项目计划草稿，并提出了修改意见。
请根据用户的反馈，对 **原计划** 进行调整。

原计划 JSON：
{{current_plan}}

用户反馈/指令：
{{message}}

**调整规则**：
1. **精准修改**：按用户要求增删改任务、调整时间或标题。
2. **保持完整**：返回修改后的 **完整** 项目计划 JSON。
3. **结构严谨**：保持与原计划相同的 JSON 结构。
4. **意图判断**：如果用户是在闲聊或询问无关问题（如"天气怎样"），请忽略修改，原样返回原计划，并在 extra_message 中说明。

请返回 JSON 格式：
{{{{
  "project_title": "...",
  "description": "...",
  "tasks": [
     {{{{
        "title": "...",
        "description": "...",
        "deadline": "YYYY-MM-DDTHH:MM:SS",
        "evidence_type": "text/image/number/none"
     }}}}
  ],
  "extra_message": "（可选）对修改的解释，或者对无效指令的回复"
}}}}
"""


class ConversationService:
    """Intelligent conversation service for multi-turn planning."""
    
    def __init__(self):
        """Initialize conversation service."""
        # Import the shared AI service logic or create similar one
        # For simplicity, we'll reuse the same pattern as AIService
        from app.services.ai_service import ai_service
        self.ai_service = ai_service
        self.mock_mode = ai_service.mock_mode
        
        logger.info("Conversation service initialized using AIService")
    
    def _call_ai(self, prompt: str) -> str:
        """Call AI using the shared ai_service _call_ai method."""
        if self.mock_mode:
            return ""
        return self.ai_service._call_ai(prompt)
    
    def recognize_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Recognize user intent from message.
        
        Returns:
            (intent, extracted_info)
        """
        if self.mock_mode:
            return self._mock_recognize_intent(message)
        
        # Heuristic Override for Scheduling (Stability fix)
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["日程", "安排"]) and any(w in msg_lower for w in ["查看", "查询", "看下", "有", "什么"]):
             logger.info("Intent heuristic override: view_schedule")
             return "view_schedule", {}

        try:
            prompt = f"{INTENT_RECOGNITION_PROMPT}\n\n用户消息：{message}"
            response_text = self._call_ai(prompt)
            result = self.ai_service._extract_json(response_text)
            
            intent = result.get("intent", "chat")
            extracted_info = result.get("extracted_info", {})
            
            logger.info(f"Intent recognized: {intent}")
            return intent, extracted_info
        
        except Exception as e:
            logger.error(f"Intent recognition failed: {e}")
            return "chat", {}
    
    def gather_information(
        self,
        collected_info: Dict[str, Any],
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[bool, str]:
        """
        Check if we have enough information, or ask more questions.
        
        Returns:
            (info_complete, ai_message)
        """
        if self.mock_mode:
            return self._mock_gather_information(collected_info)
        
        try:
            prompt = INFORMATION_GATHERING_PROMPT.format(
                collected_info=json.dumps(collected_info, ensure_ascii=False, indent=2)
            )
            
            # Add conversation history
            prompt += "\n\n对话历史：\n"
            for msg in conversation_history[-4:]:  # Last 4 messages
                prompt += f"{msg['role']}: {msg['content']}\n"
            
            response_text = self._call_ai(prompt)
            result = self.ai_service._extract_json(response_text)
            
            info_complete = result.get("info_complete", False)
            message = result.get("message", "请告诉我更多信息。")
            
            return info_complete, message
        
        except Exception as e:
            logger.error(f"Information gathering failed: {e}")
            return True, "好的，让我开始规划。"
    
    def extract_simple_task(self, message: str) -> Dict[str, Any]:
        """Extract task information from message."""
        if self.mock_mode:
            return self._mock_extract_simple_task(message)
        
        try:
            current_time = datetime.now().isoformat()
            prompt = SIMPLE_TASK_EXTRACTION_PROMPT.format(
                message=message,
                current_time=current_time
            )
            
            
            response_text = self._call_ai(prompt)
            logger.info(f"[DEBUG] Qwen response for task extraction: {repr(response_text)}")
            task_info = self.ai_service._extract_json(response_text)
            
            return task_info
        
        except Exception as e:
            logger.error(f"Task extraction failed: {e}")
            raise ValueError(f"无法提取任务信息: {str(e)}")
    
    def answer_question(self, message: str) -> str:
        """Answer a user question."""
        if self.mock_mode:
            # Better mock responses
            msg = message.lower()
            if "几点" in msg or "时间" in msg:
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
                return f"现在是 {now_str}"
            
            if "弱智" in msg or "笨" in msg or "傻" in msg:
                 return "抱歉，我现在处于离线模式 (Mock Mode)，能力有限。请配置 GEMINI_API_KEY 以解锁完整智能。"
            
            return f"这是一个很好的问题！作为离线助手，建议您：保持专注，制定计划。您可以尝试说'明天7点起床'来创建任务。"
        
        try:
            prompt = QUESTION_ANSWER_PROMPT.format(message=message)
            response_text = self._call_ai(prompt)
            return response_text.strip()
        
        except Exception as e:
            logger.error(f"Question answering failed: {e}")
            return "抱歉，我暂时无法回答这个问题。"
    
    def refine_plan(self, current_plan: Dict[str, Any], message: str) -> Dict[str, Any]:
        """Refine an existing plan based on user message."""
        if self.mock_mode:
            # Simple mock: append message to description to show change
            import copy
            new_plan = copy.deepcopy(current_plan)
            # new_plan["description"] += f" [Refined: {message}]"
            # Instead of modifying description, let's just pretend we processed it
            # In a real mock, we might parse "add task" etc.
            # For now, just return valid structure with message
            return {
                "project_title": new_plan.get("project_title", "Project"),
                "description": new_plan.get("description", ""),
                "tasks": new_plan.get("tasks", []),
                "extra_message": f"Mock: 已收到修改意见 '{message}'，但 Mock 模式不支持复杂逻辑修改。"
            }
            
        try:
            prompt = PLAN_REFINEMENT_PROMPT.format(
                current_plan=json.dumps(current_plan, ensure_ascii=False, indent=2),
                message=message
            )
            
            response_text = self._call_ai(prompt)
            result = self.ai_service._extract_json(response_text)
            return result
            
        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            # Fallback: Return original plan with error message
            current_plan["extra_message"] = f"抱歉，调整计划时出错: {str(e)}"
            return current_plan
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from AI response using centralized ai_service logic."""
        return self.ai_service._extract_json(text)

    
    # Mock implementations
    def _mock_recognize_intent(self, message: str) -> Tuple[str, Dict[str, Any]]:
        """Mock intent recognition."""
        msg_lower = message.lower()
        
        # Schedule queries - Priority Check
        if any(word in msg_lower for word in ["日程", "安排", "计划表", "schedule", "查看今天", "今日安排"]):
            return "view_schedule", {}
        
        # Simple heuristics
        if any(word in msg_lower for word in ["明天", "今天", "今晚", "下周", "起床", "健身", "交报告", "吃饭", "跑步", "开会"]):
             # If it looks like a task (has time or action)
            if len(message) < 30 and ("学" not in msg_lower or "完" not in msg_lower):
                return "simple_task", {"goal": message}
        
        if any(word in msg_lower for word in ["学完", "准备", "考研", "减肥", "个月", "计划", "项目"]):
            return "complex_project", {"goal": message}
        
        # Explicit questions
        if any(word in msg_lower for word in ["怎么", "如何", "什么", "为什么", "?", "？", "几点", "时间"]):
            return "question", {}
            
        # Greetings/Chat
        if any(word in msg_lower for word in ["你好", "谢谢", "再见", "弱智", "笨", "傻"]):
             return "chat", {}
        
        # Default fallback
        if len(message) > 10:
             return "question", {} # Treat long unknown messages as questions
             
        return "chat", {}
    
    def _mock_gather_information(self, collected_info: Dict[str, Any]) -> Tuple[bool, str]:
        """Mock information gathering."""
        needed = []
        
        if "deadline" not in collected_info:
            needed.append("期望多久完成？")
        if "daily_time" not in collected_info:
            needed.append("每天能投入多少时间？")
        
        if not needed:
            return True, "好的，信息已经足够，让我帮你生成计划。"
        
        message = "好的！为了帮你制定合理的计划，我需要了解：\n"
        for i, q in enumerate(needed, 1):
            message += f"{i}. {q}\n"
        
        return False, message.strip()
    
    def _mock_extract_simple_task(self, message: str) -> Dict[str, Any]:
        """Mock task extraction."""
        from datetime import timedelta
        import re
        
        # Default to tomorrow 09:00 if no time found
        deadline = datetime.now() + timedelta(days=1)
        deadline = deadline.replace(hour=9, minute=0, second=0, microsecond=0)
        
        # Regex for Time: (Hour)(点/./:|：)(Minute)?(分)?
        time_pattern = re.search(r'(\d+|[一二三四五六七八九十两]+)(?:点|:|：)(\d+|[一二三四五六七八九十零]+|半)?(?:分)?', message)
        
        if time_pattern:
            cn_num = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, 
                      '六': 6, '七': 7, '八': 8, '九': 9, '十': 10, '零': 0, '两':2}
            
            def parse_cn_number(text):
                if not text: return 0
                if text.isdigit(): return int(text)
                if text == '半': return 30
                
                val = 0
                if '十' in text:
                    parts = text.split('十')
                    if parts[0]: val += cn_num.get(parts[0], 0) * 10
                    else: val += 10
                    if len(parts) > 1 and parts[1]: val += cn_num.get(parts[1], 0)
                else:
                    val = cn_num.get(text, 0)
                return val

            h_str = time_pattern.group(1)
            m_str = time_pattern.group(2)
            
            hour = parse_cn_number(h_str)
            minute = parse_cn_number(m_str)
            
            if 0 <= hour <= 24 and 0 <= minute < 60:
                deadline = deadline.replace(hour=hour, minute=minute)
        
        return {
            "title": message[:50] if len(message) <= 50 else message[:47] + "...",
            "description": "",
            "deadline": deadline.strftime("%Y-%m-%dT%H:%M:%S"),
            "evidence_type": "none"
        }


# Global instance
conversation_service = ConversationService()
