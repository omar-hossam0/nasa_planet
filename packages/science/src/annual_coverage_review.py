"""Annual diagnostics for prepared NDVI with potentially changing monthly support.

Two estimands are deliberately separate: a day-weighted mean of twelve regional
monthly means, and an area mean of cells each observed in all twelve months of
that year. Neither reconstructs a missing observation.
"""
from __future__ import annotations

import numpy as np
import xarray as xr

from .preprocessing import annual_summary, validate_month_axis


def annual_support_review(cells: xr.DataArray, region: xr.DataArray,
                          eligible: xr.DataArray, weights: xr.DataArray) -> xr.Dataset:
    validate_month_axis(cells)
    validate_month_axis(region)
    if cells.dims != ("time", "lat", "lon") or region.dims != ("time",):
        raise ValueError("Expected monthly cells (time, lat, lon) and region (time)")
    if eligible.dims != ("lat", "lon") or weights.dims != ("lat", "lon"):
        raise ValueError("Expected spatial eligibility and weights")
    cells, region, eligible, weights = xr.align(cells, region, eligible, weights, join="exact")
    if not bool(np.isfinite(eligible).all()) or not bool(((eligible == 0) | (eligible == 1)).all()):
        raise ValueError("Eligibility must be a binary mask")
    eligible = eligible.astype(bool)
    if bool(np.isinf(cells).any()) or bool(np.isinf(region).any()):
        raise ValueError("Infinite NDVI is invalid")
    if not bool(np.isfinite(weights).all()) or bool((weights <= 0).any()):
        raise ValueError("Weights must be finite and positive")
    if bool(cells.where(~eligible).notnull().any()):
        raise ValueError("Prepared cells contain finite observations outside eligibility")
    valid = cells.notnull()
    area = weights.where(valid, 0).sum(("lat", "lon"))
    normalized = weights.where(valid, 0) / area.where(area > 0)
    recomputed = (cells * normalized).sum(("lat", "lon"), min_count=1)
    if not np.allclose(region, recomputed, rtol=0, atol=1e-12, equal_nan=True):
        raise ValueError("Regional monthly mean does not match observed-cell area weights")

    counts = valid.groupby("time.year").sum("time")
    complete = (counts == 12) & eligible
    cell_annual = annual_summary(cells, "vegetation_greenness")
    regional_annual = annual_summary(region, "vegetation_greenness")
    complete_area = weights.where(complete, 0).sum(("lat", "lon"))
    complete_weights = weights.where(complete, 0) / complete_area.where(complete_area > 0)
    complete_cell_mean = (cell_annual * complete_weights).sum(("lat", "lon"), min_count=1)
    result = xr.Dataset({
        "cell_annual": cell_annual,
        "regional_annual_from_monthly": regional_annual,
        "regional_annual_complete_cell_years": complete_cell_mean,
        "valid_month_count_by_cell_year": counts,
        "complete_cell_year": complete.astype("int8"),
        "incomplete_eligible_cell_count": (eligible & ~complete).sum(("lat", "lon")),
        "complete_cell_count": complete.sum(("lat", "lon")),
        "complete_cell_area_fraction_selected": (complete_area / weights.sum()).clip(0, 1),
        "observed_area_fraction_selected": (area / weights.sum()).clip(0, 1),
    }, attrs={"status": "annual preparation review; default unchanged", "imputation": "none",
              "annual_valid_month_requirement": 12, "inference_status": "not_computed",
              "regional_annual_interpretation": "day-weighted mean of twelve possibly changing-support regional monthly means",
              "complete_cell_year_interpretation": "diagnostic area mean of complete cell annual values; footprint may change between years"})
    for name in result.data_vars:
        result[name].attrs.setdefault("units", "1")
    result.valid_month_count_by_cell_year.attrs["units"] = "months"
    result.incomplete_eligible_cell_count.attrs["units"] = "cells"
    result.complete_cell_count.attrs["units"] = "cells"
    return result
