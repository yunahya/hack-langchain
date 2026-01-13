"""
Application configuration using pydantic-settings.

Loads settings from environment variables and .env file.
"""

from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # CORS origins for Next.js frontend
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    ]

    # Default LLM model
    default_model: str = "google/gemini-2.0-flash"

    # API settings
    api_timeout_seconds: int = 300  # 5 minutes for long workflows

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
