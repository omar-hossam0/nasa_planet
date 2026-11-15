"""Comparison schemas. Cell comparisons are implemented; regional ones are reserved."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import DISCLAIMER, DataMode, EvidenceState, TrendDirection


class ComparisonType(str, Enum):
    cells = "cells"
    # Reserved: regional comparison needs two completed results and a
    # compatibility check on variable, unit, period, method and revision.


class ComparisonRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "comparison_type": "cells",
                "result_id": "result_mock_example",
                "cell_ids": ["cell_01", "cell_02"],
            }
        },
    )

    comparison_type: ComparisonType = ComparisonType.cells
    result_id: str = Field(min_length=1, max_length=128)
    cell_ids: list[str] = Field(
        min_length=2,
        max_length=4,
        description="Two to four cell ids belonging to the referenced result.",
    )

    @field_validator("cell_ids")
    @classmethod
    def _deduplicate(cls, value: list[str]) -> list[str]:
        seen: list[str] = []
        for item in value:
            cleaned = item.strip()
            if cleaned and cleaned not in seen:
                seen.append(cleaned)
        if len(seen) < 2:
            raise ValueError("cell_ids must contain at least two distinct cell ids")
        return seen


class ComparisonCell(BaseModel):
    cell_id: str
    label: str
    bbox: list[float]
    trend_value: float | None
    trend_unit: str
    direction: TrendDirection
    evidence_state: EvidenceState
    missing_data: bool


class ComparisonSeriesPoint(BaseModel):
    month: str
    values: dict[str, float | None]


class CompatibilityReport(BaseModel):
    variable_match: bool
    unit_match: bool
    period_match: bool
    method_version_match: bool
    dataset_revision_match: bool
    compatible: bool
    notes: list[str] = Field(default_factory=list)


class ComparisonDelta(BaseModel):
    cell_id: str
    difference_from_first: float | None
    percent_difference: float | None


class ComparisonResponse(BaseModel):
    comparison_id: str
    comparison_type: ComparisonType
    result_id: str
    variable_id: str
    display_name: str
    unit: str
    trend_unit: str
    start_month: str
    end_month: str
    compatibility: CompatibilityReport
    cells: list[ComparisonCell]
    series: list[ComparisonSeriesPoint]
    deltas: list[ComparisonDelta]
    summary: str
    chart_hint: str = "multi_line"
    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    warnings: list[str] = Field(default_factory=list)
