"""Read-only access to the bundled cubes through the explicit input contract.

This module decodes CF missing values and preserves ancillary QA fields. It
does not choose a QA threshold, aggregate a region or run a trend test.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import xarray as xr

REPOSITORY = Path(__file__).resolve().parents[3]
SCOPE = Path("docs/architecture/scope.v2.json")
SUPPORTED_CALENDARS = {"standard", "gregorian", "proleptic_gregorian"}


def calendar_months(start: str, end: str) -> list[str]:
    def index(value: str) -> int:
        if (len(value) != 7 or value[4] != "-" or not value.isascii()
                or not value[:4].isdigit() or not value[5:].isdigit()):
            raise ValueError(f"Expected YYYY-MM, received {value!r}")
        year, month = map(int, value.split("-"))
        if not 1 <= month <= 12 or not 1 <= year <= 9999:
            raise ValueError(f"Invalid calendar month: {value}")
        return year * 12 + month - 1

    first, last = index(start), index(end)
    if first > last:
        raise ValueError("Period start follows period end")
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in range(first, last + 1)]


def input_entry(variable_id: str, region_id: str, *, root: Path = REPOSITORY) -> dict:
    scope = json.loads((root / SCOPE).read_text(encoding="utf-8"))
    matches = [entry for entry in scope["entries"]
               if entry["variable_id"] == variable_id and entry["region_id"] == region_id]
    if len(matches) != 1:
        raise ValueError("Expected one registered variable/region pair")
    entry = dict(matches[0])
    for field in ("product_id", "version", "source_variable", "cube_variable", "cube_units", "cube_file"):
        if not entry.get(field):
            raise ValueError(f"Missing explicit input contract field: {field}")
    return entry


def validate_cube(ds: xr.Dataset, entry: dict) -> None:
    name = entry["cube_variable"]
    if name not in ds.data_vars:
        raise ValueError(f"Registered cube field {name!r} is absent")
    if ds[name].dims != ("time", "lat", "lon"):
        raise ValueError("Expected variable dimensions (time, lat, lon)")
    if ds[name].attrs.get("units") != entry["cube_units"]:
        raise ValueError("Cube units differ from the registered units")
    if ds.attrs.get("product") != entry["product_id"]:
        raise ValueError("Cube product differs from the registered product")
    if any(ds.sizes.get(axis, 0) == 0 for axis in ("time", "lat", "lon")):
        raise ValueError("Cube contains an empty dimension")
    for axis in ("time", "lat", "lon"):
        if axis not in ds.coords or ds[axis].dims != (axis,):
            raise ValueError(f"Expected one-dimensional coordinate: {axis}")
    calendar = ds.time.encoding.get("calendar", "standard")
    if calendar not in SUPPORTED_CALENDARS or not np.issubdtype(ds.time.dtype, np.datetime64):
        raise ValueError("Only decoded Gregorian calendar timestamps are supported")
    actual = [str(value)[:7] for value in ds.time.values]
    if actual != calendar_months(*entry["period"]):
        raise ValueError("Missing, duplicated, out-of-order or out-of-period months")
    west, south, east, north = entry["bbox"]
    for axis, lower, upper in (("lat", south, north), ("lon", west, east)):
        values = ds[axis].values
        if not np.all(np.isfinite(values)) or not np.all(np.diff(values) > 0):
            raise ValueError(f"Coordinate {axis} must be finite and strictly increasing")
        if not np.all((values >= lower) & (values <= upper)):
            raise ValueError(f"Coordinate {axis} extends outside the registered rectangle")
    required_qa = {
        "GPM_3IMERGM": ("precipitationQualityIndex", "randomError"),
        "MOD13C2": ("VI_Quality", "pixel_reliability"),
    }.get(entry["product_id"], ())
    for field in required_qa:
        if field not in ds.data_vars or ds[field].dims != ds[name].dims or ds[field].shape != ds[name].shape:
            raise ValueError(f"Required ancillary field is absent or misaligned: {field}")
    if np.isinf(ds[name].values).any():
        raise ValueError("Infinite values are invalid; missing values must decode to NaN")


def load_cube(variable_id: str, region_id: str, *, root: Path = REPOSITORY) -> xr.Dataset:
    """Return a loaded, validated dataset after closing its underlying file."""
    root = Path(root).resolve()
    entry = input_entry(variable_id, region_id, root=root)
    path = (root / entry["cube_file"]).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Registered cube path escapes the repository")
    with xr.open_dataset(path, decode_cf=True, mask_and_scale=True) as opened:
        validate_cube(opened, entry)
        result = opened.load()
    result.attrs.update({
        "semantic_variable_id": variable_id,
        "registered_region_id": region_id,
        "provider_variable": entry["source_variable"],
        "processed_variable": entry["cube_variable"],
        "registered_product_version": entry["version"],
        "science_input_contract_revision": "1.0",
        "qa_status": "ancillary fields retained; no additional product QA selection applied",
        "inference_status": "not_computed",
    })
    return result


def monthly_precipitation_amount(rate: xr.DataArray) -> xr.DataArray:
    """Integrate an IMERG Gregorian monthly mean mm/hr rate into monthly mm."""
    if rate.attrs.get("units") != "mm/hr":
        raise ValueError("Expected a monthly precipitation rate in mm/hr")
    if "time" not in rate.coords or rate.time.dims != ("time",):
        raise ValueError("Expected a one-dimensional time coordinate")
    if rate.time.encoding.get("calendar", "standard") not in SUPPORTED_CALENDARS:
        raise ValueError("Unsupported calendar for month-duration conversion")
    if not np.issubdtype(rate.time.dtype, np.datetime64):
        raise ValueError("Expected decoded Gregorian timestamps")
    months = [str(value)[:7] for value in rate.time.values]
    if not months or months != calendar_months(months[0], months[-1]):
        raise ValueError("Monthly rate requires ordered, contiguous unique months")
    if np.isinf(rate.values).any() or bool((rate < 0).any()):
        raise ValueError("Precipitation rates must be nonnegative or missing")
    amount = rate * rate.time.dt.days_in_month * 24
    amount.attrs = {
        **rate.attrs,
        "units": "mm",
        "long_name": "monthly accumulated precipitation",
        "source_units": "mm/hr",
        "conversion": "monthly mean rate multiplied by Gregorian calendar-month days and 24 hours/day",
    }
    amount.name = "precipitation_amount"
    return amount
