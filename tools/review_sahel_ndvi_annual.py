"""Read-only review of existing Sahel NDVI inputs; write isolated annual evidence."""
from __future__ import annotations

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
from src.annual_coverage_review import annual_support_review
from src.data_loader import load_cube
from src.preprocessing import annual_summary
from src.qa_policy_review import distribution, missingness_groups
from review_sahel_ndvi import difference, preservation_snapshot, sha, write_json

REPORTS = ROOT / "packages/science/phase_reports"
OUT = ROOT / "data/derived/science/sahel_ndvi_annual_review"
LABELS = {"strict_100": "Strict 100% (default)", "standard_100": "Standard 100%",
          "standard_95": "Standard 95% (experimental)"}


def number(value):
    value = float(value)
    return value if np.isfinite(value) else None


def old_files():
    snapshot = preservation_snapshot()
    for folder in (ROOT / "data/derived/science/sahel_ndvi_policy_review",
                   ROOT / "data/derived/science/sahel_ndvi_preprocessing_comparison"):
        snapshot.update({p.relative_to(ROOT).as_posix(): sha(p) for p in folder.rglob("*") if p.is_file()})
    snapshot.update({p.relative_to(ROOT).as_posix(): sha(p) for p in REPORTS.glob("SAHEL_NDVI_POLICY*")})
    p = REPORTS / "SAHEL_NDVI_QA_DISTRIBUTIONS.json"
    snapshot[p.relative_to(ROOT).as_posix()] = sha(p)
    return snapshot


def month_records(ds, annual, weights):
    observed = np.isfinite(ds.cell_monthly.values)
    eligible = ds.eligible.values.astype(bool)
    w = weights.values
    selected_area, eligible_area = float(w.sum()), float(w[eligible].sum())
    lat = np.broadcast_to(ds.lat.values[:, None], w.shape)
    lon = np.broadcast_to(ds.lon.values[None, :], w.shape)
    rows = []
    for i, time in enumerate(ds.time.values):
        mask = observed[i]
        area = float(w[mask].sum())
        prev = observed[i - 1] if i else None
        intersection = float(w[mask & prev].sum()) if i else None
        union = float(w[mask | prev].sum()) if i else None
        rows.append({"month": str(time)[:7], "regional_ndvi": number(ds.regional_monthly.values[i]),
                     "observed_cell_count": int(mask.sum()),
                     "missing_eligible_cell_count": int((eligible & ~mask).sum()),
                     "structurally_excluded_cell_count": int((~eligible).sum()),
                     "valid_area_fraction_selected": area / selected_area,
                     "valid_area_fraction_eligible": area / eligible_area if eligible_area else None,
                     "missing_eligible_area_fraction": float(w[eligible & ~mask].sum()) / eligible_area if eligible_area else None,
                     "changed_area_fraction_selected_since_previous_month": float(w[mask ^ prev].sum()) / selected_area if i else None,
                     "observed_area_jaccard_with_previous_month": intersection / union if union else None,
                     "observed_latitude_centroid": float((w[mask] * lat[mask]).sum()) / area if area else None,
                     "observed_longitude_centroid": float((w[mask] * lon[mask]).sum()) / area if area else None})
    groups = missingness_groups(observed, eligible, w, ds.time.dt.month.values)
    years = ds.time.dt.year.values
    annual_rows = []
    for y in annual.year.values:
        a = annual.sel(year=y)
        subset = observed[years == y]
        monthly_area = annual.observed_area_fraction_selected.isel(time=np.flatnonzero(years == y))
        missing = eligible & ~subset
        area_time = eligible_area * len(subset)
        count = int(eligible.sum()) * len(subset)
        annual_rows.append({"year": int(y), "calendar_records_present": len(subset),
                            "valid_regional_months": int(ds.regional_monthly.isel(time=np.flatnonzero(years == y)).notnull().sum()),
                            "missing_eligible_cell_months": int(missing.sum()),
                            "eligible_cell_month_denominator": count,
                            "missing_eligible_cell_month_fraction": int(missing.sum()) / count if count else None,
                            "missing_eligible_area_time_fraction": float((missing * w).sum()) / area_time if area_time else None,
                            "incomplete_eligible_cell_years": int(a.incomplete_eligible_cell_count),
                            "complete_cell_years": int(a.complete_cell_count),
                            "complete_cell_area_fraction_selected": float(a.complete_cell_area_fraction_selected),
                            "mean_monthly_valid_area_fraction_selected": float(monthly_area.mean("time")),
                            "minimum_monthly_valid_area_fraction_selected": float(monthly_area.min("time")),
                            "regional_annual_from_monthly": number(a.regional_annual_from_monthly),
                            "regional_annual_complete_cell_years": number(a.regional_annual_complete_cell_years),
                            "season_missingness": missingness_groups(subset, eligible, w, ds.time.dt.month.values[years == y])["season"]})
        np.testing.assert_allclose(annual_rows[-1]["mean_monthly_valid_area_fraction_selected"],
                                   eligible_area / selected_area * (1 - annual_rows[-1]["missing_eligible_area_time_fraction"]),
                                   atol=1e-12, rtol=0)
    assert sum(r["missing_eligible_cell_months"] for r in annual_rows) == sum(r["missing_eligible_cell_count"] for r in rows)
    return {"monthly": rows, "calendar_month": groups["calendar_month"], "season": groups["season"],
            "annual": annual_rows, "eligible_cell_count": int(eligible.sum()),
            "eligible_area_fraction_selected": eligible_area / selected_area,
            "structurally_excluded_cells": int((~eligible).sum()),
            "missing_eligible_cell_months": sum(r["missing_eligible_cell_count"] for r in rows),
            "incomplete_eligible_cell_years": sum(r["incomplete_eligible_cell_years"] for r in annual_rows),
            "unique_eligible_cells_with_any_gap": int((eligible & ~observed.all(axis=0)).sum()),
            "incomplete_regional_annual_records": sum(r["regional_annual_from_monthly"] is None for r in annual_rows),
            "monthly_changed_area_fraction_selected": distribution([r["changed_area_fraction_selected_since_previous_month"] for r in rows[1:]]),
            "monthly_observed_latitude_centroid": distribution([r["observed_latitude_centroid"] for r in rows])}


