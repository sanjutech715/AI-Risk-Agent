"""
config.py
─────────
Centralized configuration management using Pydantic BaseSettings.
Loads configuration from environment variables with validation.
"""

import os
from typing import List, Optional
from distutils.util import strtobool
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )
    """Application settings loaded from environment variables."""

    # ── Server Configuration ──────────────────────────────────────────────────
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000, gt=0, le=65535)
    reload: bool = Field(default=False, alias="UVICORN_RELOAD")
    debug: bool = Field(default=False)

    # ── CORS Configuration ────────────────────────────────────────────────────
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
    )
    cors_allow_credentials: bool = Field(default=True)
    cors_allow_methods: List[str] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
    )

    # ── Database Configuration ────────────────────────────────────────────────
    database_url: str = Field(
        default="postgresql://user:password@localhost:5432/risk_agent",
    )
    database_pool_size: int = Field(default=10, gt=0)
    database_max_overflow: int = Field(default=20, ge=0)

    # ── Redis Cache Configuration ─────────────────────────────────────────────
    redis_url: str = Field(
        default="redis://localhost:6379/0",
    )
    cache_ttl_seconds: int = Field(default=3600, gt=0)
    cache_enabled: bool = Field(default=True)

    # ── Authentication Configuration ──────────────────────────────────────────
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        min_length=32
    )
    jwt_algorithm: str = Field(default="HS256")
    jwt_expiration_hours: int = Field(default=24, gt=0)

    # ── API Key Configuration ─────────────────────────────────────────────────
    api_key_header: str = Field(default="X-API-Key")
    api_keys: List[str] = Field(default_factory=list)

    # ── Rate Limiting Configuration ───────────────────────────────────────────
    rate_limit_requests: int = Field(default=100, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)

    # ── LLM Configuration ────────────────────────────────────────────────────
    ollama_url: str = Field(
        default="http://localhost:11434",
    )
    ollama_model: str = Field(default="llama2")
    anthropic_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-3-sonnet-20240229")

    # ── Logging Configuration ────────────────────────────────────────────────
    log_level: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_format: str = Field(
        default="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    # ── Health Check Configuration ───────────────────────────────────────────
    health_check_database: bool = Field(default=True)
    health_check_cache: bool = Field(default=True)
    health_check_llm: bool = Field(default=True)

    # ── Feature Flags ────────────────────────────────────────────────────────
    enable_batch_processing: bool = Field(default=True)
    enable_caching: bool = Field(default=True)
    enable_authentication: bool = Field(default=False)
    enable_rate_limiting: bool = Field(default=True)

    @field_validator(
        "reload",
        "debug",
        "cors_allow_credentials",
        "cache_enabled",
        "health_check_database",
        "health_check_cache",
        "health_check_llm",
        "enable_batch_processing",
        "enable_caching",
        "enable_authentication",
        "enable_rate_limiting",
        mode="before",
    )
    def _parse_bool_fields(cls, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"true", "1", "yes", "on", "y", "debug"}:
                return True
            if normalized in {"false", "0", "no", "off", "n", "release", "prod", "production"}:
                return False
        return value


# ── Global settings instance ──────────────────────────────────────────────────
settings = Settings()