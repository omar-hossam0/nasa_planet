"""Analysis adapter: runs the frozen statistics pipeline for one job.

Ingestion never happens here. The runner only reads verified cubes and the
frozen method config, so a user request can never trigger a download.
"""
from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime, timezone

import numpy as np

from . import canonical, config, receipts, registry

# make the data/analysis packages importable
sys.path.insert(0, str(config.DATA_DIR))
sys.path.insert(0, str(config.DATA_DIR / "analysis"))

import preprocess as pp  # noqa: E402
import trend as tr  # noqa: E402


class AnalysisError(Exception):
    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _granules_for(product: str, months: list[str]) -> list[dict]:
    path = config.DATA_DIR / "manifests" / f"{product}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    by_month = {g["time_start"][:7]: g for g in data["granules"]}
    out = []
    for m in months:
        g = by_month.get(m)
        if g:
            out.append({"month": m, "granule_id": g.get("id")})
    return out


def _region_series_masked(cube, mask2d):
    """cos-latitude weighted regional series restricted to a cell mask."""
    var = [v for v in cube.data_vars][0]
    lat = cube["lat"].values
    wlat = np.cos(np.deg2rad(lat))[:, None] * np.ones_like(mask2d)
    w = wlat * mask2d
    data = cube[var].values
    num = np.nansum(data * w[None, :, :], axis=(1, 2))
    den = np.nansum(np.isfinite(data) * w[None, :, :], axis=(1, 2))
    with np.errstate(invalid="ignore", divide="ignore"):
        series = num / den
    valid_cells = (np.isfinite(data) * mask2d[None, :, :]).sum(axis=(1, 2))
    return series, valid_cells, int(mask2d.sum())


def analyse_variable(entry: dict, request: dict, aoi_ring,
                     cfg: dict) -> dict:
    product = entry["product_id"]
    region = entry["region_id"]
    months = canonical.month_range(request["start_month"], request["end_month"])
    month_set = set(months)

    with pp.load_cube(product, region) as ds:
        clean = pp.apply_qa(ds, product, mode=cfg["qa"]["mode"])
        times = [str(t)[:7] for t in clean["time"].values]
        idx = [i for i, m in enumerate(times) if m in month_set]
        if not idx:
            raise AnalysisError("UNSUPPORTED_PERIOD",
                                "no months of this request exist in the cube")
        sub = clean.isel(time=idx)
        lat = sub["lat"].values
        lon = sub["lon"].values
        if aoi_ring is not None:
            inside = canonical.point_in_polygon(
                lon[None, :], lat[:, None], aoi_ring)
            mask2d = np.asarray(inside, dtype=bool)
            if not mask2d.any():
                raise AnalysisError(
                    "EMPTY_AOI",
                    "no grid-cell centre falls inside the requested polygon")
        else:
            mask2d = np.ones((len(lat), len(lon)), dtype=bool)

        series, valid_cells, n_cells = _region_series_masked(sub, mask2d)
        months_sub = [times[i] for i in idx]
        res = tr.trend_series(series, months_sub, cfg)
        sens = tr.period_sensitivity(series, months_sub, cfg)

        total = n_cells * len(months_sub)
        finite = float(np.isfinite(sub[[v for v in sub.data_vars][0]].values[
            :, mask2d]).sum()) / max(total, 1)

    state = res["state"]
    payload = {
        "variable_id": entry["variable_id"],
        "product_id": product,
        "version": entry.get("version"),
        "units": entry["units"],
        "label": entry.get("label"),
        "period": {"start": months_sub[0], "end": months_sub[-1],
                   "months": len(months_sub)},
        "aggregation_policy_id": cfg["aggregation"]["policy_id"],
        "qa_policy_mode": cfg["qa"]["mode"],
        "counts": {
            "months": len(months_sub),
            "cells": n_cells,
            "valid_fraction": round(finite, 6),
            "min_valid_cells_month": int(np.min(valid_cells)),
        },
        "state": state,
        "trend": {
            "slope_per_year": res.get("slope"),
            "slope_units": f"{entry['units']} per year",
            "p_value": res.get("p_value"),
            "p_value_uncorrected": res.get("p_value_uncorrected"),
            "ci_low": res.get("ci_low"),
            "ci_high": res.get("ci_high"),
            "ci_meta": res.get("ci_meta"),
            "test": res.get("test"),
            "dependence_correction": res.get("dependence_correction"),
            "significant_at": res.get("significant_at"),
        },
        "period_sensitivity": sens,
        "warnings": [],
        "artifact": {
            "cube": entry.get("cube_path"),
            "spatial_trend": entry.get("spatial_trend"),
        },
        "_granules": _granules_for(product, months_sub),
    }
    if state != "succeeded":
        payload["warnings"].append(
            "insufficient_data: the frozen coverage rule rejected this series; "
            "no slope is reported")
    return payload


