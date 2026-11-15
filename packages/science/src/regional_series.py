"""Native-centre bbox selection and fixed-support spherical area means."""
from __future__ import annotations

from dataclasses import dataclass
import numbers

import numpy as np
import xarray as xr


@dataclass(frozen=True)
class BoundingBox:
    west: float
    south: float
    east: float
    north: float

    def __post_init__(self):
        values = (self.west, self.south, self.east, self.north)
        if any(isinstance(v, (bool, np.bool_)) or not isinstance(v, numbers.Real) or not np.isfinite(v) for v in values):
            raise ValueError("Bounding-box coordinates must be finite real numbers")
        if not (-180 <= self.west < self.east <= 180 and -90 <= self.south < self.north <= 90):
            raise ValueError("Invalid bbox; longitude wrapping and antimeridian crossing are unsupported")

    def as_list(self) -> list[float]:
        return [float(self.west), float(self.south), float(self.east), float(self.north)]


def select_bbox(ds: xr.Dataset, bbox: BoundingBox, supported: BoundingBox) -> xr.Dataset:
    if bbox.west < supported.west or bbox.east > supported.east or bbox.south < supported.south or bbox.north > supported.north:
        raise ValueError("Requested bbox exceeds the registered study rectangle")
    for axis in ("lat", "lon"):
        if axis not in ds.coords or ds[axis].dims != (axis,):
            raise ValueError("Expected one-dimensional geographic coordinates")
        values = ds[axis].values
        if not values.size or not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0):
            raise ValueError("Coordinates must be finite and strictly increasing; implicit wrapping/reversal is unsupported")
    lat, lon = ds.lat, ds.lon
    subset = ds.isel(lat=np.flatnonzero((lat >= bbox.south) & (lat <= bbox.north)),
                     lon=np.flatnonzero((lon >= bbox.west) & (lon <= bbox.east)))
    if not subset.sizes["lat"] or not subset.sizes["lon"]:
        raise ValueError("No native cell centres lie inside the requested bbox")
    return subset


def cell_solid_angles(lat: xr.DataArray, lon: xr.DataArray, spacing: tuple[float, float]) -> xr.DataArray:
    """Relative full-cell areas on a sphere; no Earth-radius assumption needed."""
    dy, dx = spacing
    if not (np.isfinite(dy) and np.isfinite(dx) and 0 < dy <= 180 and 0 < dx <= 360):
        raise ValueError("Invalid native grid spacing")
    for axis, expected in ((lat, dy), (lon, dx)):
        values = axis.values
        if not values.size or not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0):
            raise ValueError("Area weights require finite ascending native axes")
        if values.size > 1 and not np.allclose(np.diff(values), expected, rtol=1e-4, atol=1e-5):
            raise ValueError("Native coordinate spacing differs from the registered product")
    if np.any((lat.values < -90) | (lat.values > 90)) or np.any((lon.values < -180) | (lon.values > 180)):
        raise ValueError("Coordinates outside supported geographic convention")
    south = np.deg2rad(np.maximum(lat.values - dy / 2, -90))
    north = np.deg2rad(np.minimum(lat.values + dy / 2, 90))
    weights = (np.sin(north) - np.sin(south))[:, None] * np.full((1, lon.size), np.deg2rad(dx))
    return xr.DataArray(weights, dims=("lat", "lon"), coords={"lat": lat, "lon": lon},
                        name="native_cell_solid_angle", attrs={"units": "sr", "boundary_treatment": "full native cells selected by centre; no bbox intersection"})


def fixed_support_mean(reference: xr.DataArray, weights: xr.DataArray) -> xr.Dataset:
    if reference.dims != ("time", "lat", "lon") or not reference.sizes["time"]:
        raise ValueError("Expected nonempty (time, lat, lon) reference")
    if weights.dims != ("lat", "lon"):
        raise ValueError("Expected (lat, lon) area weights")
    reference, weights = xr.align(reference, weights, join="exact")
    if not np.all(np.isfinite(weights)) or bool((weights <= 0).any()):
        raise ValueError("Weights must be finite and positive")
    valid = np.isfinite(reference)
    support = valid.all("time")
    support_weights = weights.where(support, 0)
    denominator = support_weights.sum()
    normalized = support_weights / denominator.where(denominator > 0)
    cells = reference.where(support)
    region = (cells * normalized).sum(("lat", "lon"), skipna=True, min_count=1)
    region.attrs = dict(reference.attrs)
    selected_area = weights.sum()
    before_fraction = weights.where(valid, 0).sum(("lat", "lon")) / selected_area
    result = xr.Dataset({
        "cell_monthly": cells, "regional_monthly": region,
        "fixed_support": support.astype("int8"),
        "normalized_support_weight": normalized,
        "native_cell_solid_angle": weights,
        "qa_valid_fraction_by_cell": valid.mean("time"),
        "qa_valid_area_fraction_by_month": before_fraction,
    }, attrs={"support_rule": "valid in every full registered reference month; unchanged for subperiod requests"})
    result.fixed_support.attrs = {
        "units": "1", "long_name": "fixed reference support mask",
        "flag_values": np.array([0, 1], dtype="int8"), "flag_meanings": "excluded retained",
    }
    result.normalized_support_weight.attrs = {
        "units": "1", "long_name": "fractional contribution to the fixed-support regional mean",
    }
    result.qa_valid_fraction_by_cell.attrs = {
        "units": "1", "long_name": "fraction of reference months with a QA-valid value in each cell",
    }
    result.qa_valid_area_fraction_by_month.attrs = {
        "units": "1", "long_name": "QA-valid fraction of selected native-cell area in each month",
    }
    return result
