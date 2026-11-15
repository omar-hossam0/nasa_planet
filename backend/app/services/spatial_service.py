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

    def __init__(self, results: ResultService, settings: Settings, data=None) -> None:
        self._results = results
        self._settings = settings
        self._data = data

    def get_spatial(self, result_id: str, compact: bool = False):
        result = self._results.get_result(result_id)
        if result.science:
            if compact:
                from app.schemas.spatial import CompactSpatialResponse
                variable=result.variables[0].variable_id
                a=result.science[variable]
                dy,dx=a['native_spacing_degrees']
                return CompactSpatialResponse(result_id=result.result_id,variable_id=variable,lat=a['lat'],lon=a['lon'],
                    slope=a['annual_slope'],bounds=[a['lon'][0]-dx/2,a['lat'][0]-dy/2,a['lon'][-1]+dx/2,a['lat'][-1]+dy/2],
                    cell_count=len(a['lat'])*len(a['lon']),disclaimer=result.disclaimer)
            from app.services.science_spatial import spatial
            return spatial(result)
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
        if result.science:
            from app.services.science_spatial import cell_detail
            return cell_detail(result,cell_id,self._data)
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
