"""Reproduce the isolated Stage 2 Sahel NDVI QA/coverage checkpoint.

Never writes the canonical policy, strict/standard outputs or original reports.
Run from the repository root with .venv/Scripts/python.exe tools/review_sahel_ndvi.py.
"""
from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.data_loader import input_entry, load_cube
from src.preprocessing import apply_product_qa, load_policy, policy_hash
from src.qa_policy_review import (SEASONS, coverage_experiment, decode_cmg_quality,
                                  distribution, missingness_groups)
from src.regional_series import cell_solid_angles

OUT = ROOT / "data/derived/science/sahel_ndvi_policy_review"
REPORTS = ROOT / "packages/science/phase_reports"
VARIABLE, REGION = "vegetation_greenness", "sahel_comparison"
NAME = f"{VARIABLE}__{REGION}.nc"


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def preservation_snapshot():
    paths = [ROOT / "packages/science/config/preparation_policy.json",
             ROOT / "packages/science/notebooks/02_preprocessing.ipynb"]
    for folder in ("phase_2", "phase_2_standard"):
        paths.extend(p for p in (ROOT / "data/derived/science" / folder).rglob("*") if p.is_file())
    paths.extend(REPORTS.glob("PHASE_2*"))
    # Preserve every source cube too, including the other products/regions.
    paths.extend((ROOT / "data/nasa/measurements").glob("*.nc"))
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(set(paths))}


def quality_profile(mask, fields, ndvi, weights):
    """Shares use only observations in mask, never all source observations."""
    count = int(mask.sum())
    area_time = float((mask * weights).sum())
    result = {"cell_month_count": count, "ndvi_unweighted": distribution(ndvi[mask]), "fields": {}}
    for key, values in fields.items():
        histogram = {}
        for code in np.unique(values[mask]):
            selected = mask & (values == code)
            n = int(selected.sum())
            histogram[str(int(code))] = {
                "cell_month_count": n, "cell_month_fraction": n / count if count else None,
                "area_time_fraction": float((selected * weights).sum()) / area_time if area_time else None}
        result["fields"][key] = histogram
    return result


def quality_groups(strict, standard, fields, ndvi, weights, months):
    groups = {"all": np.ones(len(months), dtype=bool),
              **{f"month_{m:02}": months == m for m in range(1, 13)},
              **{s: np.isin(months, mm) for s, mm in SEASONS.items()}}
    result = {}
    for label, selected in groups.items():
        masks = {"strict_accepted": strict[selected], "standard_accepted": standard[selected],
                 "standard_only_marginal": (standard & ~strict)[selected]}
        total = int(selected.sum()) * weights.size
        result[label] = {"source_cell_month_count": total,
                         "strict_accepted_fraction": int(masks["strict_accepted"].sum()) / total,
                         "standard_accepted_fraction": int(masks["standard_accepted"].sum()) / total,
                         "profiles": {key: quality_profile(mask, {k: v[selected] for k, v in fields.items()},
                                                              ndvi[selected], weights)
                                      for key, mask in masks.items()}}
    return result


def difference(candidate, baseline):
    good = np.isfinite(candidate) & np.isfinite(baseline)
    delta = candidate[good] - baseline[good]
    return {"paired_months": int(good.sum()), "candidate_minus_baseline": distribution(delta),
            "mean_absolute_difference": float(np.abs(delta).mean()) if delta.size else None,
            "root_mean_square_difference": float(np.sqrt(np.mean(delta ** 2))) if delta.size else None,
            "max_absolute_difference": float(np.abs(delta).max()) if delta.size else None}


