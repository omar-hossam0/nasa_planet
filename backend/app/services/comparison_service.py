"""Cell-to-cell comparison."""

from __future__ import annotations

import hashlib

from app.core.config import Settings
from app.core.exceptions import CellNotFoundError, IncompatibleComparisonError
from app.mocks.spatial import CellDataset, build_cell_datasets
from app.schemas.comparison import (
    ComparisonCell,
    ComparisonDelta,
    ComparisonRequest,
    ComparisonResponse,
    ComparisonSeriesPoint,
    ComparisonType,
    CompatibilityReport,
)
from app.services.result_service import ResultService


class ComparisonService:
    def __init__(self, results: ResultService, settings: Settings) -> None:
        self._results = results
        self._settings = settings

    def compare(self, request: ComparisonRequest) -> ComparisonResponse:
        if request.comparison_type is not ComparisonType.cells:
            # The enum currently only exposes "cells"; this guard keeps the
            # contract honest if "regions" is added before it is implemented.
            raise IncompatibleComparisonError(
                f"Comparison type '{request.comparison_type.value}' is not implemented.",
                comparison_type=request.comparison_type.value,
            )

        if len(request.cell_ids) > self._settings.max_comparison_cells:
            raise IncompatibleComparisonError(
                f"At most {self._settings.max_comparison_cells} cells can be compared at once.",
                requested=len(request.cell_ids),
            )

        result = self._results.get_result(request.result_id)
        primary = result.variables[0]
        datasets = {
            dataset.cell_id: dataset
            for dataset in build_cell_datasets(
                primary.variable_id,
                result.analysis.aoi.canonical(),
                result.analysis.start_month,
                result.analysis.end_month,
                seed_key=result.result_id,
            )
        }

        selected: list[CellDataset] = []
        for cell_id in request.cell_ids:
            dataset = datasets.get(cell_id)
            if dataset is None:
                raise CellNotFoundError(cell_id, result.result_id)
            if dataset.missing:
                raise IncompatibleComparisonError(
                    f"Cell '{cell_id}' has no data and cannot be compared.",
                    cell_id=cell_id,
                    result_id=result.result_id,
                )
            selected.append(dataset)

        trend_unit = primary.trend.slope_unit or f"{primary.unit} year-1"
        compatibility = CompatibilityReport(
            variable_match=True,
            unit_match=True,
            period_match=True,
            method_version_match=True,
            dataset_revision_match=True,
            compatible=True,
            notes=[
                "All selected cells belong to the same result, so variable, unit, period, "
                "method version and dataset revision are identical by construction.",
                "Comparability of different variables or periods is not supported yet.",
            ],
        )

        cells = [
            ComparisonCell(
                cell_id=dataset.cell_id,
                label=f"{dataset.cell_id} ({dataset.centroid[0]:.2f}, {dataset.centroid[1]:.2f})",
                bbox=list(dataset.bbox),
                trend_value=dataset.slope,
                trend_unit=trend_unit,
                direction=dataset.direction,
                evidence_state=dataset.evidence_state,
                missing_data=dataset.missing,
            )
            for dataset in selected
        ]

        series = self._aligned_series(selected)
        deltas = self._deltas(selected)
        summary = self._summary(selected, trend_unit)

        comparison_id = "cmp_mock_" + hashlib.sha256(
            f"{result.result_id}:{','.join(request.cell_ids)}".encode("utf-8")
        ).hexdigest()[:8]

        return ComparisonResponse(
            comparison_id=comparison_id,
            comparison_type=ComparisonType.cells,
            result_id=result.result_id,
            variable_id=primary.variable_id,
            display_name=primary.display_name,
            unit=primary.unit,
            trend_unit=trend_unit,
            start_month=result.analysis.start_month,
            end_month=result.analysis.end_month,
            compatibility=compatibility,
            cells=cells,
            series=series,
            deltas=deltas,
            summary=summary,
            warnings=[
                "Comparison values are synthetic. A difference between cells is descriptive, "
                "not evidence of a statistically significant spatial contrast.",
            ],
        )

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _aligned_series(datasets: list[CellDataset]) -> list[ComparisonSeriesPoint]:
        months = [point.month for point in datasets[0].series]
        by_cell = {
            dataset.cell_id: {point.month: point.value for point in dataset.series}
            for dataset in datasets
        }
        return [
            ComparisonSeriesPoint(
                month=month,
                values={cell_id: values.get(month) for cell_id, values in by_cell.items()},
            )
            for month in months
        ]

    @staticmethod
    def _deltas(datasets: list[CellDataset]) -> list[ComparisonDelta]:
        baseline = datasets[0].slope
        deltas: list[ComparisonDelta] = []
        for dataset in datasets:
            if dataset.slope is None or baseline is None:
                deltas.append(
                    ComparisonDelta(cell_id=dataset.cell_id, difference_from_first=None, percent_difference=None)
                )
                continue
            difference = round(dataset.slope - baseline, 6)
            percent = None if baseline == 0 else round((difference / abs(baseline)) * 100.0, 2)
            deltas.append(
                ComparisonDelta(
                    cell_id=dataset.cell_id,
                    difference_from_first=difference,
                    percent_difference=percent,
                )
            )
        return deltas

    @staticmethod
    def _summary(datasets: list[CellDataset], trend_unit: str) -> str:
        parts = [
            f"{dataset.cell_id}: {dataset.slope:+.4f} {trend_unit}"
            for dataset in datasets
            if dataset.slope is not None
        ]
        return (
            "Synthetic slopes for the selected cells - " + "; ".join(parts) + "."
            if parts
            else "No comparable slopes were available for the selected cells."
        )
