from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

SERVER_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=SERVER_DIR / ".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://hirelogic:hirelogic@localhost:5432/hirelogic"
    SECRET_KEY: str = "dev-secret-key"
    AGENT_INTERNAL_SECRET: str = "dev-agent-secret"
    DOCUMENTS_PATH: str = "../documents"
    BACKEND_URL: str = "http://localhost:8000"
    ENV: Literal["development", "test", "production"] = "development"
    GOOGLE_API_KEY: str = ""
    GOOGLE_GENAI_USE_VERTEXAI: bool = False

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def secret_key(self) -> str:
        return self.SECRET_KEY

    @property
    def effective_db_url(self) -> str:
        return self.DATABASE_URL

    @property
    def env(self) -> Literal["development", "test", "production"]:
        return self.ENV


@lru_cache
def get_settings() -> Settings:
    return Settings()
