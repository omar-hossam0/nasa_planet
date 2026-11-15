"""Stage 2 orchestration: immutable sources -> explicit prepared series."""
from __future__ import annotations

import json

import numpy as np
import xarray as xr

from .data_loader import input_entry, load_cube, validate_cube
from .preprocessing import (annual_summary, apply_product_qa, calendar_anomalies,
                            load_policy, monthly_analysis_values, policy_hash, select_period,
                            validate_policy)
from .regional_series import BoundingBox, cell_solid_angles, fixed_support_mean, select_bbox


def prepare_series(ds: xr.Dataset, entry: dict, *, policy: dict | None = None,
                   bbox: BoundingBox | None = None, start_month: str | None = None,
                   end_month: str | None = None) -> tuple[xr.Dataset, dict]:
    """Prepare a request using QA/support fixed over the full registered cube."""
    policy = load_policy() if policy is None else policy
    validate_policy(policy)
    validate_cube(ds, entry)
    supported = BoundingBox(*entry["bbox"])
    bbox = supported if bbox is None else bbox
    spacing = tuple(policy["spatial"]["native_spacing_degrees"][entry["product_id"]])
    full_weights = cell_solid_angles(ds.lat, ds.lon, spacing)
    subset = select_bbox(ds, bbox, supported)
    weights = full_weights.sel(lat=subset.lat, lon=subset.lon)
    cleaned, qa_summary = apply_product_qa(subset, entry, policy)
    name, variable = entry["cube_variable"], entry["variable_id"]
    reference = monthly_analysis_values(cleaned[name], variable)
    support = fixed_support_mean(reference, weights)
    first, last = entry["period"]
    start = first if start_month is None else start_month
    end = last if end_month is None else end_month
    cells = select_period(support.cell_monthly, start, end)
    region = select_period(support.regional_monthly, start, end)
    output = xr.Dataset({
        "qa_monthly": select_period(reference, start, end),
        "cell_monthly": cells,
        "regional_monthly": region,
        "cell_monthly_anomaly": calendar_anomalies(cells, support.cell_monthly),
        "regional_monthly_anomaly": calendar_anomalies(region, support.regional_monthly),
        "cell_annual": annual_summary(cells, variable),
        "regional_annual": annual_summary(region, variable),
        "fixed_support": support.fixed_support,
        "normalized_support_weight": support.normalized_support_weight,
        "native_cell_solid_angle": support.native_cell_solid_angle,
        "qa_valid_fraction_by_cell": support.qa_valid_fraction_by_cell,
        "qa_valid_area_fraction_by_month": select_period(support.qa_valid_area_fraction_by_month, start, end),
        "qa_accepted": select_period(cleaned.qa_accepted, start, end),
    })
    for field in subset.data_vars:
        if field != name:
            output[field] = select_period(subset[field], start, end)
    if variable == "precipitation":
        output["source_monthly_rate_after_qa"] = select_period(cleaned[name], start, end)
    eligible = int(support.fixed_support.sum())
    selected = support.fixed_support.size
    fraction = float(weights.where(support.fixed_support.astype(bool), 0).sum() / weights.sum())
    state = "prepared" if eligible else "insufficient_data"
    output.attrs = {
        "output_metadata_revision": "1.1",
        "preparation_state": state, "variable_id": variable,
        "region_id": entry["region_id"], "product_id": entry["product_id"],
        "product_version": entry["version"], "source_variable": entry["source_variable"],
        "cube_variable": name, "source_units": entry["cube_units"],
        "policy_revision": policy["policy_revision"], "policy_sha256": policy_hash(policy),
        "policy_review_status": policy["status"], "modis_mode": policy["qa"]["modis_mode"],
        "support_reference_start": first, "support_reference_end": last,
        "requested_start": start, "requested_end": end,
        "requested_bbox": json.dumps(bbox.as_list()),
        "selection": policy["spatial"]["selection"],
        "weighting": policy["spatial"]["weighting"],
        "boundary_treatment": "full native cells; centre-based selection; no fractional bbox overlap",
        "coverage_interpretation": "series represents retained fixed QA-valid cells, not necessarily the entire rectangle",
        "inference_status": "not_computed",
    }
    metadata = {
        **output.attrs,
        "requested_bbox": bbox.as_list(),
        "selected_grid": {"lat_count": subset.sizes["lat"], "lon_count": subset.sizes["lon"],
                          "lat_centres": [float(subset.lat.min()), float(subset.lat.max())],
                          "lon_centres": [float(subset.lon.min()), float(subset.lon.max())]},
        "analysis_months": cells.sizes["time"], "annual_calendar_years": output.year.values.tolist(),
        "regional_valid_annual_count": int(output.regional_annual.notnull().sum()),
        "selected_cell_count": selected, "eligible_fixed_support_cells": eligible,
        "excluded_from_fixed_support_cells": selected - eligible,
        "fixed_support_cell_fraction": eligible / selected,
        "fixed_support_area_fraction_of_selected_native_cells": fraction,
        "qa_valid_area_fraction_reference_min": float(support.qa_valid_area_fraction_by_month.min()),
        "qa_valid_area_fraction_reference_max": float(support.qa_valid_area_fraction_by_month.max()),
        "monthly_units": reference.attrs["units"],
        "annual_units": output.cell_annual.attrs["units"],
        "annual_aggregation": output.cell_annual.attrs["annual_aggregation"],
        "qa": qa_summary,
        "warnings": [
            "Complete-case fixed support can be geographically unrepresentative; inspect retained area/cell fractions.",
            "Weights describe centre-selected full native cells, not exact polygon-intersection areas.",
            "Preparation eligibility is not trend or inference eligibility.",
            "Policy is implemented and tested but awaiting owner review; method/app readiness is unchanged.",
        ],
    }
    if not eligible:
        metadata["reason"] = "No cells pass QA in every registered reference month"
    return output, metadata


def prepare_registered(variable_id: str, region_id: str, **kwargs) -> tuple[xr.Dataset, dict]:
    return prepare_series(load_cube(variable_id, region_id), input_entry(variable_id, region_id), **kwargs)
