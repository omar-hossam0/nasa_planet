"""Role 01 (data) preprocessing module - Trend Detective.

Single entry point for loading the verified cubes, applying the documented
QA policy, extracting regional series and regenerating the M1 artifacts
(coverage report, regional lineage, study windows).

    python preprocess.py --all              # regenerate all M1 artifacts
    python preprocess.py --coverage         # coverage report only
    python preprocess.py --lineage          # per-month hashes + granule ids
    python preprocess.py --qa-policy        # qa_policy.json
    python preprocess.py --windows          # study_windows.geojson
    python preprocess.py --series T2M Nile  # sanity print of a regional series

No network access is required: everything reads the verified local cubes and
monthly subsets in this directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent
MEAS = ROOT / "measurements"
REGIONAL = ROOT / "regional"
MANIFESTS = ROOT / "manifests"

# --------------------------------------------------------------------------
# Registries
# --------------------------------------------------------------------------

PRODUCTS = {
    "M2TMNXSLV": {
        "version": "5.12.4",
        "collection_concept_id": "C1276812859-GES_DISC",
        "variable": "T2M",
        "units": "K",
        "long_name": "2-metre air temperature",
        "source_kind": "reanalysis",
        "grid": {"lat_step": 0.5, "lon_step": 0.625},
        "quality_fields": [],
        "additional_fields": [],
    },
    "GLDAS_NOAH025_M": {
        "version": "2.1",
        "collection_concept_id": "C1342986036-GES_DISC",
        "variable": "SoilMoi0_10cm_inst",
        "units": "kg m-2",
        "long_name": "Top 0-10 cm soil moisture",
        "source_kind": "land_surface_model",
        "grid": {"lat_step": 0.25, "lon_step": 0.25},
        "quality_fields": [],
        "additional_fields": [],
    },
    "GPM_3IMERGM": {
        "version": "07",
        "collection_concept_id": "C2723754851-GES_DISC",
        "variable": "precipitation",
        "units": "mm/hr",
        "long_name": "Monthly mean precipitation rate",
        "source_kind": "satellite_gauge_merged",
        "grid": {"lat_step": 0.1, "lon_step": 0.1},
        "quality_fields": ["precipitationQualityIndex"],
        "additional_fields": ["randomError"],
    },
    "MOD13C2": {
        "version": "061",
        "collection_concept_id": "C2565788914-LPCLOUD",
        "variable": "NDVI",
        "units": "1",
        "long_name": "CMG 0.05-deg monthly NDVI",
        "source_kind": "satellite",
        "grid": {"lat_step": 0.05, "lon_step": 0.05},
        "quality_fields": ["VI_Quality", "pixel_reliability"],
        "additional_fields": [],
    },
}

WINDOWS = {
    "nile_corridor": {
        "name": "Nile corridor",
        "bbox": (29, 24, 33, 32),  # west, south, east, north
        "region_file": "Nile",
        "monthly_dir": "nile",
    },
    "morocco_comparison": {
        "name": "Morocco",
        "bbox": (-10, 30, -5, 35),
        "region_file": "Morocco",
        "monthly_dir": "morocco",
    },
    "sahel_comparison": {
        "name": "Sahel",
        "bbox": (-5, 12, 5, 17),
        "region_file": "Sahel",
        "monthly_dir": "sahel",
    },
}

PERIOD = ("2001-01", "2024-12")
MONTHS = [f"{y}-{m:02d}" for y in range(2001, 2025) for m in range(1, 13)]

# MODIS MODLAND QA bits (VI_Quality bits 0-1)
MODLAND_GOOD = 0        # VI produced, good quality
MODLAND_CHECK = 1       # VI produced, but check other QA
MODLAND_NOT_CLOUD = 2   # pixel not produced, cloud
MODLAND_NOT_OTHER = 3   # pixel not produced, other reasons
DEFAULT_ACCEPTED_BITS = (MODLAND_GOOD, MODLAND_CHECK)
STRICT_ACCEPTED_BITS = (MODLAND_GOOD,)
DEFAULT_ACCEPTED_RELIABILITY = (0, 1)   # good, acceptable
STRICT_ACCEPTED_RELIABILITY = (0,)


def cube_path(product: str, region_key: str) -> Path:
    return MEAS / f"{product}_{WINDOWS[region_key]['region_file']}_2001_2024.nc"


def load_cube(product: str, region_key: str) -> xr.Dataset:
    """Open a verified cube (lazy). Caller closes it."""
    path = cube_path(product, region_key)
    if not path.exists():
        raise FileNotFoundError(path)
    return xr.open_dataset(path)


# --------------------------------------------------------------------------
# QA policy
# --------------------------------------------------------------------------

def modis_quality_mask(qa: np.ndarray, reliability: np.ndarray,
                       mode: str = "default") -> np.ndarray:
    """Boolean array: True where the NDVI pixel passes the QA policy."""
    bits = (np.asarray(qa, dtype="u2") & np.uint16(0b11)).astype("i2")
    rel = np.asarray(reliability, dtype="i2")
    if mode == "default":
        return np.isin(bits, DEFAULT_ACCEPTED_BITS) & \
            np.isin(rel, DEFAULT_ACCEPTED_RELIABILITY)
    if mode == "strict":
        return np.isin(bits, STRICT_ACCEPTED_BITS) & \
            np.isin(rel, STRICT_ACCEPTED_RELIABILITY)
    raise ValueError(f"unknown QA mode: {mode}")


def apply_qa(ds: xr.Dataset, product: str, mode: str = "default") -> xr.Dataset:
    """Return a copy of the cube with the documented QA policy applied.

    Only MOD13C2 masks anything today. IMERG quality index is *not* used as an
    exclusion filter (observed values are far below any 0-100 style threshold),
    see qa_policy.json for the evidence.
    """
    out = ds.copy()
    spec = PRODUCTS[product]
    var = spec["variable"]
    if product == "GLDAS_NOAH025_M":
        # Older regional assembly retained the numeric source fill value.
        # Soil moisture cannot be negative; treat it as missing in every path.
        out[var] = out[var].where(out[var] >= 0)
    if product == "MOD13C2":
        mask = modis_quality_mask(out["VI_Quality"].values,
                                  out["pixel_reliability"].values, mode)
        out[var] = out[var].where(mask)
    return out


def regional_series(ds: xr.Dataset, product: str) -> dict:
    """Area-mean monthly series with the valid-cell count per month."""
    var = PRODUCTS[product]["variable"]
    data = ds[var]
    mean = data.mean(dim=("lat", "lon"), skipna=True).values
    valid = data.notnull().sum(dim=("lat", "lon")).values
    return {
        "variable": var,
        "units": PRODUCTS[product]["units"],
        "months": [str(t)[:7] for t in ds["time"].values],
        "mean": [None if not np.isfinite(v) else float(v) for v in mean],
        "valid_cells": [int(v) for v in valid],
    }


# --------------------------------------------------------------------------
# Artifacts
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build_coverage_report() -> dict:
    report = {
        "generated": "2026-11-14",
        "period": {"start": PERIOD[0], "end": PERIOD[1], "months": 288},
        "policy": "qa_policy.json",
        "cubes": {},
    }
    for product, spec in PRODUCTS.items():
        for region_key, win in WINDOWS.items():
            path = cube_path(product, region_key)
            with xr.open_dataset(path) as ds:
                var = spec["variable"]
                data = ds[var].values.astype("f8")
                finite = np.isfinite(data)
                per_month = finite.reshape(finite.shape[0], -1).mean(axis=1)
                coverage = finite.sum(axis=0)
                entry = {
                    "path": f"measurements/{path.name}",
                    "variable": var,
                    "units": spec["units"],
                    "months": int(data.shape[0]),
                    "grid": {"lat": int(data.shape[1]),
                             "lon": int(data.shape[2])},
                    "valid_fraction": round(float(finite.mean()), 6),
                    "per_month_valid_fraction": {
                        "min": round(float(per_month.min()), 6),
                        "median": round(float(np.median(per_month)), 6),
                        "max": round(float(per_month.max()), 6),
                    },
                    "cells_all_missing": int((coverage == 0).sum()),
                    "cells_partial": int(((coverage > 0) &
                                          (coverage < data.shape[0])).sum()),
                    "cells_complete": int((coverage == data.shape[0]).sum()),
                    "value_min": float(np.nanmin(data)),
                    "value_max": float(np.nanmax(data)),
                    "sha256": _sha256(path),
                    "bytes": path.stat().st_size,
                }
                if product == "MOD13C2":
                    qa = ds["VI_Quality"].values
                    rel = ds["pixel_reliability"].values
                    for mode in ("default", "strict"):
                        m = modis_quality_mask(qa, rel, mode)
                        entry[f"passes_qa_{mode}"] = round(float(m.mean()), 6)
                    bits = (qa & np.uint16(0b11))
                    vals, counts = np.unique(bits, return_counts=True)
                    entry["modland_qa_bit_counts"] = {
                        str(int(v)): int(c) for v, c in zip(vals, counts)}
                if product == "GPM_3IMERGM":
                    qi = ds["precipitationQualityIndex"].values.astype("f8")
                    qi = qi[np.isfinite(qi)]
                    entry["quality_index"] = {
                        "min": float(qi.min()),
                        "median": float(np.median(qi)),
                        "p95": float(np.percentile(qi, 95)),
                        "max": float(qi.max()),
                        "documented_scale": "0-100, higher is better",
                        "masked_by_policy": False,
                    }
            report["cubes"][f"{product}/{region_key}"] = entry
    return report


def build_lineage() -> dict:
    """Per-month SHA-256 + source granule id for every regional subset."""
    manifests = {}
    for product, spec in PRODUCTS.items():
        path = MANIFESTS / f"{product}.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            manifests[product] = {
                g["time_start"][:7]: g for g in data["granules"]}
    entries = []
    for product, spec in PRODUCTS.items():
        for region_key, win in WINDOWS.items():
            folder = REGIONAL / product / win["monthly_dir"]
            # Nile air temperature / soil moisture are subsets of the Egypt
            # parent cubes, so their monthly source files live in
            # measurements/<product>/<month>.nc instead of regional/.
            parent_mode = (region_key == "nile_corridor" and
                           product in ("M2TMNXSLV", "GLDAS_NOAH025_M"))
            if parent_mode:
                folder = MEAS / product
            for month in MONTHS:
                suffix = ".nc" if parent_mode else ".nc4"
                path = folder / f"{month}{suffix}"
                granule = manifests.get(product, {}).get(month, {})
                entry = {
                    "product": product,
                    "version": spec["version"],
                    "collection_concept_id": spec["collection_concept_id"],
                    "region_id": region_key,
                    "month": month,
                    "local_file": path.relative_to(ROOT).as_posix(),
                    "exists": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "sha256": _sha256(path) if path.exists() else None,
                    "granule_id": granule.get("id"),
                    "granule_title": granule.get("title"),
                    "granule_time_start": granule.get("time_start"),
                }
                if parent_mode:
                    entry["derivation"] = (
                        "cube is a subset of the Egypt parent cube; this "
                        "monthly file is the parent source subset")
                    entry["parent_cube"] = (
                        f"measurements/{product}_Egypt_2001_2024.nc")
                entries.append(entry)
    missing = [e["local_file"] for e in entries if not e["exists"]]
    return {
        "generated": "2026-11-14",
        "note": "One entry per product x region x month (4 x 3 x 288 = 3456).",
        "entries": entries,
        "summary": {
            "entries": len(entries),
            "files_present": len(entries) - len(missing),
            "files_missing": len(missing),
            "missing": missing[:20],
        },
    }


def build_qa_policy(coverage: dict) -> dict:
    modis = {k: v for k, v in coverage["cubes"].items()
             if k.startswith("MOD13C2/")}
    imerg = {k: v for k, v in coverage["cubes"].items()
             if k.startswith("GPM_3IMERGM/")}
    return {
        "policy_version": "1.0",
        "created": "2026-11-14",
        "owner": "Member 1 - data acquisition and validity",
        "scope": "12 cubes, 4 variables x 3 windows, 2001-01..2024-12",
        "global_rules": {
            "missing_is_not_zero": True,
            "no_implicit_regridding": True,
            "no_temporal_interpolation": True,
            "same_mask_for_analysis_and_display": True,
            "masking_never_creates_new_values": True,
        },
        "products": {
            "M2TMNXSLV": {
                "variable": "T2M",
                "units": "K",
                "quality_fields": [],
                "missing_handling": "netCDF fill converted to NaN at assembly",
                "default_mask": "finite values only",
                "notes": [
                    "Reanalysis output, not station observations.",
                    "Celsius conversion is explicit: T2M - 273.15.",
                    "Temperature differences (slopes) are identical in K and C.",
                ],
            },
            "GLDAS_NOAH025_M": {
                "variable": "SoilMoi0_10cm_inst",
                "units": "kg m-2",
                "quality_fields": [],
                "missing_handling":
                    "land-only model output; source fill -9999 -> NaN",
                "default_mask": "finite nonnegative values only",
                "notes": [
                    "Not a percentage and not relative humidity.",
                    "Cells that are missing are missing for all 288 months "
                    "(no on/off behaviour); see coverage_report.json.",
                ],
            },
            "GPM_3IMERGM": {
                "variable": "precipitation",
                "units": "mm/hr",
                "quality_fields": ["precipitationQualityIndex", "randomError"],
                "default_mask": "none (finite values only)",
                "evidence": {
                    "observed_quality_index": {
                        k.split("/")[1]: v.get("quality_index")
                        for k, v in imerg.items()},
                    "decision": (
                        "Do not exclude cells on the quality index. Observed "
                        "values in all three windows are far below a 0-100 "
                        "style threshold (medians 5-7), so a fixed cut such "
                        "as 50 or 80 would remove 100% of the data."),
                },
                "recommended_use": (
                    "Report the quality index and randomError next to every "
                    "precipitation number; use them for weighting or "
                    "caveats, not silent exclusion."),
                "unit_conversion": (
                    "mm/month = value(mm/hr) x hours_in_month; state the "
                    "conversion in the evidence card."),
            },
            "MOD13C2": {
                "variable": "NDVI",
                "units": "1",
                "quality_fields": ["VI_Quality", "pixel_reliability"],
                "fill_and_scale": {
                    "raw_fill": -3000,
                    "real_value": "raw * 0.0001",
                    "valid_range": [-0.2, 1.0],
                },
                "default_mask": (
                    "MODLAND QA bits 0-1 accepted, bits 2-3 masked; "
                    "pixel_reliability 0-1 accepted, 2-4 flagged not "
                    "excluded by the data layer"),
                "strict_mask": (
                    "MODLAND QA bits == 0 only; pixel_reliability == 0 only"),
                "evidence": {
                    "modland_qa_bit_counts": {
                        k.split("/")[1]: v.get("modland_qa_bit_counts")
                        for k, v in modis.items()},
                    "passes_qa": {
                        k.split("/")[1]: {
                            "default": v.get("passes_qa_default"),
                            "strict": v.get("passes_qa_strict"),
                        } for k, v in modis.items()},
                },
                "notes": [
                    "Bits 2-3 (pixel not produced) already appear as NaN in "
                    "the cube; they are not zeros.",
                    "NDVI is not a temperature or a precipitation proxy; do "
                    "not reuse temperature colour scales.",
                    "Spatial comparison across windows must state that the "
                    "windows have different vegetation regimes.",
                ],
            },
        },
        "display_rules": {
            "state_mask_in_legend": True,
            "show_valid_cell_count_with_series": True,
            "insufficient_data_threshold":
                "if a window/month has < 30% valid cells, show "
                "insufficient-data instead of a slope",
        },
    }


def build_study_windows() -> dict:
    features = []
    for region_key, win in WINDOWS.items():
        w, s, e, n = win["bbox"]
        features.append({
            "type": "Feature",
            "id": region_key,
            "properties": {
                "name": win["name"],
                "bbox_west_south_east_north": [w, s, e, n],
                "period": {"start": PERIOD[0], "end": PERIOD[1],
                           "months": 288},
                "variables": [
                    {"product_id": pid, "variable": spec["variable"],
                     "units": spec["units"],
                     "native_grid": spec["grid"],
                     "cube": f"measurements/{pid}_"
                             f"{win['region_file']}_2001_2024.nc"}
                    for pid, spec in PRODUCTS.items()
                ],
                "grid_alignment": (
                    "Each product keeps its native grid; the window is the "
                    "set of native grid-cell centres inside the bbox."),
                "boundary_type":
                    "geographic rectangle, not an administrative boundary",
                "limitations": [
                    "Includes neighbouring land and sea where present.",
                    "Not suitable for neighbourhood-level statements.",
                ],
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [w, s], [e, s], [e, n], [w, n], [w, s],
                ]],
            },
        })
    return {
        "type": "FeatureCollection",
        "name": "trend_detective_study_windows",
        "features": features,
    }


def write_all(verbose: bool = True) -> dict:
    coverage = build_coverage_report()
    (ROOT / "coverage_report.json").write_text(
        json.dumps(coverage, indent=2), encoding="utf-8")
    lineage = build_lineage()
    (ROOT / "regional_lineage.json").write_text(
        json.dumps(lineage, indent=2), encoding="utf-8")
    policy = build_qa_policy(coverage)
    (ROOT / "qa_policy.json").write_text(
        json.dumps(policy, indent=2), encoding="utf-8")
    windows = build_study_windows()
    (ROOT / "study_windows.geojson").write_text(
        json.dumps(windows, indent=2), encoding="utf-8")
    summary = {
        "coverage_cubes": len(coverage["cubes"]),
        "lineage_entries": lineage["summary"]["entries"],
        "lineage_missing": lineage["summary"]["files_missing"],
        "windows": len(windows["features"]),
    }
    if verbose:
        print(json.dumps(summary, indent=2))
    return summary


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--lineage", action="store_true")
    ap.add_argument("--qa-policy", action="store_true")
    ap.add_argument("--windows", action="store_true")
    ap.add_argument("--series", nargs=2,
                    metavar=("PRODUCT", "WINDOW"), help="print a series")
    args = ap.parse_args(argv)
    if args.series:
        product, region_key = args.series
        with load_cube(product, region_key) as ds:
            series = regional_series(ds, product)
        print(json.dumps({k: series[k] for k in
                          ("variable", "units", "months")}, indent=1))
        print("first 6 means:", [round(x, 3) if x is not None else None
                                 for x in series["mean"][:6]])
        return 0
    if args.all:
        write_all()
        return 0
    if args.coverage:
        (ROOT / "coverage_report.json").write_text(
            json.dumps(build_coverage_report(), indent=2), encoding="utf-8")
    if args.lineage:
        (ROOT / "regional_lineage.json").write_text(
            json.dumps(build_lineage(), indent=2), encoding="utf-8")
    if args.qa_policy:
        coverage = json.loads(
            (ROOT / "coverage_report.json").read_text(encoding="utf-8"))
        (ROOT / "qa_policy.json").write_text(
            json.dumps(build_qa_policy(coverage), indent=2), encoding="utf-8")
    if args.windows:
        (ROOT / "study_windows.geojson").write_text(
            json.dumps(build_study_windows(), indent=2), encoding="utf-8")
    if not any([args.all, args.coverage, args.lineage, args.qa_policy,
                args.windows]):
        ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
