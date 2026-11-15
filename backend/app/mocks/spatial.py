"""Deterministic synthetic spatial grid.

A fixed 3x3 regular lon/lat grid is generated inside the analysis bbox. Cell
trends are derived from each cell's own synthetic series, so ``/spatial`` and
``/cells/{cell_id}`` always agree. One cell is deliberately missing to exercise
the missing-data path in the frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.mocks.analyses import (
    SLOPE_DECIMALS,
    annual_mean_slope,
    build_series,
    direction_for,
    profile_for,
)
from app.schemas.common import EvidenceState, TrendDirection
from app.schemas.results import TimeSeriesPoint
from app.schemas.spatial import CellGeometry, SpatialCell

GRID_ROWS = 3
GRID_COLS = 3
GRID_LABEL = "3x3_regular_lonlat"
MISSING_CELL_INDEX = 8  # cell_09 - exercises the missing-data branch


@dataclass(frozen=True)
class CellDataset:
    cell_id: str
    variable_id: str
    bbox: tuple[float, float, float, float]
    centroid: tuple[float, float]
    series: list[TimeSeriesPoint]
    slope: float | None
    missing: bool

    @property
    def direction(self) -> TrendDirection:
        if self.missing:
            return TrendDirection.insufficient_data
        return direction_for(self.slope, self.variable_id)

    @property
    def evidence_state(self) -> EvidenceState:
        return EvidenceState.insufficient_data if self.missing else EvidenceState.synthetic_demo


def cell_id_for(index: int) -> str:
    return f"cell_{index + 1:02d}"


def build_cell_datasets(
    variable_id: str,
    bbox: list[float],
    start_month: str,
    end_month: str,
    *,
    seed_key: str,
) -> list[CellDataset]:
    """Build every grid cell for one result. Fully deterministic."""
    west, south, east, north = bbox
    lon_step = (east - west) / GRID_COLS
    lat_step = (north - south) / GRID_ROWS
    profile = profile_for(variable_id)
    datasets: list[CellDataset] = []

    for row in range(GRID_ROWS):
        for column in range(GRID_COLS):
            index = row * GRID_COLS + column
            cell_id = cell_id_for(index)
            cell_bbox = (
                round(west + column * lon_step, 4),
                round(south + row * lat_step, 4),
                round(west + (column + 1) * lon_step, 4),
                round(south + (row + 1) * lat_step, 4),
            )
            centroid = (
                round((cell_bbox[0] + cell_bbox[2]) / 2.0, 4),
                round((cell_bbox[1] + cell_bbox[3]) / 2.0, 4),
            )
            missing = index == MISSING_CELL_INDEX

            if missing:
                series = build_series(
                    variable_id,
                    start_month,
                    end_month,
                    offset_seed=f"{seed_key}:{cell_id}",
                    missing_months=frozenset(_all_months(start_month, end_month)),
                )
                slope = None
            else:
                # Cells vary around the regional slope: some hide a reversal,
                # which is the whole point of the product.
                factor = _cell_factor(seed_key, cell_id)
                series = build_series(
                    variable_id,
                    start_month,
                    end_month,
                    offset_seed=f"{seed_key}:{cell_id}",
                    trend_scale=1.0 + factor,
                    baseline_shift=profile.seasonal_amplitude * factor * 0.35,
                )
                slope, _, _, _ = annual_mean_slope(series)
                if slope is not None:
                    slope = round(slope, SLOPE_DECIMALS)

            datasets.append(
                CellDataset(
                    cell_id=cell_id,
                    variable_id=variable_id,
                    bbox=cell_bbox,
                    centroid=centroid,
                    series=series,
                    slope=slope,
                    missing=missing,
                )
            )

    return datasets


def _all_months(start_month: str, end_month: str) -> list[str]:
    from app.core.timeutil import month_range

    return month_range(start_month, end_month)


def _cell_factor(seed_key: str, cell_id: str) -> float:
    """Deterministic factor in [-1.5, 1.0] so cells diverge from the mean.

    The range deliberately crosses -1.0: a factor below -1.0 flips the sign of
    the cell trend, which is exactly the "what the average hides" case the
    product is built to expose.
    """
    from app.mocks.analyses import stable_seed

    raw = stable_seed(seed_key, cell_id) % 10_000
    return (raw / 10_000.0) * 2.5 - 1.5


def polygon_for(bbox: tuple[float, float, float, float]) -> CellGeometry:
    west, south, east, north = bbox
    ring = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    return CellGeometry(type="Polygon", coordinates=[ring])


def to_spatial_cell(dataset: CellDataset, result_id: str, variable_id: str, trend_unit: str) -> SpatialCell:
    return SpatialCell(
        cell_id=dataset.cell_id,
        result_id=result_id,
        variable_id=variable_id,
        bbox=list(dataset.bbox),
        centroid=list(dataset.centroid),
        geometry=polygon_for(dataset.bbox),
        trend_value=dataset.slope,
        trend_unit=trend_unit,
        direction=dataset.direction,
        evidence_state=dataset.evidence_state,
        missing_data=dataset.missing,
    )


def missing_cell_count(datasets: list[CellDataset]) -> int:
    return sum(1 for dataset in datasets if dataset.missing)
