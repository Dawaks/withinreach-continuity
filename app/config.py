"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for WithinReach Continuity.

    All values can be overridden via environment variables or a .env file.
    The Bedrock model ID is configurable and swappable — the application
    must not assume a specific model is always available.
    """

    DATABASE_URL: str = "sqlite:///./continuity.db"
    AI_ENABLED: bool = False
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-haiku-20240307-v1:0"
    BEDROCK_REGION: str = "us-east-1"
    SEED_DEMO_DATA: bool = True

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


settings = Settings()
