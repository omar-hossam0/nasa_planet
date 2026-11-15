"""API schemas (pydantic v2). Published to Members 4-6 as the contract."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .canonical import is_month


class AnalysisRequest(BaseModel):
    region_id: str = Field(description="study window id from the catalog")
    variable_ids: list[str] = Field(min_length=1, max_length=4)
    start_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    end_month: str = Field(pattern=r"^\d{4}-\d{2}$")
    aoi: dict | None = Field(
        default=None,
        description="optional GeoJSON Polygon in WGS84 lon/lat; must lie "
                    "inside the region bbox")
    aggregation_policy_id: str | None = None
    method_revision: str | None = None
    data_revision: str | None = None

    @field_validator("start_month", "end_month")
    @classmethod
    def _valid_month(cls, v: str) -> str:
        if not is_month(v):
            raise ValueError("month must look like YYYY-MM")
        return v


class JobError(BaseModel):
    code: str
    detail: str


class JobResponse(BaseModel):
    job_id: str
    state: Literal["queued", "running", "succeeded", "failed"]
    progress: float
    request_hash: str
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result_id: str | None = None
    error: JobError | None = None
    cached: bool = False


class CatalogEntry(BaseModel):
    variable_id: str
    region_id: str
    product_id: str
    version: str | None
    units: str
    label: str | None
    bbox: list[float]
    native_grid: dict | None
    measurement_ready: bool
    method_ready: bool
    app_available: bool
    method_revision: str
    source_kind: str | None
    limitations: list[str]


class CatalogResponse(BaseModel):
    data_revision: str
    method_revision: str
    entries: list[CatalogEntry]


class ResultResponse(BaseModel):
    result_id: str
    job_id: str
    request_hash: str
    state: Literal["succeeded", "insufficient_data", "unavailable", "failed"]
    data_revision: str
    method_revision: str
    receipt_id: str | None
    payload: dict[str, Any]
    payload_sha256: str


class ReceiptResponse(BaseModel):
    receipt_id: str
    payload: dict[str, Any]
    payload_sha256: str
    created_at: str


class MethodResponse(BaseModel):
    method_revision: str
    alpha: float
    basis: str
    aggregation: dict
    dependence: dict
    bootstrap: dict
    multiplicity: dict
    minimum_series: dict
    period_sensitivity: dict


class HealthResponse(BaseModel):
    status: Literal["ok"]
    software_revision: str
    data_revision: str
    method_revision: str
    database: str
    queue_depth: int
