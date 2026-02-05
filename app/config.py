"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    database_url: str = "sqlite:///./data/person_gift.db"
    gemini_api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7  # 7 days
    timezone: str = "Asia/Taipei"
    
    # Gemini mock mode (for testing without API key)
    gemini_mock_mode: bool = False
    
    # Qwen (通义千问) configuration
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    
    # AI provider: auto | gemini | qwen
    ai_provider: str = "auto"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
