import os
from typing import List, Any
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or a .env file.
    """
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: Any = ["http://localhost:3000", "http://localhost:8000"]
    GEMINI_API_KEY: str = ""

    # Load configuration from environment variables or .env file if it exists
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

# Instantiate settings singleton to import across the project
settings = Settings()
