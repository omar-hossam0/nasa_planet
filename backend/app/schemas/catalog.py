"""Catalog, region and availability schemas."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.schemas.common import (
    DISCLAIMER,
    AggregationPolicy,
    Aoi,
    AvailabilityReason,
    DataMode,
    MonthStr,
)


class CatalogState(str, Enum):
    """Two distinct questions, deliberately not collapsed into one flag."""

    catalogued = "catalogued"  # we know the variable
    measurement_ready = "measurement_ready"  # data exists for some region
    analysis_ready = "analysis_ready"  # approved method + app wiring
    planned = "planned"


class SourceInfo(BaseModel):
    product_id: str
    version: str
    source_variable: str
    provider: str = "NASA"
    documentation_url: str | None = None
    lineage_note: str


class VariableSummary(BaseModel):
    variable_id: str
    display_name: str
    description: str
    unit: str
    units_verified: bool = Field(
        description="True when the unit is asserted by a registry file in this repository."
    )
    unit_source: str
    source: SourceInfo
    availability_state: CatalogState
    measurement_ready: bool
    method_ready: bool
    app_available: bool
    demo_available: bool
    demo_only: bool
    data_mode: DataMode = DataMode.mock


class VariableDetail(VariableSummary):
    aliases: list[str] = Field(default_factory=list)
    supported_regions: list[str] = Field(default_factory=list)
    coverage_start: str
    coverage_end: str
    native_grid: dict[str, int] | None = None
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class CatalogResponse(BaseModel):
    variables: list[VariableSummary]
    count: int
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    registry_snapshot: str
    warnings: list[str] = Field(default_factory=list)


class RegionSummary(BaseModel):
    region_id: str
    display_name: str
    description: str
    bbox: list[float] = Field(description="[west, south, east, north] in WGS84 degrees.")
    period_start: str
    period_end: str
    supported_variable_ids: list[str]
    demo_only: bool = True
    data_mode: DataMode = DataMode.mock
    warnings: list[str] = Field(default_factory=list)


class RegionsResponse(BaseModel):
    regions: list[RegionSummary]
    count: int
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER


class AvailabilityResponse(BaseModel):
    """Result of asking "can I actually run this?".

    ``measurement_ready`` / ``method_ready`` / ``app_available`` come from the
    verified registry snapshot. ``demo_available`` is the mock-mode gate that
    lets the frontend exercise the flow. ``availability_source`` says which of
    the two answered, so a simulated answer is never mistaken for a verified one.
    """

    variable_id: str
    region_id: str
    start_month: str
    end_month: str
    aoi: Aoi | None = None
    measurement_ready: bool
    method_ready: bool
    app_available: bool
    demo_available: bool
    usable: bool
    reason_code: AvailabilityReason
    reason_message: str
    availability_source: str
    simulated: bool = Field(
        default=True, description="True when the answer is mock-simulated, not registry-verified."
    )
    supported_aggregation_policies: list[AggregationPolicy] = Field(default_factory=list)
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)


class AvailabilityQuery(BaseModel):
    """Documentation-only model mirroring the query parameters."""

    variable_id: str
    region_id: str
    start_month: MonthStr
    end_month: MonthStr
    bbox: str | None = Field(
        default=None,
        description="Optional 'west,south,east,north' comma-separated bbox in WGS84.",
        examples=["29.0,24.0,33.0,32.0"],
    )
