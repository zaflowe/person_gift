"""Application configuration using pydantic-settings."""
from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    database_url: str = "sqlite:///./data/person_gift.db"
    gemini_api_key: str = ""
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24 * 7
    timezone: str = "Asia/Taipei"

    # Personal telemetry. Keep the ingest key on devices; reserve the agent key
    # for GPT/administration because it can read and write semantic state.
    telemetry_ingest_key: str = ""
    telemetry_agent_key: str = ""

    # Used only by the server-side telemetry worker, independently of other AI.
    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_timeout_seconds: float = Field(default=30, ge=1, le=90)
    telemetry_enrichment_enabled: bool = False

    gemini_mock_mode: bool = False

    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    ai_provider: str = "auto"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