def plots(metrics, cases, annual):
    fig, axes = plt.subplots(1, 2, figsize=(13, 7), constrained_layout=True)
    missing = np.array([r["missing_eligible_area_fraction"] for r in metrics["policies"]["standard_95"]["monthly"]]).reshape(24, 12) * 100
    delta = (cases["standard_95"].regional_monthly.values - cases["standard_100"].regional_monthly.values).reshape(24, 12)
    for ax, values, title, cmap, units in (
            (axes[0], missing, "Standard 95%: eligible area missing", "YlOrRd", "% of eligible footprint"),
            (axes[1], delta, "Monthly NDVI: standard 95% minus 100%", "viridis", "NDVI difference (unitless)")):
        im = ax.imshow(values, aspect="auto", origin="lower", cmap=cmap, vmin=0)
        ax.set(xticks=np.arange(12), xticklabels=np.arange(1, 13), yticks=np.arange(24),
               yticklabels=np.arange(2001, 2025), xlabel="Calendar month", ylabel="Year", title=title)
        fig.colorbar(im, ax=ax, label=units, shrink=.85)
    fig.savefig(OUT / "monthly_missingness_and_difference.png", dpi=150)
    plt.close(fig)
    fig, axes = plt.subplots(3, 1, figsize=(12, 10), constrained_layout=True)
    for key, color in (("standard_100", "#e8790c"), ("standard_95", "#15956f")):
        a = annual[key]
        axes[0].plot(a.year, a.regional_annual_from_monthly, "o-", label=LABELS[key], color=color)
        axes[1].plot(a.year, a.incomplete_eligible_cell_count, "o-", label=LABELS[key], color=color)
    axes[0].plot(annual["standard_95"].year, annual["standard_95"].regional_annual_complete_cell_years,
                 "--", color="#374151", label="95%: complete cell-years only (diagnostic)")
    rows = metrics["policies"]["standard_95"]["annual"]
    axes[2].plot(np.arange(2001, 2025), [r["minimum_monthly_valid_area_fraction_selected"] * 100 for r in rows], label="95% minimum monthly area")
    axes[2].plot(np.arange(2001, 2025), [r["mean_monthly_valid_area_fraction_selected"] * 100 for r in rows], color="#15956f", label="95% mean monthly area")
    axes[2].plot(annual["standard_95"].year, annual["standard_95"].complete_cell_area_fraction_selected * 100, color="#7c3aed", label="95% complete cell-year area")
    axes[2].axhline(metrics["policies"]["standard_100"]["eligible_area_fraction_selected"] * 100, color="#e8790c", label="100% fixed area")
    axes[0].set(ylabel="Annual NDVI (unitless)", title="Day-weighted annual means; no trend inference")
    axes[1].set(ylabel="Incomplete eligible cell-years", title="A regional annual value can coexist with missing cell annual values")
    axes[2].set(ylabel="% of selected native-cell area", xlabel="Year", title="Monthly and annual spatial coverage")
    for ax in axes:
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.savefig(OUT / "annual_series_and_completeness.png", dpi=150)
    plt.close(fig)


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |",
                      *["| " + " | ".join(str(x) for x in row) + " |" for row in rows]])