def case_metrics(out, weights, marginal, months, lat, lon):
    observed = out.observed_support.values.astype(bool)
    eligible = out.eligible_support.values.astype(bool)
    eligible_area = float(weights[eligible].sum())
    areas = (observed * weights).sum((1, 2))
    total_area = float(weights.sum())
    frac_selected = np.clip(areas / total_area, 0, 1)
    frac_eligible = np.clip(areas / eligible_area, 0, 1) if eligible_area else np.full(len(areas), np.nan)
    churn = ((observed[1:] ^ observed[:-1]) * weights).sum((1, 2)) / total_area
    marginal_area = ((observed & marginal) * weights).sum((1, 2))
    lat2d = np.broadcast_to(lat[:, None], weights.shape)
    lon2d = np.broadcast_to(lon[None, :], weights.shape)
    latitude = (observed * weights * lat2d).sum((1, 2)) / np.where(areas > 0, areas, np.nan)
    longitude = (observed * weights * lon2d).sum((1, 2)) / np.where(areas > 0, areas, np.nan)
    # Geographic bands are descriptive equal latitude/longitude halves, not land classes.
    bands = {"south_lat_lt_14.5": lat2d < 14.5, "north_lat_ge_14.5": lat2d >= 14.5,
             "west_lon_lt_0": lon2d < 0, "east_lon_ge_0": lon2d >= 0}
    result = {
        "required_valid_months": out.attrs["required_valid_reference_months"],
        "eligible_cell_count": int(eligible.sum()), "selected_cell_count": weights.size,
        "eligible_area_fraction_selected": eligible_area / total_area,
        "monthly_observed_area_fraction_selected": distribution(frac_selected),
        "monthly_observed_area_fraction_eligible": distribution(frac_eligible),
        "consecutive_month_changed_area_fraction_selected": distribution(churn),
        "monthly_observed_latitude_centroid": distribution(latitude),
        "monthly_observed_longitude_centroid": distribution(longitude),
        "regional_monthly_ndvi": distribution(out.regional_monthly.values),
        "marginal_fraction_of_observed_area_time": float(marginal_area.sum() / areas.sum()) if areas.sum() else None,
        "months_below_95pct_observed_eligible_area": int((frac_eligible < .95).sum()),
        "months_below_90pct_observed_eligible_area": int((frac_eligible < .90).sum()),
        "missingness": missingness_groups(observed, eligible, weights, months),
        "halves": {}, "geographic_band_retained_area_fraction": {},
    }
    for label, sl in (("2001_2012", slice(0, 144)), ("2013_2024", slice(144, 288))):
        result["halves"][label] = {"mean_observed_area_fraction_selected": float(frac_selected[sl].mean()),
                                  "mean_observed_area_fraction_eligible": float(frac_eligible[sl].mean())}
    for label, mask in bands.items():
        result["geographic_band_retained_area_fraction"][label] = float(weights[mask & eligible].sum() / weights[mask].sum())
    for s, mm in SEASONS.items():
        keep = np.isin(months, mm)
        result["missingness"]["season"][s]["regional_monthly_ndvi"] = distribution(out.regional_monthly.values[keep])
    result["monthly"] = [
        {"month": str(out.time.values[i])[:7], "regional_ndvi": float(out.regional_monthly.values[i]) if areas[i] else None,
         "observed_cells": int(observed[i].sum()), "observed_area_fraction_selected": float(frac_selected[i]),
         "observed_area_fraction_eligible": float(frac_eligible[i]) if eligible_area else None,
         "marginal_fraction_observed_area": float(marginal_area[i] / areas[i]) if areas[i] else None,
         "latitude_centroid": float(latitude[i]) if areas[i] else None,
         "longitude_centroid": float(longitude[i]) if areas[i] else None}
        for i in range(len(areas))]
    return result


