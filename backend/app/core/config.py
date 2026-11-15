"""Application settings.

All values are environment-overridable so the same image can run in mock and
(later) real mode. No credentials are required to boot the application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator, model_validator
from typing import Literal
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Environment variables use the upper-case form of each field name
    (``APP_NAME``, ``MOCK_MODE``, ``API_PREFIX`` ...). A local ``.env`` file is
    read when present, but is never required and never committed.
    """

    model_config = SettingsConfigDict(
        env_file=(Path(__file__).resolve().parents[3] / '.env',
                  Path(__file__).resolve().parents[2] / '.env'),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- identity -------------------------------------------------------
    app_name: str = "Trend Detective Backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    api_prefix: str = "/v1"

    # --- capability switches -------------------------------------------
    # MOCK_MODE=true is the only supported mode in this milestone. Flipping it
    # to false makes the readiness probe report NOT_IMPLEMENTED for the real
    # adapters instead of silently pretending they exist.
    mock_mode: bool = True
    database_url: str | None = Field(default=None, repr=False)
    database_auto_create: bool = False
    job_backend: Literal['inline', 'database'] = 'inline'
    rag_enabled: bool = True
    regions_file: str | None = None
    llm_provider: Literal['gemini'] = 'gemini'
    gemini_api_key: SecretStr = Field(default=SecretStr(''), repr=False)
    llm_model: str = Field(default='gemini-2.5-flash', pattern=r'^[a-zA-Z0-9._-]+$')
    llm_timeout_seconds: float = Field(default=8, gt=0, le=60)
    llm_max_retries: int = Field(default=1, ge=0, le=2)

    @model_validator(mode='after')
    def validate_storage(self):
        if self.job_backend == 'database' and not self.database_url:
            raise ValueError('JOB_BACKEND=database requires DATABASE_URL')
        if self.app_env.lower() == 'production':
            raise ValueError('Production release is not enabled: real science and authorization integration remain required')
        return self

    # --- observability / web -------------------------------------------
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- request guardrails --------------------------------------------
    max_variables_per_analysis: int = Field(default=4, ge=1, le=8)
    min_period_months: int = Field(default=12, ge=1)
    max_period_months: int = Field(default=600, ge=1)
    min_aoi_span_degrees: float = Field(default=0.25, gt=0)
    max_aoi_span_degrees: float = Field(default=40.0, gt=0)
    max_question_length: int = Field(default=500, ge=8)
    max_comparison_cells: int = Field(default=4, ge=2)
    min_spin_window_years: int = Field(default=3, ge=1)
    max_spin_windows: int = Field(default=60, ge=1)

    # --- mock job behaviour --------------------------------------------
    # When true (default) a submitted analysis is executed synchronously inside
    # the request so the API is immediately pollable. Tests may set this to
    # false to observe the queued -> running -> completed transition manually.
    mock_auto_complete_jobs: bool = True

    @field_validator("api_prefix")
    @classmethod
    def _normalise_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            value = "/" + value
        return value.rstrip("/")

    @field_validator("log_level")
    @classmethod
    def _normalise_log_level(cls, value: str) -> str:
        level = value.strip().upper()
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        return level if level in allowed else "INFO"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_mock(self) -> bool:
        return self.mock_mode


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor used outside of dependency injection."""

    return Settings()
