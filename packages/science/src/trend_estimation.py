"""Exact descriptive Theil–Sen slopes with mandatory elapsed-year coordinates.

Repairs the reviewed inherited finite-pair median algorithm at the statistics
library boundary. No inference machinery is imported or invoked.
"""
from __future__ import annotations

import numbers
import re

import numpy as np
import xarray as xr


def _ordered_axis(values) -> np.ndarray:
    raw = np.asarray(values)
    if raw.ndim != 1 or raw.dtype.kind not in "iuf":
        raise ValueError("Time must be a one-dimensional numeric elapsed-year axis")
    result = raw.astype("float64")
    if not np.all(np.isfinite(result)) or not np.all(np.diff(result) > 0):
        raise ValueError("Time must be finite, unique and strictly increasing")
    return result


def monthly_elapsed_years(time) -> np.ndarray:
    """Calendar-month intervals, not implicit row indices or a 365-day year.

    Source times within a month label the same monthly aggregate. Gaps retain
    their true calendar-month distance; sub-month timestamp offsets are ignored.
    """
    if isinstance(time, xr.DataArray) and time.encoding.get("calendar", "standard") not in (
            "standard", "gregorian", "proleptic_gregorian"):
        raise ValueError("Only Gregorian monthly coordinates are supported")
    values = np.asarray(time)
    if values.ndim != 1:
        raise ValueError("Expected a one-dimensional month coordinate")
    if values.dtype.kind in "US":
        if any(not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", str(v)) for v in values):
            raise ValueError("String months must be YYYY-MM")
        values = values.astype("datetime64[M]")
    if values.dtype.kind != "M" or np.any(np.isnat(values)):
        raise ValueError("Expected decoded Gregorian timestamps or YYYY-MM labels")
    ordinals = values.astype("datetime64[M]").astype("int64")
    _ordered_axis(ordinals)
    return (ordinals - ordinals[0]).astype("float64") / 12 if len(ordinals) else np.empty(0)


def annual_elapsed_years(years) -> np.ndarray:
    values = _ordered_axis(years)
    if np.any(values != np.floor(values)) or np.any((values < 1) | (values > 9999)):
        raise ValueError("Expected actual integer calendar-year labels")
    return values - values[0] if values.size else values


def sen_slopes(values, elapsed_years, *, min_points: int = 3, batch_size: int = 64) -> dict:
    """One shared scalar/grid kernel, first dimension time; exact, no sampling.

    `min_points` is a computability guard only, not a validated scientific
    record-length threshold. Missing y values stay missing; infinite y is an
    input error. Time is validated before masking, so gaps never compress.
    """
    time = _ordered_axis(elapsed_years)
    if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Integral) or v < lower
           for v, lower in ((min_points, 2), (batch_size, 1))):
        raise ValueError("min_points must be an integer >=2 and batch_size >=1")
    raw = np.asarray(values)
    if raw.ndim < 1 or raw.shape[0] != time.size or raw.dtype.kind not in "iuf":
        raise ValueError("Numeric values must have time as their first axis")
    if time.size > 2048:
        raise ValueError("Exact pairwise kernel supports at most 2048 time samples per call")
    data = raw.astype("float64").reshape(time.size, int(np.prod(raw.shape[1:])) if raw.ndim > 1 else 1)
    if np.isinf(data).any():
        raise ValueError("Infinite observations are invalid; NaN denotes missing")
    count = np.isfinite(data).sum(axis=0)
    good_columns = np.flatnonzero(count >= min_points)
    slopes = np.full(data.shape[1], np.nan)
    span = np.full(data.shape[1], np.nan)
    for k in np.flatnonzero(count):
        valid = np.flatnonzero(np.isfinite(data[:, k]))
        span[k] = time[valid[-1]] - time[valid[0]]
    first, last = np.triu_indices(time.size, 1)
    dt = time[last] - time[first]
    # Bound temporary pair-value storage to roughly 2 million float64 entries.
    block = min(int(batch_size), max(1, 2_000_000 // max(1, len(dt))))
    for start in range(0, len(good_columns), block):
        cols = good_columns[start:start + block]
        selected = data[:, cols]
        with np.errstate(over="raise", invalid="raise", divide="raise"):
            pairs = (selected[last] - selected[first]) / dt[:, None]
        slopes[cols] = np.nanmedian(pairs, axis=0, overwrite_input=True)
    if not np.isfinite(slopes[good_columns]).all():
        raise FloatingPointError("Nonfinite slope for an otherwise computable series")
    shape = raw.shape[1:]
    return {"slope": slopes.reshape(shape), "n_valid": count.reshape(shape),
            "valid_span_years": span.reshape(shape),
            "pair_count": (count * (count - 1) // 2).reshape(shape),
            "computable": (count >= min_points).reshape(shape)}


def trend_series(values, elapsed_years, *, min_points: int = 3) -> dict:
    values = np.asarray(values)
    if values.ndim != 1:
        raise ValueError("Regional/individual-cell input must be one-dimensional")
    result = sen_slopes(values, elapsed_years, min_points=min_points)
    computed = bool(result["computable"])
    span = float(result["valid_span_years"])
    return {"slope_per_year": float(result["slope"]) if computed else None,
            "n_valid": int(result["n_valid"]), "pair_count": int(result["pair_count"]),
            "valid_span_years": span if np.isfinite(span) else None,
            "status": "computed_descriptive" if computed else "insufficient_data",
            "minimum_valid_observations": min_points, "inference_status": "not_computed"}


def cell_trends(cells: xr.DataArray, *, frequency: str, min_points: int = 3) -> xr.Dataset:
    axis = "time" if frequency == "monthly" else "year" if frequency == "annual" else None
    if axis is None or cells.dims != (axis, "lat", "lon") or cells.attrs.get("units") is None:
        raise ValueError("Expected explicitly labeled monthly/annual cells and source units")
    time = monthly_elapsed_years(cells.time) if axis == "time" else annual_elapsed_years(cells.year)
    result = sen_slopes(cells.values, time, min_points=min_points)
    out = xr.Dataset({name: (("lat", "lon"), value.astype("int8") if name == "computable" else value)
                      for name, value in result.items()}, coords={"lat": cells.lat, "lon": cells.lon})
    out.slope.attrs = {"units": f"{cells.attrs['units']} per year", "long_name": "descriptive Theil-Sen slope"}
    out.valid_span_years.attrs["units"] = "years"
    for name in ("n_valid", "pair_count", "computable"):
        out[name].attrs["units"] = "1"
    out.attrs = {"frequency": frequency, "minimum_valid_observations": min_points,
                 "inference_status": "not_computed", "estimator": "exact Theil-Sen finite-pair median"}
    return out
