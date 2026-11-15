"""Experimental MOD13C2 coverage diagnostics; independent of default preparation.

The eligibility footprint is static, but observed contributions within it may
change each month. Missing NDVI is never reconstructed or counted as zero.
"""
from __future__ import annotations

import math

import numpy as np
import xarray as xr

from .preprocessing import validate_month_axis

SEASONS = {"DJF": (12, 1, 2), "MAM": (3, 4, 5),
           "JJA": (6, 7, 8), "SON": (9, 10, 11)}
QA_FIELDS = {"modland": (0, 3), "usefulness": (2, 15), "aerosol": (6, 3),
             "adjacent_cloud": (8, 1), "brdf_correction": (9, 1),
             "mixed_cloud": (10, 1), "land_water": (11, 7),
             "cmg_geospatial": (14, 3)}


def decode_cmg_quality(quality: np.ndarray) -> dict[str, np.ndarray]:
    """C61 guide Tables 5/17; upper bits are CMG coverage, not snow/shadow.

    Invalid/fill words receive -1 in every field, never plausible good flags.
    """
    quality = np.asarray(quality)
    valid = (np.isfinite(quality) & (quality >= 0) & (quality < 65535)
             & (quality == np.floor(quality)))
    words = np.where(valid, quality, 0).astype("uint16")
    return {name: np.where(valid, ((words >> shift) & mask).astype("int16"), -1).astype("int8")
            for name, (shift, mask) in QA_FIELDS.items()}


def coverage_experiment(reference: xr.DataArray, weights: xr.DataArray,
                        coverage: float) -> xr.Dataset:
    """Apply full-reference cell eligibility, then observed-area monthly means.

    Coverage is a fraction of all registered months per cell, NOT the fraction
    of area required in each month and NOT a per-season coverage requirement.
    """
    validate_month_axis(reference)
    if reference.dims != ("time", "lat", "lon") or weights.dims != ("lat", "lon"):
        raise ValueError("Expected (time, lat, lon) values and (lat, lon) weights")
    if isinstance(coverage, (bool, np.bool_)) or not np.isfinite(coverage) or not 0 < coverage <= 1:
        raise ValueError("Coverage must be a finite fraction in (0, 1]")
    reference, weights = xr.align(reference, weights, join="exact")
    if bool(np.isinf(reference).any()) or not bool(np.isfinite(weights).all()) or bool((weights <= 0).any()):
        raise ValueError("Values cannot be infinite; weights must be finite and positive")
    # Subtract only floating-point roundoff before ceil; no relaxed percentage.
    required = math.ceil(float(coverage) * reference.sizes["time"] - 1e-12)
    valid = np.isfinite(reference)
    eligible = valid.sum("time") >= required
    observed = valid & eligible
    cells = reference.where(eligible)
    observed_area = weights.where(observed, 0).sum(("lat", "lon"))
    eligible_area = weights.where(eligible, 0).sum()
    normalized = weights.where(observed, 0) / observed_area.where(observed_area > 0)
    monthly = (cells * normalized).sum(("lat", "lon"), skipna=True, min_count=1)
    monthly.attrs = {"units": "1", "long_name": "NDVI mean over observed eligible native-cell area"}
    out = xr.Dataset({
        "cell_monthly": cells,
        "regional_monthly": monthly,
        "eligible_support": eligible.astype("int8"),
        "observed_support": observed.astype("int8"),
        "normalized_observed_weight": normalized,
        "native_cell_solid_angle": weights,
        "valid_reference_month_count": valid.sum("time"),
        "observed_cell_count": observed.sum(("lat", "lon")),
        "observed_area_fraction_selected": (observed_area / weights.sum()).clip(0, 1),
        "observed_area_fraction_eligible": (observed_area / eligible_area.where(eligible_area > 0)).clip(0, 1),
    }, attrs={"experiment_revision": "sahel-qa-review-1.0", "coverage_threshold": coverage,
              "required_valid_reference_months": required,
              "reference_month_count": reference.sizes["time"],
              "support_reference_start": str(reference.time.values[0])[:7],
              "support_reference_end": str(reference.time.values[-1])[:7],
              "eligibility": "static full-reference cell valid-month count",
              "aggregation": "monthly area weights renormalized over observed eligible cells",
              "imputation": "none", "inference_status": "not_computed",
              "status": "experimental; default policy unchanged"})
    for name in out.data_vars:
        if name != "native_cell_solid_angle":
            out[name].attrs.setdefault("units", "1")
    out.valid_reference_month_count.attrs["units"] = "months"
    out.observed_cell_count.attrs["units"] = "cells"
    return out


def distribution(values: np.ndarray) -> dict:
    values = np.asarray(values, dtype="float64")
    values = values[np.isfinite(values)]
    if not values.size:
        return {"count": 0, "min": None, "mean": None, "max": None, "p05": None, "p50": None, "p95": None}
    return {"count": int(values.size), "min": float(values.min()), "mean": float(values.mean()),
            "max": float(values.max()), **{f"p{p:02}": float(np.percentile(values, p)) for p in (5, 50, 95)}}


def missingness_groups(observed: np.ndarray, eligible: np.ndarray,
                       weights: np.ndarray, months: np.ndarray) -> dict:
    """Count and area-time denominators explicitly exclude ineligible cells.

    Seasons pool constituent calendar months over all years; no winter-year
    assignment, seasonal averaging of NDVI or unobserved values is introduced.
    """
    observed = np.asarray(observed, dtype=bool)
    eligible = np.asarray(eligible, dtype=bool)
    weights, months = np.asarray(weights), np.asarray(months)
    footprint = float(weights[eligible].sum())
    ncell = int(eligible.sum())

    def group(mask):
        subset = observed[mask]
        total = int(mask.sum()) * ncell
        observed_count = int(subset.sum())
        areas = (subset * weights).sum(axis=(1, 2))
        area_time = int(mask.sum()) * footprint
        missing_area = float(((eligible & ~subset) * weights).sum())
        counts_by_cell = subset.sum(axis=0)[eligible]
        return {"month_count": int(mask.sum()), "eligible_cell_months": total,
                "observed_cell_months": observed_count, "missing_cell_months": total - observed_count,
                "missing_cell_month_fraction": (total - observed_count) / total if total else None,
                "missing_area_time_fraction": missing_area / area_time if area_time else None,
                "observed_area_fraction_eligible": distribution(np.clip(areas / footprint, 0, 1) if footprint else []),
                "per_cell_observed_fraction": distribution(counts_by_cell / int(mask.sum()) if mask.any() else []),
                "eligible_cells_with_no_observations_in_group": int((counts_by_cell == 0).sum()) if mask.any() else None,
                "eligible_cells_with_incomplete_group": int((counts_by_cell < int(mask.sum())).sum()) if mask.any() else None}

    return {"calendar_month": {str(m): group(months == m) for m in range(1, 13)},
            "season": {s: group(np.isin(months, mm)) for s, mm in SEASONS.items()}}
