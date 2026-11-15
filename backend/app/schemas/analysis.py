"""Analysis request/response schemas and job state models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.timeutil import month_to_index
from app.schemas.common import (
    DISCLAIMER,
    AggregationPolicy,
    Aoi,
    DataMode,
    MonthStr,
)


class JobState(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"


class AnalysisRequest(BaseModel):
    """Body of ``POST /v1/analyses``."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "variable_ids": ["air_temperature"],
                "region_id": "nile_corridor",
                "aoi": {"type": "bbox", "coordinates": [29.0, 24.0, 33.0, 32.0]},
                "start_month": "2005-01",
                "end_month": "2020-12",
                "aggregation_policy": "area_weighted",
            }
        },
    )

    variable_ids: list[str] = Field(
        min_length=1,
        max_length=8,
        description="Catalog variable ids (aliases such as 'T2M' are resolved).",
    )
    region_id: str = Field(min_length=1, max_length=64, examples=["nile_corridor"])
    aoi: Aoi | None = Field(
        default=None,
        description="Optional AOI. When omitted the region bbox is used.",
    )
    start_month: MonthStr = Field(examples=["2005-01"])
    end_month: MonthStr = Field(examples=["2020-12"])
    aggregation_policy: AggregationPolicy = AggregationPolicy.area_weighted

    @field_validator("variable_ids")
    @classmethod
    def _deduplicate(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for item in value:
            cleaned = item.strip()
            if not cleaned:
                raise ValueError("variable_ids must not contain empty strings")
            if cleaned not in seen:
                seen.append(cleaned)
        if not seen:
            raise ValueError("at least one variable_id is required")
        return seen

    @field_validator("region_id")
    @classmethod
    def _clean_region(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("region_id must not be empty")
        return cleaned

    @model_validator(mode="after")
    def _check_period_order(self) -> "AnalysisRequest":
        if month_to_index(self.start_month) > month_to_index(self.end_month):
            raise ValueError("start_month must not be later than end_month")
        return self


class AnalysisSpec(BaseModel):
    """Normalised, alias-resolved analysis request used by services/adapters."""

    model_config = ConfigDict(extra="forbid")

    variable_ids: list[str]
    region_id: str
    aoi: Aoi
    start_month: str
    end_month: str
    aggregation_policy: AggregationPolicy
    period_months: int
    cache_key: str
    dataset_revision: str
    method_version: str


class StateTransition(BaseModel):
    status: JobState
    at: datetime
    message: str | None = None


class JobLinks(BaseModel):
    job: str
    result: str | None = None


class AnalysisAcceptedResponse(BaseModel):
    """Returned by ``POST /v1/analyses`` (202 for new work, 200 for cache hit)."""

    job_id: str
    status: JobState
    result_id: str | None = None
    cached: bool = False
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    links: JobLinks
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: JobState
    result_id: str | None = None
    progress_percent: int = Field(ge=0, le=100)
    request: AnalysisRequest
    resolved_variable_ids: list[str]
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)
    state_history: list[StateTransition] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    links: JobLinks
