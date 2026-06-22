"""Configuracao da aplicacao via env vars."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_env: Literal["development", "staging", "production"] = "development"
    app_name: str = "cartorio-backend"
    app_port: int = 8000
    log_level: str = "INFO"

    database_url: str

    audit_hmac_key: str = Field(min_length=32)

    pii_scrub_enabled: bool = True

    litellm_base_url: str = "http://litellm:4000"
    litellm_api_key: str = ""
    litellm_model_primary: str = "claude-opus-4-5"
    litellm_model_fallback: str = "gpt-5.5"

    evolution_base_url: str = ""
    evolution_api_key: str = ""
    evolution_instance: str = ""

    openclaw_base_url: str = ""
    openclaw_api_key: str = ""

    n8n_base_url: str = ""
    n8n_webhook_secret: str = ""

    dpo_email: str = ""
    retention_days_conversas: int = 365
    retention_days_audit: int = 1825

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
