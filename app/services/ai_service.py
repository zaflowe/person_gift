"""AI service with multi-provider support (Gemini + Qwen)."""
import json
import logging
from typing import Dict, Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI service with auto-switching between Gemini and Qwen."""
    
    def __init__(self):
        """Initialize AI service with configured provider."""
        self.mock_mode = settings.gemini_mock_mode
        self.provider = settings.ai_provider  # auto | gemini | qwen
        
        # Initialize Gemini
        self.gemini_available = False
        if settings.gemini_api_key and not self.mock_mode:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('models/gemini-2.0-flash-exp')
                self.gemini_available = True
                logger.info("✅ Gemini API initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Gemini API initialization failed: {e}")
        
        # Initialize Qwen
        self.qwen_available = False
        if settings.qwen_api_key:
            try:
                from app.services.qwen_client import get_qwen_client
                self.qwen_client = get_qwen_client()
                self.qwen_available = True
                logger.info("✅ Qwen API initialized successfully")
            except Exception as e:
                logger.warning(f"⚠️ Qwen API initialization failed: {e}")
        
        # Determine active provider
        if self.mock_mode:
            logger.warning("🤖 AI Service running in MOCK MODE")
        elif not self.gemini_available and not self.qwen_available:
            logger.warning("⚠️ No AI providers available, falling back to MOCK MODE")
            self.mock_mode = True
        else:
            available = []
            if self.gemini_available:
                available.append("Gemini")
            if self.qwen_available:
                available.append("Qwen")
            logger.info(f"🚀 AI Service ready with providers: {', '.join(available)}")
    
    def _call_ai(self, prompt: str, image_path: Optional[str] = None) -> str:
        """
        Call AI with automatic provider switching.
        
        Tries providers in this order based on configuration:
        - auto: Gemini first, then Qwen fallback
        - gemini: Only Gemini (fail if unavailable)
        - qwen: Only Qwen (fail if unavailable)
        """
        if self.mock_mode:
            return ""  # Mock mode handled separately
        
        providers_to_try = []
        
        if self.provider == "gemini":
            providers_to_try = ["gemini"]
        elif self.provider == "qwen":
            providers_to_try = ["qwen"]
        else:  # auto
            if self.gemini_available:
                providers_to_try.append("gemini")
            if self.qwen_available:
                providers_to_try.append("qwen")
        
        last_error = None
        
        for provider_name in providers_to_try:
            try:
                if provider_name == "gemini" and self.gemini_available:
                    logger.info("🔵 Calling Gemini API...")
                    if image_path:
                        from PIL import Image
                        img = Image.open(image_path)
                        response = self.gemini_model.generate_content([prompt, img])
                    else:
                        response = self.gemini_model.generate_content(prompt)
                    return response.text.strip()
                
                elif provider_name == "qwen" and self.qwen_available:
                    logger.info("🟠 Calling Qwen API...")
                    if image_path:
                        # Convert image to base64 for Qwen
                        import base64
                        with open(image_path, "rb") as img_file:
                            img_base64 = base64.b64encode(img_file.read()).decode()
                        image_url = f"data:image/jpeg;base64,{img_base64}"
                        return self.qwen_client.generate_with_image(prompt, image_url)
                    else:
                        return self.qwen_client.generate_text(prompt)
                
            except Exception as e:
                error_str = str(e)
                logger.warning(f"⚠️ {provider_name.capitalize()} API failed: {error_str}")
                last_error = e
                
                # Check if it's a rate limit error
                if "429" in error_str or "quota" in error_str.lower() or "rate" in error_str.lower():
                    logger.warning(f"🔄 {provider_name.capitalize()} rate limited, trying next provider...")
                    continue
                
                # For other errors, also try next provider if available
                if len(providers_to_try) > 1:
                    logger.warning(f"🔄 Trying next provider...")
                    continue
                else:
                    raise
        
        # All providers failed
        if last_error:
            raise last_error
        else:
            raise RuntimeError("No AI providers available")
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Extract JSON from AI response with robust error handling."""
        original_text = text
        text = text.strip()
        
        # Remove markdown code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        # Try to find JSON object in the text
        start = text.find('{')
        end = text.rfind('}')
        
        if start != -1 and end != -1 and end > start:
            text = text[start:end+1]
        
        # Try multiple parsing strategies
        strategies = [
            # Strategy 1: Direct parse
            lambda t: json.loads(t),
            
            # Strategy 2: Remove trailing commas (common AI mistake)
            lambda t: json.loads(t.replace(',}', '}').replace(',]', ']')),
            
            # Strategy 3: Fix common newline issues
            lambda t: json.loads(' '.join(t.split())),
            
            # Strategy 4: Remove all newlines and extra whitespace
            lambda t: json.loads(t.replace('\n', ' ').replace('\r', ' ')),

            # Strategy 5: Add missing braces if they seem to be missing (naked JSON body)
            lambda t: json.loads('{' + t + '}') if not t.strip().startswith('{') else json.loads(t),
            
            # Strategy 6: Naked Body + Trailing Comma (e.g. "title": "foo",)
            lambda t: json.loads('{' + t.strip().rstrip(',') + '}') if not t.strip().startswith('{') else json.loads(t),
        ]
        
        for i, strategy in enumerate(strategies):
            try:
                result = strategy(text)
                if i > 0:
                    logger.warning(f"JSON parsed with strategy {i+1}")
                return result
            except (json.JSONDecodeError, ValueError):
                continue
        
        # All strategies failed - log and raise
        logger.error(f"All JSON parse strategies failed.")
        logger.error(f"Original text (full): {original_text}")
        logger.error(f"Cleaned text (full): {text}")
        logger.error(f"Text length: {len(text)}")
        raise ValueError(f"Invalid JSON from AI. First chars: '{text[:50]}'...")
    
    async def judge_evidence(
        self,
        task_title: str,
        evidence_type: str,
        evidence_criteria: str,
        evidence_content: Optional[str] = None,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Judge task evidence using AI (Gemini or Qwen with auto-fallback).
        
        Returns:
            {
                "result": "pass" | "fail",
                "reason": str,
                "extracted_values": dict (optional)
            }
        """
        if self.mock_mode:
            return self._mock_judge_evidence(task_title, evidence_type, evidence_content)
        
        try:
            # Construct prompt
            prompt = f"""You are a strict task completion judge. Your role is to verify if the submitted evidence meets the criteria.

Task: {task_title}
Evidence Type: {evidence_type}
Criteria: {evidence_criteria}

"""
            if evidence_type == "text":
                prompt += f"Submitted Text: {evidence_content}\n"
            elif evidence_type == "number":
                prompt += f"Submitted Value: {evidence_content}\n"
            elif evidence_type == "image":
                prompt += "An image has been submitted.\n"
            
            prompt += """
Please analyze if the evidence meets the criteria. Respond in JSON format:
{
    "result": "pass" or "fail",
    "reason": "brief explanation",
    "extracted_values": {} (optional, for extracting metrics like weight, duration, etc.)
}
"""
            
            # Call AI with auto-switching
            result_text = self._call_ai(prompt, image_path)
            result = self._extract_json(result_text)
            return result
            
        except Exception as e:
            logger.error(f"Error in judge_evidence: {e}")
            return {
                "result": "fail",
                "reason": f"AI判定出错: {str(e)}",
                "extracted_values": {}
            }
    
    def _mock_judge_evidence(
        self,
        task_title: str,
        evidence_type: str,
        evidence_content: Optional[str]
    ) -> Dict[str, Any]:
        """Mock evidence judging for testing."""
        logger.info(f"[MOCK] Judging evidence for task '{task_title}'")
        
        # Simple mock logic: pass if evidence_content length > 5
        if evidence_type in ["text", "number"]:
            passed = evidence_content and len(str(evidence_content)) > 5
        else:
            passed = True  # Always pass for images in mock mode
        
        return {
            "result": "pass" if passed else "fail",
            "reason": "Mock AI判定: 证据符合标准" if passed else "Mock AI判定: 证据不足",
            "extracted_values": {}
        }
    
    async def analyze_project(
        self,
        title: str,
        description: str,
        success_criteria: Optional[str],
        failure_criteria: Optional[str]
    ) -> Dict[str, Any]:
        """
        Analyze project and suggest breakdown.
        
        Returns:
            {
                "analysis": str,
                "suggested_milestones": [
                    {"title": str, "description": str, "is_critical": bool}
                ],
                "confidence": float
            }
        """
        if self.mock_mode:
            return self._mock_analyze_project(title, description)
        
        try:
            prompt = f"""You are a project planning assistant. Analyze the following project and suggest a breakdown.

Project Title: {title}
Description: {description}
Success Criteria: {success_criteria or "Not specified"}
Failure Criteria: {failure_criteria or "Not specified"}

Please analyze this project and suggest:
1. Key milestones needed to achieve this goal
2. Which milestones are critical (failure to achieve them means project failure)
3. Realistic timeline considerations

Respond in JSON format:
{{
    "analysis": "overall analysis and recommendations",
    "suggested_milestones": [
        {{"title": "milestone name", "description": "details", "is_critical": true/false}}
    ],
    "confidence": 0.0-1.0
}}
"""
            
            result_text = self._call_ai(prompt)
            result = self._extract_json(result_text)
            return result
            
        except Exception as e:
            logger.error(f"Error in analyze_project: {e}")
            return self._mock_analyze_project(title, description)
    
    def _mock_analyze_project(self, title: str, description: str) -> Dict[str, Any]:
        """Mock project analysis."""
        logger.info(f"[MOCK] Analyzing project '{title}'")
        return {
            "analysis": f"Mock分析: 项目 '{title}' 需要分阶段实施，建议设置清晰的里程碑。",
            "suggested_milestones": [
                {
                    "title": "阶段一：准备工作",
                    "description": "完成前期调研和资源准备",
                    "is_critical": False
                },
                {
                    "title": "阶段二：核心实施",
                    "description": "完成项目核心目标",
                    "is_critical": True
                },
                {
                    "title": "阶段三：验收确认",
                    "description": "验证成果是否符合预期",
                    "is_critical": True
                }
            ],
            "confidence": 0.7
        }

    async def estimate_bodyfat(
        self,
        image_path: str,
        user_info: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate body fat from image.
        
        Returns:
            {
                "estimated_bodyfat": float,
                "confidence": float,
                "analysis": str
            }
        """
        if self.mock_mode:
            return self._mock_estimate_bodyfat()
        
        try:
            prompt = f"""You are a fitness expert. Estimate the body fat percentage of the person in this image.
User Info (if available): {user_info or "Not provided"}

Please provide a conservative estimate based on visual markers (definition, vascularity, etc.).
Respond in JSON format:
{{
    "estimated_bodyfat": 15.5,
    "confidence": 0.8,
    "analysis": "Brief analysis of why you estimated this value."
}}
"""
            
            
            # Use unified AI call handling
            result_text = self._call_ai(prompt, image_path)
            result_text = result_text.strip()
            
            # Try to extract JSON
            if "```json" in result_text:
                json_start = result_text.index("```json") + 7
                json_end = result_text.index("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            
            result = json.loads(result_text)
            return result
        except Exception as e:
            logger.error(f"Error in estimate_bodyfat: {e}")
            return self._mock_estimate_bodyfat()

    def _mock_estimate_bodyfat(self) -> Dict[str, Any]:
        """Mock body fat estimation."""
        logger.info("[MOCK] Estimating body fat")
        return {
            "estimated_bodyfat": 20.0,
            "confidence": 0.6,
            "analysis": "Mock估算: 基于视觉特征推测体脂约为 20%。"
        }


# Singleton instance
ai_service = AIService()