def coverage_appendix(metrics):
    rows = []
    for s, e in zip(metrics["policies"]["standard_100"]["monthly"], metrics["policies"]["standard_95"]["monthly"]):
        rows.append([e["month"], f'{s["valid_area_fraction_selected"] * 100:.6f}',
                     f'{e["valid_area_fraction_selected"] * 100:.6f}', f'{e["valid_area_fraction_eligible"] * 100:.6f}',
                     e["missing_eligible_cell_count"], f'{s["regional_ndvi"]:.6f}', f'{e["regional_ndvi"]:.6f}'])
    text = """# Sahel Standard 95%: all 288 monthly coverage records

Generated by `tools/review_sahel_ndvi_annual.py`. All values are read from existing
prepared files. Selected area means all 20,000 centre-selected native full cells;
eligible area means the policy's own static footprint. NDVI is unitless. Missing
cell values remain missing; regional means use only observed eligible area.
There are five permanently excluded cells under Standard 95%, separate from the
missing eligible cells below. All Standard 100% eligible cells are observed each
month. See [the checkpoint](SAHEL_NDVI_STANDARD95_REVIEW.md) for annual completeness.

"""
    text += table(["Month", "100% valid selected area %", "95% valid selected area %", "95% valid eligible area %",
                   "95% missing eligible cells", "100% regional NDVI", "95% regional NDVI"], rows) + "\n"
    (REPORTS / "SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md").write_text(text, encoding="utf-8")