def series_only(entry: dict, request: dict, cfg: dict,
                with_trend: bool = False, with_ci: bool = False) -> dict:
    """Monthly series (and optional trend) without any bootstrap unless asked.

    Used by the chart and the region comparison; the numbers come from the same
    aggregation and method as the evidence card, so the chart cannot disagree
    with the card.
    """
    product = entry["product_id"]
    region = entry["region_id"]
    months = canonical.month_range(request["start_month"],
                                   request["end_month"])
    month_set = set(months)
    with pp.load_cube(product, region) as ds:
        clean = pp.apply_qa(ds, product, mode=cfg["qa"]["mode"])
        times = [str(t)[:7] for t in clean["time"].values]
        idx = [i for i, m in enumerate(times) if m in month_set]
        if not idx:
            raise AnalysisError("UNSUPPORTED_PERIOD",
                                "no months of this request exist in the cube")
        sub = clean.isel(time=idx)
        lat = sub["lat"].values
        lon = sub["lon"].values
        aoi = request.get("aoi")
        if aoi:
            ring = aoi["coordinates"][0]
            mask2d = np.asarray(canonical.point_in_polygon(
                lon[None, :], lat[:, None], ring), dtype=bool)
            if not mask2d.any():
                raise AnalysisError("EMPTY_AOI", "no cell centre inside AOI")
        else:
            mask2d = np.ones((len(lat), len(lon)), dtype=bool)
        series, valid_cells, n_cells = _region_series_masked(sub, mask2d)
        months_sub = [times[i] for i in idx]
        var = [v for v in sub.data_vars][0]
        finite = float(np.isfinite(sub[var].values[:, mask2d]).sum()) / \
            max(n_cells * len(months_sub), 1)
        out = {
            "variable_id": entry["variable_id"],
            "product_id": product,
            "units": entry["units"],
            "months": months_sub,
            "values": [None if not np.isfinite(v) else round(float(v), 6)
                       for v in series],
            "valid_cells": [int(v) for v in valid_cells],
            "cells": n_cells,
            "valid_fraction": round(finite, 6),
        }
        if with_trend:
            res = tr.trend_series(series, months_sub, cfg, with_ci=with_ci)
            out["trend"] = {
                "slope_per_year": res.get("slope"),
                "p_value": res.get("p_value"),
                "ci_low": res.get("ci_low"),
                "ci_high": res.get("ci_high"),
                "state": res.get("state"),
            }
            slope = res.get("slope")
            if slope is not None:
                # linear trend line in the series' own units, computed here so
                # the browser never does statistics
                t = np.arange(len(months_sub)) / 12.0
                base = float(np.nanmean(series))
                line = base + slope * (t - t.mean())
                out["trend_line"] = [round(float(v), 6) for v in line]
    return out


def run(job: dict) -> tuple[dict, dict, str, str]:
    """Execute a job.

    Returns (result_payload, receipt_payload, result_id, receipt_id). Nothing
    is persisted here; the worker writes both rows in one transaction.
    """
    request = json.loads(job["canonical_request_json"])
    reg = registry.load_registry()
    cfg = reg.method
    if request["method_revision"] != reg.method_revision:
        raise AnalysisError(
            "METHOD_REVISION_MISMATCH",
            f"request asks for {request['method_revision']} but the server is "
            f"frozen at {reg.method_revision}")
    if request["data_revision"] != reg.revision:
        raise AnalysisError(
            "DATA_REVISION_MISMATCH",
            "request data_revision does not match the installed data")

    aoi_ring = None
    if request.get("aoi"):
        aoi_ring = request["aoi"]["coordinates"][0]

    per_variable = []
    for vid in request["variable_ids"]:
        entry = reg.servable(vid, request["region_id"])
        if not entry:
            raise AnalysisError(
                "UNAVAILABLE_SOURCE",
                f"{vid}/{request['region_id']} is not measurement+method ready")
        per_variable.append(analyse_variable(entry, request, aoi_ring, cfg))

    states = [v["state"] for v in per_variable]
    if all(s == "insufficient_data" for s in states):
        overall = "insufficient_data"
    else:
        overall = "succeeded"

    spatial_mask = {
        "aoi": request.get("aoi"),
        "cell_selection": "grid-cell centres inside the AOI polygon"
                          if aoi_ring is not None else "all cells in window",
        "cells_per_variable": {v["variable_id"]: v["counts"]["cells"]
                               for v in per_variable},
    }
    receipt_payload = receipts.build(job, request, per_variable, spatial_mask)

    result_id = "res_" + uuid.uuid4().hex[:16]
    receipt_id = "rcpt_" + uuid.uuid4().hex[:16]
    result_payload = {
        "result_id": result_id,
        "job_id": job["id"],
        "request_hash": job["request_hash"],
        "state": overall,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_revision": job["data_revision"],
        "method_revision": job["method_revision"],
        "software_revision": config.SOFTWARE_REVISION,
        "request": request,
        "variables": per_variable,
        "receipt_id": receipt_id,
        "warnings": [],
    }
    return result_payload, receipt_payload, result_id, receipt_id
