"""Spatial representations of stored science arrays; never generate replacement data."""

import numpy as np
from app.adapters.science import (
    SCIENCE_LOCK,
    DISCLAIMER,
    ScienceStatisticsAdapter,
    direction,
)
from app.schemas.common import EvidenceState
from app.schemas.spatial import (
    SpatialResponse,
    SpatialCell,
    CellDetailResponse,
    CellGeometry,
)
from app.schemas.results import TimeSeriesPoint, TrendSummary
from app.schemas.analysis import AnalysisSpec
from app.core.exceptions import CellNotFoundError


def cells(result):
    primary = result.variables[0]
    artifact = result.science[primary.variable_id]
    lat, lon = artifact["lat"], artifact["lon"]
    # Cell-centre footprints use native spacing, not a stretched synthetic grid.
    meta = artifact["metadata"]
    dy, dx = artifact["native_spacing_degrees"]
    for row, y in enumerate(lat):
        for col, x in enumerate(lon):
            value = artifact["annual_slope"][row][col]
            bbox = [x - dx / 2, y - dy / 2, x + dx / 2, y + dy / 2]
            w, s, e, n = bbox
            yield SpatialCell(
                cell_id=f"cell_{row}_{col}",
                result_id=result.result_id,
                variable_id=primary.variable_id,
                bbox=bbox,
                centroid=[x, y],
                geometry=CellGeometry(
                    coordinates=[[[w, s], [e, s], [e, n], [w, n], [w, s]]]
                ),
                trend_value=value,
                trend_unit=primary.trend.slope_unit,
                direction=direction(value),
                evidence_state=EvidenceState.descriptive_only,
                missing_data=value is None,
                data_mode="real",
            )


def spatial(result):
    primary = result.variables[0]
    items = list(cells(result))
    return SpatialResponse(
        result_id=result.result_id,
        variable_id=primary.variable_id,
        unit=primary.unit,
        trend_unit=primary.trend.slope_unit,
        grid="native_source_grid",
        cell_count=len(items),
        missing_cell_count=sum(c.missing_data for c in items),
        bounds=result.analysis.aoi.canonical(),
        cells=items,
        data_mode="real",
        disclaimer=DISCLAIMER,
        warnings=result.warnings,
    )


def cell_detail(result, cell_id, data):
    item = next((c for c in cells(result) if c.cell_id == cell_id), None)
    if item is None:
        raise CellNotFoundError(cell_id, result.result_id)
    from app.services.analysis_service import spec_from_result
    from packages.science.src.trend_estimation import annual_elapsed_years, trend_series

    primary = result.variables[0]
    with SCIENCE_LOCK:
        p, _ = ScienceStatisticsAdapter(data).prepare(
            spec_from_result(result, data), primary.variable_id
        )
        _, r, c = cell_id.split("_")
        row, col = int(r), int(c)
        annual = p.cell_annual.isel(lat=row, lon=col)
        tr = trend_series(annual.values, annual_elapsed_years(p.year))
        monthly = p.cell_monthly.isel(lat=row, lon=col)
        series = [
            TimeSeriesPoint(
                month=m,
                value=float(v) if np.isfinite(v) else None,
                missing=not np.isfinite(v),
            )
            for m, v in zip(
                p.time.values.astype("datetime64[M]").astype(str), monthly.values
            )
        ]
    return CellDetailResponse(
        cell_id=cell_id,
        result_id=result.result_id,
        variable_id=primary.variable_id,
        display_name=primary.display_name,
        unit=primary.unit,
        bbox=item.bbox,
        centroid=item.centroid,
        geometry=item.geometry,
        missing_data=item.missing_data,
        evidence_state=EvidenceState.descriptive_only,
        trend=TrendSummary(
            method_id="theil_sen",
            method_version=result.method.method_version,
            direction=item.direction,
            slope_per_year=tr["slope_per_year"],
            slope_unit=item.trend_unit,
            n_months=sum(not x.missing for x in series),
            n_years=tr["n_valid"],
            inference_status="not_computed",
            evidence_state=EvidenceState.descriptive_only,
        ),
        series=series,
        data_mode="real",
        disclaimer=DISCLAIMER,
        warnings=result.warnings,
    )
