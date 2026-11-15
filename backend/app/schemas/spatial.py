"""Spatial (map-ready) schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import (
    DISCLAIMER,
    ApiWarning,
    DataMode,
    EvidenceState,
    TrendDirection,
)
from app.schemas.results import TimeSeriesPoint, TrendSummary


class CellGeometry(BaseModel):
    """Plain GeoJSON-ish geometry so the map layer needs no translation."""

    type: str = "Polygon"
    coordinates: list[list[list[float]]] = Field(
        description="GeoJSON Polygon rings: [[[lon, lat], ...]]."
    )


class SpatialCell(BaseModel):
    cell_id: str
    result_id: str
    variable_id: str
    bbox: list[float] = Field(description="[west, south, east, north] in WGS84 degrees.")
    centroid: list[float] = Field(description="[lon, lat]")
    geometry: CellGeometry
    trend_value: float | None = Field(
        default=None, description="Synthetic slope in trend_unit; null when missing."
    )
    trend_unit: str
    direction: TrendDirection
    evidence_state: EvidenceState = EvidenceState.synthetic_demo
    missing_data: bool = False
    data_mode: DataMode = DataMode.mock


class SpatialResponse(BaseModel):
    result_id: str
    variable_id: str
    unit: str
    trend_unit: str
    grid: str
    cell_count: int
    missing_cell_count: int
    bounds: list[float]
    cells: list[SpatialCell]
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[ApiWarning] = Field(default_factory=list)


class CellDetailResponse(BaseModel):
    cell_id: str
    result_id: str
    variable_id: str
    display_name: str
    unit: str
    bbox: list[float]
    centroid: list[float]
    geometry: CellGeometry
    missing_data: bool
    evidence_state: EvidenceState
    trend: TrendSummary
    series: list[TimeSeriesPoint]
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[ApiWarning] = Field(default_factory=list)
