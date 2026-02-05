"""Qwen API client using OpenAI SDK compatibility."""
import logging
from typing import Optional, List, Dict, Any
from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class QwenClient:
    """Qwen API client wrapper."""
    
    def __init__(self):
        """Initialize Qwen client."""
        if not settings.qwen_api_key:
            raise ValueError("QWEN_API_KEY is not configured")
        
        self.client = OpenAI(
            api_key=settings.qwen_api_key,
            base_url=settings.qwen_base_url
        )
        self.model = settings.qwen_model
        logger.info(f"Qwen client initialized with model: {self.model}")
    
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text using Qwen API.
        
        Args:
            prompt: The text prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text content
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            
            content = response.choices[0].message.content
            logger.info(f"Qwen API call successful, generated {len(content)} chars")
            logger.info(f"Qwen raw response: {repr(content)}")  # DEBUG: Show exact response
            return content
            
        except Exception as e:
            logger.error(f"Qwen API error: {e}")
            raise
    
    def generate_with_image(
        self,
        prompt: str,
        image_url: str,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """
        Generate text with image input (multi-modal).
        
        Args:
            prompt: The text prompt
            image_url: URL or base64 encoded image
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text content
        """
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
            
            response = self.client.chat.completions.create(
                model="qwen-vl-max",  # Force VL model for images
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            content = response.choices[0].message.content
            logger.info(f"Qwen vision API call successful")
            return content
            
        except Exception as e:
            logger.error(f"Qwen vision API error: {e}")
            raise


# Singleton instance
qwen_client: Optional[QwenClient] = None

def get_qwen_client() -> QwenClient:
    """Get or create Qwen client singleton."""
    global qwen_client
    if qwen_client is None:
        qwen_client = QwenClient()
    return qwen_client
