"""Phase 3 descriptive slopes only; Stage 2 files are immutable inputs."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from scipy.stats.mstats import sen_seasonal_slopes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.preprocessing import policy_hash
from src.qa_policy_review import distribution
from src.trend_estimation import annual_elapsed_years, cell_trends, monthly_elapsed_years, trend_series
from review_sahel_ndvi import preservation_snapshot, sha, write_json

REPORTS = ROOT / "packages/science/phase_reports"
OUT = ROOT / "data/derived/science/phase_3"
MIN_POINTS = 3
REF_TOLERANCE = 1e-10
FORBIDDEN = {"p_value", "p_values", "ci_low", "ci_high", "confidence_interval", "significant", "significant_fdr", "classification"}


def stage2_snapshot():
    result = preservation_snapshot()
    # All existing preparation supplements, experimental arrays and reports too.
    for folder in (ROOT / "data/derived/science").iterdir():
        if folder.is_dir() and folder.name != "phase_3":
            result.update({p.relative_to(ROOT).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()})
    for p in [*REPORTS.glob("SAHEL_NDVI*"), REPORTS / "PHASE_2_APPROVAL.md"]:
        result[p.relative_to(ROOT).as_posix()] = sha(p)
    return result


def reference_slope(values, frequency):
    # One column computes ordinary Sen slope at regular row positions. Preserve
    # NaN rows as masks, then convert monthly row units to years. This function
    # returns slopes only, and never computes intervals or a hypothesis test.
    reference = sen_seasonal_slopes(np.ma.masked_invalid(np.asarray(values, dtype="float64")[:, None]))
    return float(reference.intra_slope[0]) * (12 if frequency == "monthly" else 1)


def assert_no_inference(value):
    if isinstance(value, dict):
        assert not FORBIDDEN.intersection(value), FORBIDDEN.intersection(value)
        for v in value.values():
            assert_no_inference(v)
    elif isinstance(value, list):
        for v in value:
            assert_no_inference(v)


def load_cases():
    prepared = json.loads((REPORTS / "PHASE_2_COVERAGE.json").read_text())
    standard = json.loads((REPORTS / "PHASE_2_QA_SENSITIVITY.json").read_text())
    review = json.loads((REPORTS / "SAHEL_NDVI_POLICY_METRICS.json").read_text())
    annual = json.loads((REPORTS / "SAHEL_NDVI_STANDARD95_REVIEW.json").read_text())
    cases = [{"key": f"{e['variable_id']}__{e['region_id']}__strict_100", "policy": "strict_100",
              "record": e, "variable_id": e["variable_id"], "region_id": e["region_id"], "experimental": False}
             for e in prepared["entries"]]
    e = next(e for e in standard["entries"] if e["region_id"] == "sahel_comparison")
    cases.append({"key": "vegetation_greenness__sahel_comparison__standard_100", "policy": "standard_100",
                  "record": e, "variable_id": e["variable_id"], "region_id": e["region_id"], "experimental": False})
    cases.append({"key": "vegetation_greenness__sahel_comparison__standard_95", "policy": "standard_95",
                  "record": review["cases"]["standard_95"], "variable_id": "vegetation_greenness",
                  "region_id": "sahel_comparison", "experimental": True,
                  "annual_record": annual["policies"]["standard_95"]})
    return cases


def load_prepared(case):
    record = case["record"]
    assert sha(ROOT / record["artifact"]) == record["artifact_sha256"]
    with xr.open_dataset(ROOT / record["artifact"]) as opened:
        fields = ["cell_monthly", "regional_monthly", "native_cell_solid_angle"]
        if case["experimental"]:
            fields += ["eligible_support", "observed_area_fraction_selected"]
        else:
            fields += ["fixed_support", "cell_annual", "regional_annual", "regional_monthly_anomaly"]
        ds = opened[fields].load()
    support = "eligible_support" if case["experimental"] else "fixed_support"
    ds = ds.rename({support: "eligible_support"})
    if case["experimental"]:
        annual_record = case["annual_record"]
        assert sha(ROOT / annual_record["annual_review_artifact"]) == annual_record["annual_review_sha256"]
        with xr.open_dataset(ROOT / annual_record["annual_review_artifact"]) as annual:
            for field in ("cell_annual", "valid_month_count_by_cell_year", "regional_annual_complete_cell_years"):
                ds[field] = annual[field].load()
            ds["regional_annual"] = annual.regional_annual_from_monthly.load()
        # Enforce the full original-month completeness rule before estimating
        # annual cell slopes. Incomplete cell-years are not compressed or filled.
        incomplete = ds.valid_month_count_by_cell_year < 12
        assert bool(ds.cell_annual.where(incomplete).isnull().all())
        assert int((ds.eligible_support.astype(bool) & incomplete).sum()) == annual_record["incomplete_eligible_cell_years"]
    return ds


def summarize_grid(grid, support):
    eligible = support.values.astype(bool)
    computed = grid.computable.values.astype(bool)
    return {"eligible_preparation_cells": int(eligible.sum()), "selected_cells": eligible.size,
            "computable_cell_slopes": int((computed & eligible).sum()),
            "insufficient_eligible_cells": int((eligible & ~computed).sum()),
            "excluded_preparation_cells": int((~eligible).sum()),
            "eligible_valid_observation_count": distribution(grid.n_valid.values[eligible]),
            "eligible_valid_span_years": distribution(grid.valid_span_years.values[eligible]),
            "cell_slope_distribution": distribution(grid.slope.values[computed & eligible])}


def regional_result(values, frequency, units):
    t = monthly_elapsed_years(values.time) if frequency == "monthly" else annual_elapsed_years(values.year)
    result = trend_series(values.values, t, min_points=MIN_POINTS)
    result["slope_units"] = f"{units} per year"
    result["time_convention"] = ("elapsed calendar-month ordinals / 12" if frequency == "monthly" else "actual calendar-year label differences")
    return result


def validate_reference(case, ds, grids, region, rows):
    for frequency, field in (("monthly", "cell_monthly"), ("annual", "cell_annual")):
        values = ds["regional_monthly" if frequency == "monthly" else "regional_annual"].values
        expected = reference_slope(values, frequency)
        actual = region[frequency]["slope_per_year"]
        np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=REF_TOLERANCE)
        rows.append({"case": case["key"], "scope": "regional", "frequency": frequency,
                     "actual": actual, "reference": expected, "absolute_difference": abs(actual - expected)})
        indices = np.flatnonzero(grids[frequency].computable.values)
        sample = np.unique(indices[np.linspace(0, len(indices) - 1, min(6, len(indices)), dtype=int)]) if len(indices) else []
        for index in sample:
            i, j = np.unravel_index(index, grids[frequency].slope.shape)
            values = ds[field].values[:, i, j]
            expected = reference_slope(values, frequency)
            actual = float(grids[frequency].slope.values[i, j])
            t = monthly_elapsed_years(ds.time) if frequency == "monthly" else annual_elapsed_years(ds.year)
            scalar = trend_series(values, t, min_points=MIN_POINTS)
            assert scalar["n_valid"] == int(grids[frequency].n_valid.values[i, j])
            assert scalar["slope_per_year"] == actual
            np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=REF_TOLERANCE)
            rows.append({"case": case["key"], "scope": "deterministic_spread_cell", "frequency": frequency,
                         "latitude": float(ds.lat.values[i]), "longitude": float(ds.lon.values[j]),
                         "n_valid": scalar["n_valid"], "actual": actual, "reference": expected,
                         "absolute_difference": abs(actual - expected)})
    sensitivities = (("monthly_calendar_anomaly", "regional_monthly_anomaly", "monthly"),
                     ("annual_complete_cell_year_diagnostic", "regional_annual_complete_cell_years", "annual"))
    for name, field, frequency in sensitivities:
        if name in region:
            actual = region[name]["slope_per_year"]
            expected = reference_slope(ds[field].values, frequency)
            np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=REF_TOLERANCE)
            rows.append({"case": case["key"], "scope": name, "frequency": frequency,
                         "actual": actual, "reference": expected, "absolute_difference": abs(actual - expected)})


def policy_sensitivity(results):
    cases = [r for r in results if r["variable_id"] == "vegetation_greenness" and r["region_id"] == "sahel_comparison"]
    by_policy = {r["policy"]: r for r in cases}
    comparison = {}
    for candidate, baseline in (("standard_100", "strict_100"), ("standard_95", "standard_100")):
        comparison[f"{candidate}_minus_{baseline}"] = {
            f"regional_{freq}_slope_difference_per_year": by_policy[candidate]["regional"][freq]["slope_per_year"] - by_policy[baseline]["regional"][freq]["slope_per_year"]
            for freq in ("monthly", "annual")}
    return comparison


def make_plots(results):
    rows = [r for r in results if r["variable_id"] == "vegetation_greenness" and r["region_id"] == "sahel_comparison"]
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    names = [r["policy"].replace("_", " ") for r in rows]
    for ax, freq in zip(axes, ("monthly", "annual")):
        values = [r["regional"][freq]["slope_per_year"] for r in rows]
        bars = ax.bar(names, values, color=["#2563eb", "#e8790c", "#15956f"])
        ax.bar_label(bars, fmt="%.6f", padding=3)
        label = "raw monthly" if freq == "monthly" else "prepared annual"
        ax.set(title=f"Sahel NDVI: {label} regional series", ylabel="Descriptive slope (NDVI per year)")
        ax.grid(axis="y", alpha=.2)
    fig.suptitle("Preparation sensitivity; Standard 95% experimental; no inference")
    fig.savefig(OUT / "sahel_policy_slopes.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    plots = []
    for r in rows[:2]:
        with xr.open_dataset(ROOT / r["grid_artifact"]) as grid:
            plots.extend([(r["policy"], f, grid[f"{f}_slope"].load()) for f in ("monthly", "annual")])
    vmax = max(float(abs(data).max()) for _, _, data in plots)
    for ax, (label, frequency, values) in zip(axes.flat, plots):
        im = ax.pcolormesh(values.lon, values.lat, values, shading="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set(title=f"{label}: {frequency}", xlabel="Longitude", ylabel="Latitude", facecolor="#dedede")
    fig.colorbar(im, ax=axes.ravel().tolist(), label="Descriptive NDVI slope per year; gray = excluded", shrink=.8)
    fig.suptitle("Strict and standard complete support: continuous slopes, no classifications")
    fig.savefig(OUT / "sahel_cell_slopes.png", dpi=150)
    plt.close(fig)


def main():
    start = time.perf_counter()
    OUT.mkdir(parents=True, exist_ok=True)
    before = stage2_snapshot()
    snapshot_path = OUT / "stage2_preserved.json"
    if snapshot_path.exists():
        assert json.loads(snapshot_path.read_text()) == before, "Stage 2 changed since first Phase 3 run"
    else:
        write_json(snapshot_path, before)
    policy_path = ROOT / "packages/science/config/trend_policy.json"
    policy = json.loads(policy_path.read_text())
    assert policy["minimum_valid_observations"] == MIN_POINTS
    rows, reference_rows = [], []
    for case in load_cases():
        started = time.perf_counter()
        print(f"Estimating {case['key']}", flush=True)
        ds = load_prepared(case)
        units = ds.cell_monthly.attrs["units"]
        grids = {frequency: cell_trends(ds[field], frequency=frequency, min_points=MIN_POINTS)
                 for frequency, field in (("monthly", "cell_monthly"), ("annual", "cell_annual"))}
        region = {frequency: regional_result(ds[field], frequency, units)
                  for frequency, field in (("monthly", "regional_monthly"), ("annual", "regional_annual"))}
        if not case["experimental"]:
            region["monthly_calendar_anomaly"] = regional_result(ds.regional_monthly_anomaly, "monthly", units)
        else:
            region["annual_complete_cell_year_diagnostic"] = regional_result(ds.regional_annual_complete_cell_years, "annual", units)
        validate_reference(case, ds, grids, region, reference_rows)
        grid = xr.merge([g.rename({name: f"{frequency}_{name}" for name in g.data_vars}) for frequency, g in grids.items()], combine_attrs="drop_conflicts")
        grid["eligible_support"] = ds.eligible_support
        grid.attrs.update({"case": case["key"], "policy": case["policy"], "experimental": int(case["experimental"]),
                           "source_prepared_artifact": case["record"]["artifact"],
                           "source_prepared_sha256": case["record"]["artifact_sha256"],
                           "trend_policy_sha256": policy_hash(policy), "inference_status": "not_computed"})
        assert not FORBIDDEN.intersection(grid.data_vars)
        target = OUT / f"{case['key']}.nc"
        grid.to_netcdf(target, encoding={key: {"zlib": True, "complevel": 4} for key in grid.data_vars})
        with xr.open_dataset(target) as reopened:
            xr.testing.assert_allclose(reopened, grid)
        stats = {"case": case["key"], "variable_id": case["variable_id"], "region_id": case["region_id"],
                 "policy": case["policy"], "experimental": case["experimental"],
                 "source_artifact": case["record"]["artifact"], "source_artifact_sha256": case["record"]["artifact_sha256"],
                 "regional": region, "grid": {frequency: summarize_grid(g, ds.eligible_support) for frequency, g in grids.items()},
                 "eligible_area_fraction_selected": float(ds.native_cell_solid_angle.where(ds.eligible_support.astype(bool), 0).sum() / ds.native_cell_solid_angle.sum()),
                 "grid_artifact": target.relative_to(ROOT).as_posix(), "grid_sha256": sha(target),
                 "cell_annual_missing_eligible_records": int((ds.cell_annual.isnull() & ds.eligible_support.astype(bool)).sum()),
                 "annual_interpretation": ("experimental annual mean of changing-support monthly regional means; incomplete cell-years excluded from cell slopes"
                                           if case["experimental"] else "fixed support; regional annual and cell annual summaries each require twelve original months"),
                 "elapsed_seconds": time.perf_counter() - started}
        rows.append(stats)
        print(f"  monthly={region['monthly']['slope_per_year']:.8g}; annual={region['annual']['slope_per_year']:.8g} {units}/year; "
              f"{stats['elapsed_seconds']:.1f}s", flush=True)
    make_plots(rows)
    assert stage2_snapshot() == before, "Stage 2 input bytes changed"
    result = {"method_revision": policy["revision"], "approval_record": "packages/science/phase_reports/PHASE_2_APPROVAL.md",
              "inference_status": "not_computed", "default_changed": False, "preparation_policy_changed": False,
              "software_versions": {name: importlib.metadata.version(name) for name in ("numpy", "xarray", "scipy", "netCDF4")},
              "code_sha256": {p: sha(ROOT / p) for p in ("packages/science/src/trend_estimation.py", "tools/run_science_trends.py", "packages/science/config/trend_policy.json")},
              "input_git_revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
              "policy": policy, "cases": rows, "sahel_policy_sensitivity": policy_sensitivity(rows),
              "elapsed_seconds": time.perf_counter() - start}
    assert_no_inference(result)
    write_json(REPORTS / "PHASE_3_RESULTS.json", result)
    validation = {"status": "passed", "reference": "SciPy mstats.sen_seasonal_slopes single-column intra_slope; slope only",
                  "reference_url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.mstats.sen_seasonal_slopes.html",
                  "reference_scipy_version": importlib.metadata.version("scipy"),
                  "single_column_interpretation": "ordinary pairwise Sen median, no seasonal adjustment; masked rows retain time positions",
                  "reference_absolute_tolerance": REF_TOLERANCE,
                  "reference_comparisons": len(reference_rows), "max_absolute_difference": max(r["absolute_difference"] for r in reference_rows),
                  "scalar_grid_sample_parity": True, "reference_records": reference_rows,
                  "stage2_preserved_file_count": len(before), "all_stage2_sha256_unchanged": True,
                  "stage2_sha256": before, "grid_netcdf_reopen_checks": True,
                  "inference_outputs_present": False, "incomplete_experimental_cell_years_stay_missing": True}
    write_json(REPORTS / "PHASE_3_VALIDATION.json", validation)
    write_json(OUT / "manifest.json", {"results": "packages/science/phase_reports/PHASE_3_RESULTS.json",
                                      "results_sha256": sha(REPORTS / "PHASE_3_RESULTS.json"),
                                      "validation_sha256": sha(REPORTS / "PHASE_3_VALIDATION.json")})
    print(f"PASS: {len(rows)} cases; {len(reference_rows)} reference checks; {len(before)} Stage 2 files unchanged.")


if __name__ == "__main__":
    main()
