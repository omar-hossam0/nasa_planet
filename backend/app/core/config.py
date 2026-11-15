"""Application settings.

All values are environment-overridable so the same image can run in mock and
(later) real mode. No credentials are required to boot the application.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Environment variables use the upper-case form of each field name
    (``APP_NAME``, ``MOCK_MODE``, ``API_PREFIX`` ...). A local ``.env`` file is
    read when present, but is never required and never committed.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
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
