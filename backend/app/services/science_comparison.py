"""Cell comparisons consume the same stored/recomputed science values as cell detail."""

from app.adapters.science import ScienceDataAdapter, DISCLAIMER
from app.services.science_spatial import cell_detail
from app.schemas.comparison import (
    ComparisonCell,
    ComparisonDelta,
    ComparisonResponse,
    ComparisonSeriesPoint,
    CompatibilityReport,
)
from app.core.exceptions import IncompatibleComparisonError


def compare(result, request, settings):
    data = ScienceDataAdapter(settings.regions_file)
    items = [cell_detail(result, key, data) for key in request.cell_ids]
    if any(item.missing_data for item in items):
        raise IncompatibleComparisonError(
            "A selected cell has no valid descriptive estimate."
        )
    first = items[0].trend.slope_per_year
    series = [
        ComparisonSeriesPoint(
            month=point.month,
            values={item.cell_id: item.series[index].value for item in items},
        )
        for index, point in enumerate(items[0].series)
    ]
    cells = [
        ComparisonCell(
            cell_id=item.cell_id,
            label=item.cell_id,
            bbox=item.bbox,
            trend_value=item.trend.slope_per_year,
            trend_unit=item.trend.slope_unit,
            direction=item.trend.direction,
            evidence_state=item.evidence_state,
            missing_data=False,
        )
        for item in items
    ]
    return ComparisonResponse(
        comparison_id="cmp_" + result.result_id + "_" + "_".join(request.cell_ids),
        comparison_type=request.comparison_type,
        result_id=result.result_id,
        variable_id=items[0].variable_id,
        display_name=items[0].display_name,
        unit=items[0].unit,
        trend_unit=items[0].trend.slope_unit,
        start_month=result.analysis.start_month,
        end_month=result.analysis.end_month,
        compatibility=CompatibilityReport(
            variable_match=True,
            unit_match=True,
            period_match=True,
            method_version_match=True,
            dataset_revision_match=True,
            compatible=True,
            notes=["Same source, QA footprint and method."],
        ),
        cells=cells,
        series=series,
        deltas=[
            ComparisonDelta(
                cell_id=item.cell_id,
                difference_from_first=item.trend.slope_per_year - first,
                percent_difference=(
                    None
                    if first == 0
                    else (item.trend.slope_per_year - first) / abs(first) * 100
                ),
            )
            for item in items
        ],
        summary="Descriptive comparison; no statistical significance claim.",
        warnings=[DISCLAIMER],
        data_mode="real",
        disclaimer=DISCLAIMER,
    )
