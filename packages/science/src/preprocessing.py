"""Explicit source QA and calendar preparation; no trend/inference methods."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import xarray as xr

from .data_loader import REPOSITORY, calendar_months, monthly_precipitation_amount

POLICY_PATH = REPOSITORY / "packages/science/config/preparation_policy.json"


def load_policy(path: Path = POLICY_PATH) -> dict:
    policy = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_policy(policy)
    return policy


def validate_policy(policy: dict) -> None:
    if policy["qa"]["modis_mode"] not in ("strict", "standard"):
        raise ValueError("Unknown MODIS QA mode")
    if policy["coverage"]["fixed_support"] != "valid_after_qa_in_every_registered_reference_month":
        raise ValueError("Only complete fixed-reference support is implemented")
    if policy["coverage"]["annual_required_months"] != 12:
        raise ValueError("Only complete calendar years are implemented")
    required = {
        ("spatial", "selection"): "native_cell_centres_inclusive_bbox",
        ("spatial", "weighting"): "full_native_spherical_cell_solid_angle",
        ("spatial", "boundary_intersection"): False,
        ("spatial", "longitude_convention"): "-180_to_180_no_wrap",
        ("coverage", "support_reference"): "full_source_period_from_input_contract",
        ("coverage", "minimum_support_cells"): 1,
        ("coverage", "minimum_area_fraction"): None,
        ("coverage", "imputation"): "none",
        ("qa", "imerg_quality_threshold"): None,
        ("qa", "imerg_quality_weighting"): False,
        ("qa", "retain_ancillary_fields"): True,
        ("temporal", "precipitation_monthly_basis"): "calendar_month_amount_mm",
        ("temporal", "precipitation_annual"): "sum_complete_monthly_amounts",
        ("temporal", "other_annual"): "calendar_day_weighted_mean_of_complete_monthly_values",
        ("temporal", "anomaly_baseline"): "arithmetic_mean_per_calendar_month_over_registered_reference",
        ("temporal", "annual_coordinate"): "actual_calendar_year",
    }
    for (section, key), expected in required.items():
        if policy[section][key] != expected:
            raise ValueError(f"Unsupported policy setting: {section}.{key}")


def policy_hash(policy: dict) -> str:
    return hashlib.sha256(json.dumps(policy, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def validate_month_axis(data: xr.DataArray) -> list[str]:
    if "time" not in data.coords or data.time.dims != ("time",) or not data.sizes.get("time"):
        raise ValueError("Expected a nonempty one-dimensional monthly time axis")
    if not np.issubdtype(data.time.dtype, np.datetime64):
        raise ValueError("Expected decoded Gregorian timestamps")
    if data.time.encoding.get("calendar", "standard") not in ("standard", "gregorian", "proleptic_gregorian"):
        raise ValueError("Unsupported calendar")
    months = [str(value)[:7] for value in data.time.values]
    if months != calendar_months(months[0], months[-1]):
        raise ValueError("Monthly axis has gaps, duplicates or reversed dates")
    return months


def apply_product_qa(ds: xr.Dataset, entry: dict, policy: dict) -> tuple[xr.Dataset, dict]:
    """Mask analysis values, retaining unmodified ancillary fields and input."""
    validate_policy(policy)
    name, product = entry["cube_variable"], entry["product_id"]
    data = ds[name]
    mask = np.isfinite(data)
    if product in ("GLDAS_NOAH025_M", "GPM_3IMERGM"):
        mask = mask & (data >= 0)
    elif product == "MOD13C2":
        quality, reliability = xr.align(ds["VI_Quality"], ds["pixel_reliability"], join="exact")
        if quality.dims != data.dims or reliability.dims != data.dims:
            raise ValueError("MODIS QA dimensions differ from NDVI")
        q, r = quality.values, reliability.values
        q_valid = np.isfinite(q) & (q >= 0) & (q < policy["qa"]["modis_quality_fill"]) & (q == np.floor(q))
        r_valid = np.isfinite(r) & (r == np.floor(r))
        bits = np.where(q_valid, q, 0).astype("uint16") & 3
        mode = policy["qa"]["modis_mode"]
        accepted = policy["qa"]["modis_modes"][mode]
        flags = q_valid & r_valid & np.isin(bits, accepted["accepted_modland_bits"]) & np.isin(r, accepted["accepted_reliability"])
        lower, upper = policy["qa"]["modis_processed_ndvi_range"]
        mask = mask & (data >= lower) & (data <= upper) & xr.DataArray(flags, dims=data.dims, coords=data.coords)
    elif product != "M2TMNXSLV":
        raise ValueError("Unsupported product QA policy")
    cleaned = ds.copy(deep=False)
    cleaned[name] = data.where(mask)
    cleaned[name].attrs = dict(data.attrs)
    cleaned["qa_accepted"] = mask.astype("int8")
    cleaned["qa_accepted"].attrs = {"long_name": "analysis value passes selected product QA", "units": "1"}
    cleaned.attrs = {**ds.attrs, "qa_policy_revision": policy["policy_revision"],
                     "qa_policy_hash": policy_hash(policy), "qa_mode": policy["qa"]["modis_mode"],
                     "qa_status": "explicit preparation QA applied; inference not computed"}
    before, after = int(np.isfinite(data).sum()), int(mask.sum())
    return cleaned, {
        "source_finite_values": before, "accepted_values": after,
        "excluded_finite_values": before - after, "total_values": data.size,
        "accepted_fraction_all_values": after / data.size,
        "modis_mode": policy["qa"]["modis_mode"] if product == "MOD13C2" else None,
        "ancillary_threshold_applied": False if product == "GPM_3IMERGM" else None,
    }


def select_period(data: xr.Dataset | xr.DataArray, start: str, end: str) -> xr.Dataset | xr.DataArray:
    wanted = calendar_months(start, end)
    actual = validate_month_axis(data if isinstance(data, xr.DataArray) else data[next(iter(data.data_vars))])
    if wanted[0] < actual[0] or wanted[-1] > actual[-1]:
        raise ValueError("Requested period is outside available coverage")
    labels = np.array(actual)
    return data.isel(time=np.flatnonzero((labels >= start) & (labels <= end)))


def monthly_analysis_values(data: xr.DataArray, variable_id: str) -> xr.DataArray:
    if variable_id == "precipitation":
        return monthly_precipitation_amount(data)
    return data.copy(deep=False)


def annual_summary(monthly: xr.DataArray, variable_id: str) -> xr.DataArray:
    """Require twelve valid calendar months per location; never fill or scale up."""
    validate_month_axis(monthly)
    if bool(np.isinf(monthly).any()):
        raise ValueError("Infinite monthly values cannot be aggregated")
    count = monthly.notnull().groupby("time.year").sum("time")
    if variable_id == "precipitation":
        if monthly.attrs.get("units") != "mm":
            raise ValueError("Annual precipitation requires monthly amounts in mm")
        result = monthly.groupby("time.year").sum("time", skipna=True, min_count=1)
        aggregation = "sum of twelve monthly precipitation amounts"
    else:
        if variable_id not in ("air_temperature", "soil_moisture", "vegetation_greenness"):
            raise ValueError("Unknown annual aggregation variable")
        expected_units = {"air_temperature": "K", "soil_moisture": "kg m-2", "vegetation_greenness": "1"}
        if monthly.attrs.get("units") != expected_units[variable_id]:
            raise ValueError("Annual variable and units do not match")
        days = monthly.time.dt.days_in_month.astype("float64")
        numerator = (monthly * days).groupby("time.year").sum("time", skipna=True, min_count=1)
        denominator = days.where(monthly.notnull()).groupby("time.year").sum("time", skipna=True)
        result = numerator / denominator.where(denominator > 0)
        aggregation = "calendar-day-weighted mean of twelve monthly values"
    result = result.where(count == 12)
    result.attrs = {**monthly.attrs, "annual_aggregation": aggregation,
                    "required_valid_months": 12, "time_basis": "actual calendar year coordinate"}
    result.attrs["long_name"] = ("annual accumulated precipitation" if variable_id == "precipitation"
                                 else f"calendar-day-weighted annual mean {variable_id.replace('_', ' ')}")
    result.name = "annual"
    return result


def calendar_anomalies(monthly: xr.DataArray, reference: xr.DataArray) -> xr.DataArray:
    """Subtract the fixed-reference mean for the matching calendar month."""
    validate_month_axis(monthly)
    validate_month_axis(reference)
    if monthly.attrs.get("units") != reference.attrs.get("units"):
        raise ValueError("Anomaly input and reference units differ")
    if bool(np.isinf(monthly).any()) or bool(np.isinf(reference).any()):
        raise ValueError("Infinite values cannot be used for climatology")
    for axis in reference.dims:
        if axis != "time" and (axis not in monthly.coords or not np.array_equal(reference[axis], monthly[axis])):
            raise ValueError("Anomaly input and reference grids differ")
    count = reference.notnull().groupby("time.month").sum("time")
    total = reference.astype("float64").groupby("time.month").sum("time", skipna=True, min_count=1)
    climatology = (total / count.where(count > 0)).reindex(month=np.arange(1, 13))
    selected = climatology.sel(month=monthly.time.dt.month)
    result = (monthly - selected).drop_vars("month")
    labels = validate_month_axis(reference)
    result.attrs = {**monthly.attrs, "anomaly_baseline_start": labels[0],
                    "anomaly_baseline_end": labels[-1],
                    "anomaly_method": "fixed-reference calendar-month arithmetic mean"}
    result.attrs["long_name"] = "departure from the fixed-reference mean for the matching calendar month"
    result.name = "monthly_anomaly"
    return result