def checkpoint_report(metrics):
    e, s = metrics["policies"]["standard_95"], metrics["policies"]["standard_100"]
    c = metrics["comparisons"]
    worst = min(e["monthly"], key=lambda r: r["valid_area_fraction_selected"])
    yearly = {r["year"]: r for r in e["annual"]}
    incomplete_denominator = e["eligible_cell_count"] * 24
    policy_rows = [[LABELS[key], p["eligible_cell_count"], f'{p["eligible_area_fraction_selected"] * 100:.4f}%',
                    p["missing_eligible_cell_months"], p["incomplete_eligible_cell_years"], p["incomplete_regional_annual_records"]]
                   for key, p in metrics["policies"].items()]
    month_rows = [[month, g["missing_cell_months"], f'{g["missing_cell_month_fraction"] * 100:.6f}%',
                   f'{g["missing_area_time_fraction"] * 100:.6f}%'] for month, g in e["calendar_month"].items()]
    season_rows = [[season, g["missing_cell_months"], f'{g["missing_area_time_fraction"] * 100:.6f}%'] for season, g in e["season"].items()]
    year_rows = [[a["year"], a["missing_eligible_cell_months"], a["incomplete_eligible_cell_years"],
                  f'{a["missing_eligible_area_time_fraction"] * 100:.6f}%',
                  f'{a["minimum_monthly_valid_area_fraction_selected"] * 100:.4f}%',
                  f'{b["regional_annual_from_monthly"]:.6f}', f'{a["regional_annual_from_monthly"]:.6f}',
                  f'{a["regional_annual_from_monthly"] - b["regional_annual_from_monthly"]:+.6f}']
                 for a, b in zip(e["annual"], s["annual"])]
    report = f"""# Stage 2 checkpoint: Standard 95% NDVI monthly and annual review

Date: 15 November 2026. Branch: `codex/ml-statistics`.
Status: **review complete; Phase 3 decision pending**. Default: **unchanged**.

## Recommendation for Phase 3

Keep all three policies available: **Strict 100% as the unchanged default/control**,
**Standard 100% as the fixed-footprint comparison**, and **Standard 95% as an
experimental coverage sensitivity**. These results support carrying all three
into Phase 3 estimator validation, with explicit footprint labels. They do not
support promoting Standard 95% to the default or interpreting its annual regional
series as a constant-area average.

Standard 95% improves eligibility to 99.9751% of selected native-cell area, but
missing observations concentrate in particular months and years. Its regional
annual series has all 24 years, while **{e['incomplete_eligible_cell_years']:,} eligible cell-year
records remain incomplete and their cell annual values stay missing**. Phase 3
must retain monthly support diagnostics, compare common geography and test the
effect of the annual aggregation choice before interpreting temporal change.
Phase 3 has not started. No slopes or inference were computed.

## Inputs and preservation

Review scope: MOD13C2 Collection 6.1 NDVI in the Sahel rectangle [-5, 12, 5, 17],
January 2001 through December 2024; 20,000 cells and 288 months. NDVI is already
scaled and dimensionless. This review reads the existing original strict and
standard artifacts plus the existing experimental `standard_95.nc`. It does
not regenerate their values or modify QA, eligibility, weights or default policy.

The 95% rule requires at least 274 of 288 valid months per cell over the fixed
full reference. Standard 100% requires all 288. Both use the same standard QA.
The detailed-QA interpretation and marginal-data limitations remain those in the
[earlier policy checkpoint](SAHEL_NDVI_POLICY_CHECKPOINT.md); no new QA cutoff
or accuracy claim is introduced here. The experimental 90% and strict relaxed
stress cases also remain available in their original locations.

The run preserved **{metrics['verification']['preserved_file_count']} existing files** by before/after SHA-256,
including source cubes, policy, original outputs, earlier review artifacts and
the preprocessing notebook. New annual arrays and figures use a separate folder.

{table(['Policy', 'Eligible cells', 'Eligible selected area', 'Missing eligible cell-months', 'Incomplete eligible cell-years', 'Incomplete regional annual records'], policy_rows)}

Area denominators are full native spherical cells selected by their centres;
they are not exact polygon-intersection areas. Cell-count percentages and area
percentages differ with latitude. Structural exclusions are separate from
missing observations inside an eligible footprint.

## Missing observations by month, season and year

Standard 95% has **{e['missing_eligible_cell_months']:,} missing values out of
5,758,560 eligible cell-months** ({e['missing_eligible_cell_months'] / 5758560 * 100:.6f}%). Its five structurally
excluded cells represent another 1,440 cell-month positions, excluded from this
missingness denominator. There are 101 months with at least one eligible gap and
187 months with none. Across the 24 years, 3,464 eligible cells have at least one
gap; this is not the same count as incomplete cell-years, because a cell can be
incomplete in more than one year.

Each calendar-month row pools 24 occurrences across all eligible cells. Missing
area-time weights every constituent monthly cell by its native area; it does
not insert an NDVI value or weight by days. Annual NDVI uses day weights below.

{table(['Calendar month', 'Missing eligible cell-months', 'Missing count fraction', 'Missing eligible area-time'], month_rows)}

{table(['Season', 'Missing eligible cell-months', 'Missing eligible area-time'], season_rows)}

DJF means December/January/February, MAM March–May, JJA June–August and SON
September–November. These are pooled calendar groups, not claims about local
wet/dry seasons or constructed winter years. **{5102 / 5279 * 100:.2f}% of eligible gaps occur in JJA**.
The JSON also supplies season counts within each calendar year (DJF there uses
January, February and December of that same year, not a continuous winter).

The year table below gives missingness, annual completeness and the annual
policy comparison. Each complete year contains 239,940 eligible cell-month
positions under Standard 95%. All years have 12 valid regional monthly means.
The annual NDVI columns use day-weighted monthly regional means, as explained below.

{table(['Year', 'Missing eligible cell-months', 'Incomplete eligible cell-years', 'Missing eligible area-time', 'Worst monthly selected area', 'Annual NDVI 100%', 'Annual NDVI 95%', '95% minus 100%'], year_rows)}

Every month is reported individually in the
[288-row coverage appendix](SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md), including
valid selected-area percentages for both policies, valid eligible area under
95%, missing eligible cell counts, and the two monthly regional NDVI values.
Full-precision values and all three policies are in the JSON evidence.

![Monthly gaps and policy differences](../../../data/derived/science/sahel_ndvi_annual_review/monthly_missingness_and_difference.png)

## Does the regional average change its spatial support?

**Yes for Standard 95%.** Its eligibility footprint stays fixed at 19,995 cells,
but a monthly regional mean uses only currently observed eligible cells and
renormalizes their spherical area weights. Standard 100%'s 16,531 cells remain
observed in every month, so that policy's contributing geography is constant.

In the worst month, **{worst['month']}**, Standard 95% observes {worst['observed_cell_count']:,} cells,
with {worst['missing_eligible_cell_count']:,} eligible cells missing. Valid area is
**{worst['valid_area_fraction_selected'] * 100:.4f}% of the selected rectangle cells**, or
**{worst['valid_area_fraction_eligible'] * 100:.4f}% of the eligible footprint**. A 95% per-cell
full-period threshold therefore does not guarantee 95% regional area in every month.
Standard 100% observes 82.5869% of selected native-cell area in every month.

Between successive months, the area switching into or out of Standard 95%'s
contributing set averages {e['monthly_changed_area_fraction_selected']['mean'] * 100:.4f}% of selected area and reaches
{e['monthly_changed_area_fraction_selected']['max'] * 100:.4f}%. This counts the symmetric difference of sets, not just
net area change. Its contributing-area latitude centroid ranges from
{e['monthly_observed_latitude_centroid']['min']:.4f} to {e['monthly_observed_latitude_centroid']['max']:.4f} degrees north.
These diagnostics show that geography and weights change, even when the total
area change is small. They do not measure missing locations' unknown NDVI.

## Monthly and annual series: what changes and what does not?

Across 288 paired monthly regional values, Standard 95% minus Standard 100%
has a mean **{c['monthly_95_minus_100']['candidate_minus_baseline']['mean']:.6f} NDVI**, minimum
{c['monthly_95_minus_100']['candidate_minus_baseline']['min']:.6f}, maximum
{c['monthly_95_minus_100']['candidate_minus_baseline']['max']:.6f}, and RMSE
{c['monthly_95_minus_100']['root_mean_square_difference']:.6f}. These are descriptive differences, not error estimates.
On the **common Standard 100% footprint**, the Standard 95% source values
recover the original monthly and annual Standard 100% series to absolute tolerance
1e-12. Thus these contrasts arise from added locations and their availability,
not new measurements, rescaling, or different QA at shared observations.

Two annual estimates are explicitly distinguished:

1. **Annual mean of regional monthly means:** require twelve finite regional
   monthly values and average using actual calendar-month day counts. For Standard
   95%, each of those twelve monthly means can have a different footprint. All 24
   annual records are present for both policies; that does not establish complete
   spatial observations. This definition matches the original regional annual
   preparation rule, with an explicit changing-support caveat.
2. **Diagnostic annual mean over complete cell-years:** first require twelve
   original valid months in each cell-year and compute its day-weighted annual
   NDVI. Leave incomplete cell-years missing. Then average the complete cell
   annual values by native area. This uses a constant set of cells within each
   year but can change geography between years; it is not a replacement default.

Standard 95% has **{e['incomplete_eligible_cell_years']:,} incomplete eligible cell-years out of
{incomplete_denominator:,}** ({e['incomplete_eligible_cell_years'] / incomplete_denominator * 100:.4f}%), leaving
{incomplete_denominator - e['incomplete_eligible_cell_years']:,} complete cell-year annual values. The five structurally
excluded cells are not counted as incomplete eligible records. Strict 100% and
Standard 100% each have no incomplete cell-years inside their own smaller footprints.

For the first annual definition, the mean difference over 24 paired years is
**{c['annual_95_minus_100']['candidate_minus_baseline']['mean']:.6f} NDVI**, ranging from
{c['annual_95_minus_100']['candidate_minus_baseline']['min']:.6f} to {c['annual_95_minus_100']['candidate_minus_baseline']['max']:.6f}; RMSE is
{c['annual_95_minus_100']['root_mean_square_difference']:.6f}. Requiring complete cell-years in Standard 95% changes its
annual estimate by a mean {c['annual_95_monthly_means_minus_complete_cell_years']['candidate_minus_baseline']['mean']:.6f} NDVI (monthly-regional definition
minus complete-cell definition), with maximum absolute difference
**{c['annual_95_monthly_means_minus_complete_cell_years']['max_absolute_difference']:.6f}** in 2015. This comparison changes the
spatial sample; it does not recover the unknown values in missing cells.

In 2015 specifically, {yearly[2015]['incomplete_eligible_cell_years']:,} eligible cell-years are incomplete. The
Standard 95% annual regional mean is {yearly[2015]['regional_annual_from_monthly']:.6f}, whereas the complete-cell-year diagnostic
is {yearly[2015]['regional_annual_complete_cell_years']:.6f}. Its complete-cell-year area is only
{yearly[2015]['complete_cell_area_fraction_selected'] * 100:.4f}% of selected native-cell area, compared with static 99.9751%
eligibility. A year with twelve regional points is not an all-area complete year.

![Annual series and completeness](../../../data/derived/science/sahel_ndvi_annual_review/annual_series_and_completeness.png)

## Preservation of missing values and scientific trade-offs

No interpolation, zero filling, forward filling, climatological reconstruction,
or rescaling was applied. Every finite prepared cell value equals its original
source value exactly. Incomplete cell annual values remain NaN. If an annual
regional input lacks a valid month, its annual value is NaN; if no complete
cell-years remain, their diagnostic regional mean is NaN. Zero mask values,
excluded weights and missing counts are bookkeeping, not replacement NDVI.

Broader eligibility reduces the geographic exclusion evident in strict data,
but adds marginal observations and time-varying spatial composition. Summer-
concentrated missingness and the uneven year distribution can affect seasonal
amplitude and annual averages. More retained area or higher NDVI does not prove
higher accuracy. Neither complete regional records nor this review establish
representativeness, missing-at-random behavior, measurement-error magnitude or
statistical significance.

## Phase 3 handoff and reproducibility

- Preserve Strict 100% as default/control and Standard 100% as the constant-
  footprint comparison. Continue to label their geographic restrictions.
- Carry Standard 95% only as an explicitly experimental monthly and annual
  sensitivity. Retain its 288 observed-area records and masks, plus incomplete
  cell-year flags. Compare the same dates and common spatial footprint.
- Keep the two annual definitions separate. Use 2015 and other low-coverage
  periods as preparation sensitivity checks in estimator validation. Any new
  monthly-area gate, seasonal completeness threshold, QA cutoff or default
  promotion needs an explicit versioned decision; none was imposed here.
- Test missing/short/seasonal inputs and explicit elapsed-year units in Phase 3
  before interpreting slopes. Leave inference and application readiness unchanged.

Reproduce this read-only-input review from the repository root:
`.\\.venv\\Scripts\\python.exe tools/review_sahel_ndvi_annual.py`.
It requires the already prepared original and experimental files; it does not
rebuild them. New arrays/figures are in
`data/derived/science/sahel_ndvi_annual_review/` (ignored by Git).
The three `*_annual_review.nc` files store complete/incomplete cell-year counts,
missing-preserving cell annual values, both annual regional estimates and area
diagnostics. The original three preprocessing policies remain available unchanged.

Evidence: [full JSON](SAHEL_NDVI_STANDARD95_REVIEW.json),
[all monthly coverage records](SAHEL_NDVI_STANDARD95_MONTHLY_COVERAGE.md),
[earlier QA checkpoint](SAHEL_NDVI_POLICY_CHECKPOINT.md).
The generator verifies original hashes, source-value identity, QA/support masks,
canonical annual reproduction, common-footprint monthly/annual agreement, year
accounting and NetCDF reopening. Validation command:
`.\\.venv\\Scripts\\python.exe -m unittest discover -s packages/science/tests -q`.
**51 tests pass**, including seven new annual/completeness checks.
"""
    (REPORTS / "SAHEL_NDVI_STANDARD95_REVIEW.md").write_text(report, encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    before = old_files()
    previous = json.loads((REPORTS / "SAHEL_NDVI_POLICY_METRICS.json").read_text())
    coverage = json.loads((REPORTS / "PHASE_2_COVERAGE.json").read_text())
    sensitivity = json.loads((REPORTS / "PHASE_2_QA_SENSITIVITY.json").read_text())
    records = {
        "strict_100": next(e for e in coverage["entries"] if e["variable_id"] == "vegetation_greenness" and e["region_id"] == "sahel_comparison"),
        "standard_100": next(e for e in sensitivity["entries"] if e["region_id"] == "sahel_comparison"),
        "standard_95": previous["cases"]["standard_95"],
    }
    source = load_cube("vegetation_greenness", "sahel_comparison")
    assert sha(ROOT / previous["source"]["cube_file"]) == previous["source_sha256"]
    result = {"revision": "standard95-annual-review-1.0", "period": ["2001-01", "2024-12"],
              "inference_status": "not_computed", "default_changed": False, "imputation": "none",
              "annual_rule": "calendar-day-weighted mean requiring twelve valid original months",
              "season_rule": "pooled DJF/MAM/JJA/SON calendar groups, not winter-year aggregates",
              "policies": {}, "comparisons": {}}
    cases, annual = {}, {}
    for key, record in records.items():
        path = ROOT / record["artifact"]
        assert sha(path) == record["artifact_sha256"], str(path)
        support = "eligible_support" if key == "standard_95" else "fixed_support"
        fields = ["cell_monthly", "regional_monthly", support, "qa_accepted", "native_cell_solid_angle"]
        if key != "standard_95":
            fields += ["cell_annual", "regional_annual"]
        with xr.open_dataset(path) as opened:
            ds = opened[fields].load().rename({support: "eligible"})
        cases[key] = ds
        weights = ds.native_cell_solid_angle
        valid = np.isfinite(ds.cell_monthly.values)
        np.testing.assert_array_equal(valid, ds.qa_accepted.values.astype(bool) & ds.eligible.values.astype(bool))
        np.testing.assert_array_equal(ds.cell_monthly.values[valid], source.NDVI.values[valid])
        a = annual_support_review(ds.cell_monthly, ds.regional_monthly, ds.eligible, weights)
        annual[key] = a
        if key != "standard_95":
            np.testing.assert_allclose(a.cell_annual, ds.cell_annual, atol=1e-12, rtol=0, equal_nan=True)
            np.testing.assert_allclose(a.regional_annual_from_monthly, ds.regional_annual, atol=1e-12, rtol=0, equal_nan=True)
        a.attrs.update({"policy": key, "source_artifact": record["artifact"], "source_artifact_sha256": record["artifact_sha256"]})
        destination = OUT / f"{key}_annual_review.nc"
        a.to_netcdf(destination, encoding={k: {"zlib": True, "complevel": 4} for k in a.data_vars})
        with xr.open_dataset(destination) as reopened:
            xr.testing.assert_allclose(reopened, a)
        result["policies"][key] = {**month_records(ds, a, weights), "source_artifact": record["artifact"],
                                   "source_artifact_sha256": record["artifact_sha256"],
                                   "annual_review_artifact": destination.relative_to(ROOT).as_posix(),
                                   "annual_review_sha256": sha(destination)}
        print(f"{key}: {result['policies'][key]['missing_eligible_cell_months']} missing cell-months; "
              f"{result['policies'][key]['incomplete_eligible_cell_years']} incomplete cell-years", flush=True)
    standard, experimental = cases["standard_100"], cases["standard_95"]
    np.testing.assert_array_equal(standard.eligible.values.astype(bool) & ~experimental.eligible.values.astype(bool), False)
    np.testing.assert_array_equal(cases["strict_100"].eligible.values.astype(bool) & ~standard.eligible.values.astype(bool), False)
    common_cells = experimental.cell_monthly.where(standard.eligible.astype(bool))
    common_weights = weights.where(standard.eligible.astype(bool), 0)
    common_mean = (common_cells * (common_weights / common_weights.sum())).sum(("lat", "lon"), min_count=1)
    common_mean.attrs["units"] = "1"
    np.testing.assert_allclose(common_mean, standard.regional_monthly, atol=1e-12, rtol=0)
    np.testing.assert_allclose(annual_summary(common_mean, "vegetation_greenness"), standard.regional_annual, atol=1e-12, rtol=0)
    result["comparisons"] = {
        "monthly_95_minus_100": difference(experimental.regional_monthly.values, standard.regional_monthly.values),
        "annual_95_minus_100": difference(annual["standard_95"].regional_annual_from_monthly.values, standard.regional_annual.values),
        "annual_95_monthly_means_minus_complete_cell_years": difference(annual["standard_95"].regional_annual_from_monthly.values,
                                                                       annual["standard_95"].regional_annual_complete_cell_years.values),
        "annual_95_complete_cell_years_minus_100": difference(annual["standard_95"].regional_annual_complete_cell_years.values, standard.regional_annual.values),
        "common_standard100_footprint_max_abs_monthly_difference": float(abs(common_mean - standard.regional_monthly).max()),
    }
    for key, comparison in result["comparisons"].items():
        if key.startswith("annual_"):
            comparison["paired_years"] = comparison.pop("paired_months")
    plots(result, cases, annual)
    assert before == old_files(), "An original file changed"
    result["verification"] = {"preserved_file_count": len(before), "all_original_hashes_unchanged": True,
                              "source_values_and_missing_masks_verified": True,
                              "canonical_annual_outputs_reproduced": True, "annual_netcdf_reopen_verified": True,
                              "preserved_sha256": before}
    write_json(REPORTS / "SAHEL_NDVI_STANDARD95_REVIEW.json", result)
    coverage_appendix(result)
    checkpoint_report(result)
    print("Wrote annual review metrics, 288 monthly coverage rows and isolated annual diagnostic arrays.")


if __name__ == "__main__":
    main()
