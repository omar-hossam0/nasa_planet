"""Map-ready spatial payloads derived from a stored result."""

from __future__ import annotations

from app.core.config import Settings
from app.core.exceptions import CellNotFoundError
from app.mocks import analyses as synthetic
from app.mocks.spatial import (
    GRID_COLS,
    GRID_LABEL,
    GRID_ROWS,
    CellDataset,
    build_cell_datasets,
    missing_cell_count,
    polygon_for,
    to_spatial_cell,
)
from app.schemas.common import ApiWarning, Severity
from app.schemas.results import ResultResponse
from app.schemas.spatial import CellDetailResponse, SpatialResponse
from app.services.result_service import ResultService


class SpatialService:
    """Cells are regenerated deterministically from the parent result identity.

    Nothing is stored per cell, so ``/spatial`` and ``/cells/{id}`` can never
    drift apart.
    """

    def __init__(self, results: ResultService, settings: Settings) -> None:
        self._results = results
        self._settings = settings

    def get_spatial(self, result_id: str) -> SpatialResponse:
        result = self._results.get_result(result_id)
        datasets = self._cells(result)
        primary = result.variables[0]
        trend_unit = primary.trend.slope_unit or f"{primary.unit} year-1"

        warnings = [
            ApiWarning(
                code="SYNTHETIC_GRID",
                message="Cells are synthetic demo values, not a NASA gridded product.",
                severity=Severity.warning,
            )
        ]
        if any(dataset.missing for dataset in datasets):
            warnings.append(
                ApiWarning(
                    code="MISSING_CELLS",
                    message=(
                        f"{missing_cell_count(datasets)} cell(s) carry no data and must be "
                        "rendered as missing, not as zero."
                    ),
                    severity=Severity.info,
                )
            )

        return SpatialResponse(
            result_id=result.result_id,
            variable_id=primary.variable_id,
            unit=primary.unit,
            trend_unit=trend_unit,
            grid=GRID_LABEL,
            cell_count=len(datasets),
            missing_cell_count=missing_cell_count(datasets),
            bounds=result.analysis.aoi.canonical(),
            cells=[
                to_spatial_cell(dataset, result.result_id, primary.variable_id, trend_unit)
                for dataset in datasets
            ],
            warnings=warnings,
        )

    def get_cell(self, result_id: str, cell_id: str) -> CellDetailResponse:
        result = self._results.get_result(result_id)
        datasets = {dataset.cell_id: dataset for dataset in self._cells(result)}
        dataset = datasets.get(cell_id)
        if dataset is None:
            raise CellNotFoundError(cell_id, result_id)

        primary = result.variables[0]
        trend_unit = primary.trend.slope_unit or f"{primary.unit} year-1"
        trend = synthetic.summarise_trend(primary.variable_id, dataset.series, label=f"cell {cell_id}")

        warnings = [
            ApiWarning(
                code="SYNTHETIC_CELL",
                message="This cell is a synthetic demonstration value, not a NASA observation.",
                severity=Severity.warning,
            )
        ]
        if dataset.missing:
            warnings.append(
                ApiWarning(
                    code="CELL_MISSING_DATA",
                    message="This cell has no data; its trend is not estimable.",
                    severity=Severity.warning,
                )
            )

        return CellDetailResponse(
            cell_id=cell_id,
            result_id=result.result_id,
            variable_id=primary.variable_id,
            display_name=primary.display_name,
            unit=primary.unit,
            bbox=list(dataset.bbox),
            centroid=list(dataset.centroid),
            geometry=polygon_for(dataset.bbox),
            missing_data=dataset.missing,
            evidence_state=dataset.evidence_state,
            trend=trend,
            series=dataset.series,
            warnings=warnings,
        )

    # -- helpers ----------------------------------------------------------
    def _cells(self, result: ResultResponse) -> list[CellDataset]:
        primary = result.variables[0]
        return build_cell_datasets(
            primary.variable_id,
            result.analysis.aoi.canonical(),
            result.analysis.start_month,
            result.analysis.end_month,
            seed_key=result.result_id,
        )

    @staticmethod
    def grid_label() -> str:
        return f"{GRID_ROWS}x{GRID_COLS} ({GRID_LABEL})"
