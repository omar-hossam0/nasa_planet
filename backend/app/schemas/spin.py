"""Spin It (time-window sensitivity) schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import DISCLAIMER, DataMode, EvidenceState, TrendDirection


class SpinStatus(str, Enum):
    queued = "queued"
    completed = "completed"
    failed = "failed"


class SpinRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "minimum_window_years": 10,
                "start_year_min": 2001,
                "end_year_max": 2024,
            }
        },
    )

    minimum_window_years: int = Field(default=10, ge=1, le=30)
    start_year_min: int | None = Field(default=None, ge=1900, le=2200)
    end_year_max: int | None = Field(default=None, ge=1900, le=2200)

    @model_validator(mode="after")
    def _check_bounds(self) -> "SpinRequest":
        if (
            self.start_year_min is not None
            and self.end_year_max is not None
            and self.start_year_min > self.end_year_max
        ):
            raise ValueError("start_year_min must not be greater than end_year_max")
        return self


class SpinWindow(BaseModel):
    window_id: str
    start_month: str
    end_month: str
    years: float
    trend_value: float | None
    direction: TrendDirection
    evidence_state: EvidenceState = EvidenceState.synthetic_demo


class SpinSummary(BaseModel):
    window_count: int
    min_trend: float | None
    max_trend: float | None
    mean_trend: float | None
    sign_agreement_share: float | None = Field(
        default=None,
        description=(
            "Share of windows sharing the modal trend sign. Descriptive sensitivity only; "
            "not a probability that the trend is real."
        ),
    )
    note: str = "Descriptive sensitivity across synthetic windows. Not a statistical test."


class SpinLinks(BaseModel):
    self_url: str
    result: str


class SpinCreateResponse(BaseModel):
    spin_id: str
    result_id: str
    status: SpinStatus
    message: str
    links: SpinLinks
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER


class SpinResponse(BaseModel):
    spin_id: str
    result_id: str
    status: SpinStatus
    request: SpinRequest
    variable_id: str
    display_name: str
    unit: str
    trend_unit: str
    windows: list[SpinWindow]
    summary: SpinSummary
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)
