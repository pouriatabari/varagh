"""Application settings, loaded from environment variables / `.env`."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets only ever come from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Varagh"
    environment: Literal["development", "test", "production"] = "development"
    debug: bool = False

    database_url: str = "postgresql+psycopg://varagh:varagh@db:5432/varagh"
    secret_key: str = "dev-secret-key-change-me"
    timezone: str = "Asia/Tehran"

    # Optional single-user HTTP Basic auth.
    basic_auth_user: str = ""
    basic_auth_password: str = ""

    # AI is entirely optional; without a key the app is fully functional.
    ai_provider: str = ""
    ai_api_key: str = ""
    ai_model: str = ""
    ai_base_url: str = ""
    ai_timeout_seconds: float = 30.0
    ai_max_output_tokens: int = 2048
    # How the key is sent: "x-api-key", "bearer" or "both".
    ai_auth_header: Literal["x-api-key", "bearer", "both"] = "both"
    # Custom provider: the full endpoint URL and extra headers.
    ai_custom_url: str = ""
    ai_custom_headers: str = ""
    ai_custom_method: Literal["json", "openai", "anthropic", "prompt"] = "json"

    # Notification channels.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    webhook_url: str = ""
    webhook_format: Literal["json", "slack"] = "slack"

    # Filesystem paths.
    data_dir: str = "./data"

    @property
    def basic_auth_enabled(self) -> bool:
        return bool(self.basic_auth_user and self.basic_auth_password)

    @property
    def ai_enabled(self) -> bool:
        return bool(self.ai_provider and self.ai_api_key and self.ai_model)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton."""
    return Settings()
