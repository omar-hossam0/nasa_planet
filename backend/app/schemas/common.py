"""Shared enums, primitives and the standard error envelope."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from app.core.timeutil import is_valid_month

DISCLAIMER = "Synthetic demonstration data. Not a NASA scientific result."


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class DataMode(str, Enum):
    """Machine-readable provenance marker carried by every payload."""

    mock = "mock"
    real = "real"


class EvidenceState(str, Enum):
    """How much scientific weight a value carries."""

    synthetic_demo = "synthetic_demo"
    verified = "verified"
    insufficient_data = "insufficient_data"
    not_computed = "not_computed"


class TrendDirection(str, Enum):
    increasing = "increasing"
    decreasing = "decreasing"
    inconclusive = "inconclusive"
    insufficient_data = "insufficient_data"
    not_computed = "not_computed"


class AggregationPolicy(str, Enum):
    area_weighted = "area_weighted"
    cell_mean = "cell_mean"
    unweighted_mean = "unweighted_mean"


class Language(str, Enum):
    en = "en"
    ar = "ar"


class Severity(str, Enum):
    info = "info"
    warning = "warning"
    error = "error"


class AvailabilityReason(str, Enum):
    """Why a variable/region/period is or is not usable."""

    DEMO_READY = "DEMO_READY"
    MOCK_DEMO_ONLY = "MOCK_DEMO_ONLY"
    METHOD_NOT_APPROVED = "METHOD_NOT_APPROVED"
    OUTSIDE_COVERAGE = "OUTSIDE_COVERAGE"
    UNKNOWN_VARIABLE = "UNKNOWN_VARIABLE"
    UNKNOWN_REGION = "UNKNOWN_REGION"
    INVALID_PERIOD = "INVALID_PERIOD"
    INVALID_AOI = "INVALID_AOI"


class AoiType(str, Enum):
    bbox = "bbox"


# ---------------------------------------------------------------------------
# Primitives
# ---------------------------------------------------------------------------
def _validate_month(value: str) -> str:
    if not is_valid_month(value):
        raise ValueError("must be a YYYY-MM month string, for example '2005-01'")
    return value


MonthStr = Annotated[str, AfterValidator(_validate_month)]


class ApiWarning(BaseModel):
    """Structured warning. Clients should render these, not drop them."""

    code: str = Field(description="Stable warning identifier.")
    message: str = Field(description="Human readable warning.")
    severity: Severity = Severity.warning


class Aoi(BaseModel):
    """Area of interest. Only ``bbox`` is approved for this milestone."""

    model_config = ConfigDict(extra="forbid")

    type: AoiType = Field(default=AoiType.bbox, description="Geometry kind.")
    coordinates: list[float] = Field(
        min_length=4,
        max_length=4,
        description="[west, south, east, north] in WGS84 degrees.",
        examples=[[29.0, 24.0, 33.0, 32.0]],
    )

    @field_validator("coordinates")
    @classmethod
    def _validate_coordinates(cls, value: list[float]) -> list[float]:
        west, south, east, north = value
        if not -180.0 <= west <= 180.0 or not -180.0 <= east <= 180.0:
            raise ValueError("longitudes must be within [-180, 180]")
        if not -90.0 <= south <= 90.0 or not -90.0 <= north <= 90.0:
            raise ValueError("latitudes must be within [-90, 90]")
        if west >= east:
            raise ValueError("west must be strictly less than east")
        if south >= north:
            raise ValueError("south must be strictly less than north")
        return [float(coord) for coord in value]

    @property
    def west(self) -> float:
        return self.coordinates[0]

    @property
    def south(self) -> float:
        return self.coordinates[1]

    @property
    def east(self) -> float:
        return self.coordinates[2]

    @property
    def north(self) -> float:
        return self.coordinates[3]

    @property
    def width(self) -> float:
        return self.east - self.west

    @property
    def height(self) -> float:
        return self.north - self.south

    def canonical(self) -> list[float]:
        """Rounded, order-stable form used inside cache keys."""
        return [round(coord, 4) for coord in self.coordinates]


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    request_id: str


class ErrorEnvelope(BaseModel):
    """Single error shape returned by every failing endpoint."""

    error: ErrorDetail

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "code": "DATA_NOT_AVAILABLE",
                    "message": "The requested data is not available.",
                    "details": {"variable_id": "precipitation"},
                    "request_id": "req_3f8a1c92d4e1",
                }
            }
        }
    )


class PageMeta(BaseModel):
    count: int
    total: int


class Meta(BaseModel):
    """Envelope metadata shared by list responses."""

    data_mode: DataMode = DataMode.mock
    disclaimer: str = DISCLAIMER
    generated_at: str | None = None


BBox = list[float]
FilterKey = Literal["variable_id", "region_id", "period", "aoi"]
