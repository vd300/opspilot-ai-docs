from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "OpsPilot AI"
    app_version: str = "0.1.0"
    environment: str = Field(default="local", validation_alias="APP_ENV")
    debug: bool = False
    log_level: str = "INFO"
    persistence_database_path: str = "data/opspilot.sqlite3"
    model_provider: Literal["stub", "openai"] = "stub"
    model_name: str = "gpt-4.1-mini"
    model_api_key: str | None = None
    model_base_url: str = "https://api.openai.com/v1"
    model_timeout_seconds: float = Field(default=20.0, gt=0)
    live_model_validation_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="APP_",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
