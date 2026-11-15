"""Result payload schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import (
    DISCLAIMER,
    AggregationPolicy,
    ApiWarning,
    Aoi,
    DataMode,
    EvidenceState,
    TrendDirection,
)


class TimeSeriesPoint(BaseModel):
    month: str = Field(examples=["2005-01"])
    value: float | None = Field(description="Monthly value in the declared unit; null when missing.")
    missing: bool = False


class TrendSummary(BaseModel):
    """Descriptive trend of the synthetic series.

    No significance test is computed in this milestone, so ``p_value`` and
    ``r_squared`` stay null and ``inference_status`` says so explicitly.
    """

    method_id: str
    method_version: str
    direction: TrendDirection
    slope_per_year: float | None = None
    slope_unit: str | None = Field(default=None, examples=["K year-1"])
    intercept: float | None = Field(
        default=None, description="Fitted value at the first complete year of the sample."
    )
    n_months: int
    n_years: int = Field(default=0, description="Complete calendar years used in the fit.")
    p_value: float | None = None
    r_squared: float | None = None
    inference_status: str = "not_computed"
    evidence_state: EvidenceState = EvidenceState.synthetic_demo
    notes: list[str] = Field(default_factory=list)


class VariableResult(BaseModel):
    variable_id: str
    display_name: str
    unit: str
    units_verified: bool
    series: list[TimeSeriesPoint]
    trend: TrendSummary


class DatasetRevision(BaseModel):
    variable_id: str
    product_id: str
    version: str
    source_variable: str
    revision: str
    source: str = "mock_registry_snapshot"


class MethodRef(BaseModel):
    method_id: str
    method_version: str
    aggregation_policy: AggregationPolicy
    status: str = "mock_synthetic"
    approved: bool = False
    note: str = "Mock statistics adapter. Method has not been scientifically reviewed."


class AnalysisEcho(BaseModel):
    """The request that produced the result, echoed for traceability."""

    variable_ids: list[str]
    region_id: str
    region_display_name: str
    aoi: Aoi
    start_month: str
    end_month: str
    period_months: int
    aggregation_policy: AggregationPolicy


class SpatialRef(BaseModel):
    spatial_url: str
    cell_count: int
    missing_cell_count: int = 0
    grid: str


class ResultLinks(BaseModel):
    self_url: str
    spatial: str
    receipt: str
    receipt_download: str


class ResultResponse(BaseModel):
    result_id: str
    job_id: str
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    evidence_state: EvidenceState = EvidenceState.synthetic_demo
    analysis: AnalysisEcho
    datasets: list[DatasetRevision]
    method: MethodRef
    variables: list[VariableResult]
    warnings: list[ApiWarning] = Field(default_factory=list)
    spatial: SpatialRef | None = None
    receipt_id: str
    links: ResultLinks
    created_at: datetime


class ResultSummary(BaseModel):
    """Lightweight listing entry (used by tests and future search)."""

    result_id: str
    job_id: str
    region_id: str
    variable_ids: list[str]
    start_month: str
    end_month: str
    data_mode: DataMode = DataMode.mock