def plot_review(cases, monthly_quality, lat, lon):
    fig, axes = plt.subplots(2, 3, figsize=(13, 7), constrained_layout=True)
    for ax, (key, out) in zip(axes.flat, cases.items()):
        image = ax.pcolormesh(lon, lat, out.eligible_support, vmin=0, vmax=1, cmap="cividis", shading="auto")
        ax.set(title=key, xlabel="Longitude", ylabel="Latitude")
    fig.colorbar(image, ax=axes.ravel().tolist(), label="Eligible cell (0 excluded, 1 retained)", shrink=.75)
    fig.suptitle("Sahel NDVI: static eligible footprints, 2001–2024")
    fig.savefig(OUT / "eligible_footprints.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(13, 10), constrained_layout=True)
    for key, out in cases.items():
        axes[0].plot(out.time, out.regional_monthly, label=key, linewidth=.7)
        axes[1].plot(out.time, out.observed_area_fraction_selected * 100, label=key, linewidth=.7)
        axes[2].plot(out.time, (1 - out.observed_area_fraction_eligible) * 100, label=key, linewidth=.7)
    for ax in axes:
        ax.grid(alpha=.2)
    axes[0].set(ylabel="NDVI (unitless)", title="Prepared regional series: different footprints and QA acceptance")
    axes[0].legend(ncols=3, fontsize=8)
    axes[1].set(ylabel="% of selected native-cell area", title="Area actually observed each month")
    axes[2].set(ylabel="% of eligible footprint missing", title="Monthly gaps remain missing; no imputation", xlabel="Year")
    fig.savefig(OUT / "monthly_series_and_support.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), constrained_layout=True)
    months = np.arange(1, 13)
    strict = [monthly_quality[f"month_{m:02}"]["strict_accepted_fraction"] for m in months]
    standard = [monthly_quality[f"month_{m:02}"]["standard_accepted_fraction"] for m in months]
    axes[0].plot(months, np.array(strict) * 100, "o-", label="Strict accepted")
    axes[0].plot(months, np.array(standard) * 100, "o-", label="Standard accepted")
    axes[0].set(ylabel="% of source cell-months", title="Calendar-month QA acceptance", xticks=months, xlabel="Calendar month")
    axes[0].legend()
    for key, out in cases.items():
        if key.endswith("100"):
            continue
        missing = 1 - out.observed_area_fraction_eligible
        axes[1].plot(months, missing.groupby("time.month").mean() * 100, "o-", label=key)
    axes[1].set(ylabel="% of eligible area-time missing", title="Seasonal gaps within relaxed footprints", xticks=months, xlabel="Calendar month")
    axes[1].legend(fontsize=8)
    fig.savefig(OUT / "calendar_month_quality.png", dpi=150)
    plt.close(fig)


def main():
    for folder in ("phase_2", "phase_2_standard"):
        baseline = ROOT / "data/derived/science" / folder / NAME
        if not baseline.is_file():
            raise FileNotFoundError(f"Existing Stage 2 baseline required; review will not regenerate it: {baseline}")
    OUT.mkdir(parents=True, exist_ok=True)
    preserved = preservation_snapshot()
    # An initial manifest persists across reruns: never silently reset history.
    snapshot_path = OUT / "preserved_originals.json"
    if snapshot_path.exists():
        historical = json.loads(snapshot_path.read_text())
        # The user authorized adding comparison displays to this notebook after
        # the checkpoint. It is presentation, not an input to QA calculations.
        # Preserve its current bytes within every run, but permit edits between
        # runs. Historical snapshots remain untouched; all data/policy/report
        # hashes still have to match the first review run exactly.
        presentation = "packages/science/notebooks/02_preprocessing.ipynb"
        if {k: v for k, v in historical.items() if k != presentation} != {
                k: v for k, v in preserved.items() if k != presentation}:
            raise ValueError("An original artifact changed since the first review run")
    else:
        write_json(snapshot_path, preserved)
    policy = load_policy()
    document = policy["sources"][0]
    if sha(ROOT / document["path"]) != document["sha256"]:
        raise ValueError("MOD13C2 documentation hash mismatch")
    entry = input_entry(VARIABLE, REGION)
    source = load_cube(VARIABLE, REGION)
    weights = cell_solid_angles(source.lat, source.lon, (.05, .05))
    w = weights.values
    months = source.time.dt.month.values
    fields = decode_cmg_quality(source.VI_Quality.values)
    fields["reliability"] = source.pixel_reliability.values
    qa, masks = {}, {}
    for mode in ("strict", "standard"):
        selected_policy = copy.deepcopy(policy)
        selected_policy["qa"]["modis_mode"] = mode
        qa[mode], _ = apply_product_qa(source, entry, selected_policy)
        masks[mode] = qa[mode].qa_accepted.values.astype(bool)
    marginal = masks["standard"] & ~masks["strict"]
    quality = quality_groups(masks["strict"], masks["standard"], fields, source.NDVI.values, w, months)
    write_json(REPORTS / "SAHEL_NDVI_QA_DISTRIBUTIONS.json", quality)
    print("Computed calendar-month and seasonal QA histograms", flush=True)
    result = {"revision": "sahel-qa-review-1.0", "inference_status": "not_computed",
              "default_changed": False, "source": entry, "source_sha256": sha(ROOT / entry["cube_file"]),
              "documentation": document, "canonical_policy_sha256": policy_hash(policy),
              "coverage_definition": "per-cell valid months / all 288 reference months after each QA mode",
              "season_definition": "DJF/MAM/JJA/SON pooled calendar months across 2001-2024; not climate regime labels",
              "area_denominator": "all 20000 centre-selected full native spherical cells; no polygon intersection",
              "imputation": "none", "cases": {}, "comparisons": {}}
    cases = {}
    baselines = {}
    for mode, folder in (("strict", "phase_2"), ("standard", "phase_2_standard")):
        with xr.open_dataset(ROOT / "data/derived/science" / folder / NAME) as ds:
            baselines[mode] = ds[["regional_monthly", "fixed_support", "qa_monthly"]].load()
        np.testing.assert_array_equal(np.isfinite(baselines[mode].qa_monthly), masks[mode])
    for mode in ("strict", "standard"):
        for fraction in (1., .95, .90):
            key = f"{mode}_{int(round(fraction * 100))}"
            out = coverage_experiment(qa[mode].NDVI, weights, fraction)
            out.attrs.update({"qa_mode": mode, "source_cube_sha256": result["source_sha256"],
                              "source_cube_file": entry["cube_file"], "canonical_policy_sha256": policy_hash(policy),
                              "product_id": "MOD13C2", "product_version": "061",
                              "variable_id": VARIABLE, "region_id": REGION})
            effective = copy.deepcopy(policy)
            effective["qa"]["modis_mode"] = mode
            out.attrs["effective_qa_policy_sha256"] = policy_hash(effective)
            for field in ("VI_Quality", "pixel_reliability"):
                out[field] = source[field]
            out["qa_accepted"] = qa[mode].qa_accepted
            if fraction == 1:
                np.testing.assert_array_equal(out.eligible_support, baselines[mode].fixed_support)
                np.testing.assert_allclose(out.regional_monthly, baselines[mode].regional_monthly, atol=1e-12, rtol=0)
            # A finite output exists exactly where an original QA-valid observation exists in an eligible cell.
            expected = masks[mode] & out.eligible_support.values.astype(bool)
            np.testing.assert_array_equal(np.isfinite(out.cell_monthly.values), expected)
            np.testing.assert_array_equal(out.cell_monthly.values[expected], source.NDVI.values[expected])
            target = OUT / f"{key}.nc"
            out.to_netcdf(target, encoding={k: {"zlib": True, "complevel": 4} for k in out.data_vars})
            with xr.open_dataset(target) as reopened:
                np.testing.assert_allclose(reopened.regional_monthly, out.regional_monthly, atol=0, rtol=0)
                np.testing.assert_array_equal(np.isfinite(reopened.cell_monthly), expected)
            stats = case_metrics(out, w, marginal, months, source.lat.values, source.lon.values)
            stats["artifact"] = target.relative_to(ROOT).as_posix()
            stats["artifact_sha256"] = sha(target)
            baseline_support = baselines[mode].fixed_support.values.astype(bool)
            stats["added_cells_vs_same_qa_100"] = int((out.eligible_support.values.astype(bool) & ~baseline_support).sum())
            stats["difference_from_same_qa_100"] = difference(out.regional_monthly.values, baselines[mode].regional_monthly.values)
            # On the baseline footprint all observations exist, so the mean must recover the baseline.
            common = qa[mode].NDVI.where(baselines[mode].fixed_support.astype(bool))
            common_weights = weights.where(baselines[mode].fixed_support.astype(bool), 0)
            common_mean = (common * (common_weights / common_weights.sum())).sum(("lat", "lon"), min_count=1)
            stats["same_qa_common_100_footprint_max_abs_difference"] = float(abs(common_mean - baselines[mode].regional_monthly).max())
            np.testing.assert_allclose(common_mean, baselines[mode].regional_monthly, atol=1e-12, rtol=0)
            result["cases"][key] = stats
            # Keep only small plotting fields/footprints after writing large cell arrays.
            cases[key] = out[["regional_monthly", "observed_area_fraction_selected", "observed_area_fraction_eligible", "eligible_support"]]
            print(f"{key}: {stats['eligible_cell_count']} cells; eligible area {stats['eligible_area_fraction_selected']:.6f}; "
                  f"monthly minimum {stats['monthly_observed_area_fraction_selected']['min']:.6f}", flush=True)
    result["comparisons"]["standard100_minus_strict100"] = difference(
        cases["standard_100"].regional_monthly.values, cases["strict_100"].regional_monthly.values)
    for season, mm in SEASONS.items():
        subset = np.isin(months, mm)
        result["comparisons"][f"standard100_minus_strict100_{season}"] = difference(
            cases["standard_100"].regional_monthly.values[subset], cases["strict_100"].regional_monthly.values[subset])
    for mode in ("strict", "standard"):
        result["comparisons"][f"{mode}90_minus_{mode}95"] = difference(
            cases[f"{mode}_90"].regional_monthly.values, cases[f"{mode}_95"].regional_monthly.values)
    # A QA change on the strict complete footprint changes neither values nor support.
    strict_support = baselines["strict"].fixed_support.astype(bool)
    common_weights = weights.where(strict_support, 0)
    standard_on_strict = (qa["standard"].NDVI.where(strict_support) *
                          (common_weights / common_weights.sum())).sum(("lat", "lon"), min_count=1)
    np.testing.assert_allclose(standard_on_strict, baselines["strict"].regional_monthly, atol=1e-12, rtol=0)
    result["comparisons"]["standardQA_on_strict100_footprint_minus_strict100"] = difference(
        standard_on_strict.values, baselines["strict"].regional_monthly.values)
    plot_review(cases, quality, source.lat.values, source.lon.values)
    after = preservation_snapshot()
    if after != preserved:
        raise AssertionError("Original artifacts changed during the review")
    result["verification"] = {"original_file_count": len(preserved), "all_original_sha256_unchanged": True,
                              "baseline_100_masks_equal": True, "baseline_100_series_max_tolerance": 1e-12,
                              "finite_output_equals_observed_eligible_source": True,
                              "netcdf_reopen_checks": True, "preservation_snapshot": snapshot_path.relative_to(ROOT).as_posix(),
                              "preserved_originals_sha256": preserved}
    write_json(REPORTS / "SAHEL_NDVI_POLICY_METRICS.json", result)
    print("Original files preserved; wrote checkpoint metrics, six separate NetCDF cases and three figures.")


if __name__ == "__main__":
    main()
