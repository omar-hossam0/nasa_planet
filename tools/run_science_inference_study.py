"""Reproducible Phase 4 research: calibration first; no automatic inference release."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import false_discovery_control, norm

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.inference import adjust_fdr, annual_inference, wilson_interval
from src.preprocessing import policy_hash
from src.trend_estimation import trend_series
from review_sahel_ndvi import sha, write_json
from run_science_trends import load_cases, load_prepared

REPORTS = ROOT / "packages/science/phase_reports"
# Deliberately outside the earlier phase's immutable source-snapshot tree.
OUT = ROOT / "data/derived/science_inference/phase_4"


def preserved_inputs():
    old = json.loads((REPORTS / "PHASE_3_VALIDATION.json").read_text())["stage2_sha256"]
    for file, expected in old.items():
        assert sha(ROOT / file) == expected, file
    paths = [*REPORTS.glob("PHASE_3*"), ROOT / "packages/science/notebooks/03_trend_validation.ipynb",
             ROOT / "packages/science/config/trend_policy.json", ROOT / "packages/science/src/trend_estimation.py"]
    paths += [p for p in (ROOT / "data/derived/science/phase_3").rglob("*") if p.is_file()]
    return {**old, **{p.relative_to(ROOT).as_posix(): sha(p) for p in paths}}


def ar1(rng, samples, n, phi):
    # Burn-in plus stationary innovation scaling; marginal variance approximately 1.
    noise = rng.normal(scale=np.sqrt(1 - phi * phi), size=(samples, n + 200))
    for i in range(1, n + 200):
        noise[:, i] += phi * noise[:, i - 1]
    return noise[:, -n:]


def summarize_simulation(values, years, truth, block, config, label):
    count = len(values)
    slopes, widths, covered, rejected = [], [], 0, 0
    for i, series in enumerate(values):
        outcome = annual_inference(series, years, block_length=block,
                                   replicates=config["bootstrap_replicates"],
                                   confidence=config["confidence_level"], seed=config["monte_carlo"]["seed"] + i,
                                   min_points=config["minimum_annual_observations"])
        assert outcome["status"] == "candidate_diagnostic"
        slopes.append(outcome["slope_per_year"])
        lo, hi = outcome["interval_candidate"]
        widths.append(hi - lo)
        covered += lo <= truth <= hi
        rejected += outcome["p_value_candidate"] <= config["alpha"]
    estimate = np.asarray(slopes)
    return {"scenario": label, "n_years": len(years), "true_slope_per_year": truth,
            "block_length_years": block, "replications": count,
            "covered": int(covered), "coverage": covered / count,
            "coverage_mc95": wilson_interval(int(covered), count),
            "rejected": int(rejected), "rejection_rate": rejected / count,
            "rejection_mc95": wilson_interval(int(rejected), count),
            "rejection_interpretation": "false_positive_rate" if truth == 0 else "power",
            "mean_interval_width": float(np.mean(widths)),
            "mean_slope_bias": float(np.mean(estimate - truth)),
            "slope_rmse": float(np.sqrt(np.mean((estimate - truth) ** 2)))}


def monte_carlo(config):
    mc = config["monte_carlo"]
    count, base_seed = mc["replications_per_scenario"], mc["seed"]
    results = []
    for n in mc["null_lengths"]:
        for phi in mc["ar1_phi"]:
            rng = np.random.default_rng(np.random.SeedSequence([base_seed, n, int(phi * 100), 0]))
            errors = ar1(rng, count, n, phi)
            for block in config["block_length_sensitivity_years"]:
                label = f"annual_ar1_null_phi{phi}_n{n}"
                record = summarize_simulation(errors, np.arange(2001, 2001 + n), 0., block, config, label)
                record.update({"model": "annual_ar1", "phi": phi, "record_seed_components": [base_seed, n, int(phi * 100), 0]})
                results.append(record)
                write_json(OUT / "simulation_progress.json", {"policy_sha256": policy_hash(config), "records": results})
                print(f"{label}, block={block}: false positive={record['rejection_rate']:.3f}, coverage={record['coverage']:.3f}", flush=True)
    n = mc["power_length"]
    for phi in mc["ar1_phi"]:
        rng = np.random.default_rng(np.random.SeedSequence([base_seed, n, int(phi * 100), 1]))
        errors = ar1(rng, count, n, phi)
        for truth in mc["power_slopes_per_year"]:
            for block in config["block_length_sensitivity_years"]:
                if block == 1:
                    continue
                label = f"annual_ar1_power_phi{phi}_slope{truth}"
                values = errors + truth * np.arange(n)
                record = summarize_simulation(values, np.arange(2001, 2001 + n), truth, block, config, label)
                record.update({"model": "annual_ar1", "phi": phi, "record_seed_components": [base_seed, n, int(phi * 100), 1]})
                results.append(record)
                write_json(OUT / "simulation_progress.json", {"policy_sha256": policy_hash(config), "records": results})
                print(f"{label}, block={block}: power={record['rejection_rate']:.3f}, coverage={record['coverage']:.3f}", flush=True)
    # Repeated strong monthly seasonal cycles aggregated into complete annual
    # records with actual Gregorian day weights; no monthly inference is implied.
    import xarray as xr
    from src.preprocessing import annual_summary
    months = np.arange(np.datetime64("2001-01"), np.datetime64("2025-01")).astype("datetime64[ns]")
    for phi in (0., .7):
        rng = np.random.default_rng(np.random.SeedSequence([base_seed, 288, int(phi * 100), 2]))
        monthly = ar1(rng, count, 288, phi) + 3 * np.sin(2 * np.pi * np.arange(288) / 12)
        data = xr.DataArray(monthly.T, dims=("time", "replication"), coords={"time": months}, attrs={"units": "1"})
        annual = annual_summary(data, "vegetation_greenness").values.T
        for block in (3, 4, 6):
            label = f"monthly_seasonal_null_annualized_phi{phi}"
            record = summarize_simulation(annual, np.arange(2001, 2025), 0., block, config, label)
            record.update({"model": "annualized_monthly_seasonal", "monthly_phi": phi,
                           "seasonal_amplitude": 3., "record_seed_components": [base_seed, 288, int(phi * 100), 2]})
            results.append(record)
            print(f"{label}, block={block}: false positive={record['rejection_rate']:.3f}, coverage={record['coverage']:.3f}", flush=True)
    return results


def fdr_study(config):
    mc = config["monte_carlo"]
    families, m = mc["fdr_families_per_scenario"], mc["fdr_family_size"]
    rows, max_error = [], 0.
    rng = np.random.default_rng(mc["seed"] + 928)
    for dependence in ("independent", "positive_shared_factor", "signed_shared_factor"):
        for nonnull_fraction in (0., .2):
            z = rng.normal(size=(families, m))
            if dependence != "independent":
                load = np.ones(m) if dependence == "positive_shared_factor" else np.where(np.arange(m) % 2, 1, -1)
                z = np.sqrt(.5) * z + np.sqrt(.5) * rng.normal(size=(families, 1)) * load
            truth = np.zeros(m, dtype=bool)
            truth[:int(m * nonnull_fraction)] = True
            z[:, truth] += 3.
            p = 2 * norm.sf(np.abs(z))
            for method in ("BH", "BY"):
                expected = false_discovery_control(p, method=method.lower(), axis=1)
                actual = np.stack([adjust_fdr(row, method=method, q=config["multiplicity"]["q"])["adjusted_p"] for row in p])
                error = float(np.max(np.abs(actual - expected)))
                max_error = max(error, max_error)
                np.testing.assert_allclose(actual, expected, atol=1e-14, rtol=1e-12)
                rejected = actual <= config["multiplicity"]["q"]
                n = rejected.sum(axis=1)
                false = rejected[:, ~truth].sum(axis=1)
                fdp = false / np.maximum(n, 1)
                se = float(np.std(fdp, ddof=1) / np.sqrt(families))
                interval = wilson_interval(int((n > 0).sum()), families) if not truth.any() else [max(0., float(fdp.mean() - 1.96 * se)), min(1., float(fdp.mean() + 1.96 * se))]
                power = float((rejected[:, truth].sum(axis=1) / truth.sum()).mean()) if truth.any() else None
                rows.append({"dependence": dependence, "nonnull_fraction": nonnull_fraction, "method": method,
                             "families": families, "family_size": m, "fdr": float(fdp.mean()), "fdr_mc95": interval,
                             "mean_rejections": float(n.mean()), "power": power,
                             "fdr_interval_method": "Wilson all-null Bernoulli event" if not truth.any() else "normal Monte Carlo mean-FDP across independent families",
                             "reference_max_absolute_difference": error})
    return {"rows": rows, "max_reference_absolute_difference": max_error,
            "valid_marginal_p_values": "two-sided Gaussian tails with exact N(0,1) null marginals",
            "interpretation": "synthetic arithmetic/assumption checks; no guarantee for invalid NASA candidate p-values"}


def gate_results(records, config):
    screen = config["monte_carlo"]["research_screen"]
    chosen = [row for row in records if row["model"] == "annual_ar1" and row["true_slope_per_year"] == 0
              and row["n_years"] == 24 and row["block_length_years"] == config["block_length_candidate_years"]]
    checks = [{"scenario": row["scenario"],
               "false_positive_upper_mc95": row["rejection_mc95"][1],
               "coverage_lower_mc95": row["coverage_mc95"][0],
               "passes_research_screen": row["rejection_mc95"][1] <= screen["max_false_positive_rate_upper_wilson"]
               and row["coverage_mc95"][0] >= screen["min_coverage_lower_wilson"]} for row in chosen]
    return {"checks": checks, "passes_research_screen": bool(checks) and all(row["passes_research_screen"] for row in checks),
            "application_release": False, "note": "Even a passed minimum research screen is not proof of nominal coverage or owner approval"}


def nasa_diagnostics(config):
    rows = []
    for index, case in enumerate(load_cases()):
        if case["experimental"]:
            rows.append({"case": case["key"], "status": "inference_withheld", "reason": "Standard 95% remains experimental with changing spatial support; incomplete cell-years stay missing"})
            continue
        ds = load_prepared(case)
        for block in (3, 4, 6):
            outcome = annual_inference(ds.regional_annual.values, ds.year.values, block_length=block,
                                       replicates=config["diagnostic_replicates"], confidence=config["confidence_level"],
                                       seed=config["monte_carlo"]["seed"] + index,
                                       min_points=config["minimum_annual_observations"])
            rows.append({"case": case["key"], "policy": case["policy"], "role": "primary_strict_family" if case["policy"] == "strict_100" else "separate_policy_sensitivity",
                         "units": ds.regional_annual.attrs["units"] + " per year", **outcome,
                         "scientific_status": "diagnostic_only; individual p-value calibration not released"})
    return rows


def plots(records, fdr):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.7), constrained_layout=True)
    for block in (1, 3, 4, 6):
        chosen = sorted([r for r in records if r["model"] == "annual_ar1" and r["true_slope_per_year"] == 0 and r["n_years"] == 24 and r["block_length_years"] == block], key=lambda r:r["phi"])
        axes[0].plot([r["phi"] for r in chosen], [r["rejection_rate"] for r in chosen], "o-", label=f"Block {block} years")
        axes[1].plot([r["phi"] for r in chosen], [r["coverage"] for r in chosen], "o-", label=f"Block {block} years")
    axes[0].axhline(.05, linestyle="--", color="black", label="Nominal 5%")
    axes[1].axhline(.95, linestyle="--", color="black", label="Nominal 95%")
    axes[0].set(ylabel="False-positive rate", title="No-trend AR(1), 24 annual observations")
    axes[1].set(ylabel="Empirical interval coverage", title="95% candidate basic-bootstrap intervals")
    for ax in axes:
        ax.set_xlabel("True annual AR(1) coefficient")
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.savefig(OUT / "annual_calibration.png", dpi=150)
    plt.close(fig)
    fig, ax = plt.subplots(figsize=(11, 4.5), constrained_layout=True)
    labels = [r["dependence"].replace("_", " ") + (" / mixed" if r["nonnull_fraction"] else " / null") for r in fdr["rows"] if r["method"] == "BH"]
    x = np.arange(len(labels))
    for method, offset in (("BH", -.18), ("BY", .18)):
        rows = [r for r in fdr["rows"] if r["method"] == method]
        ax.bar(x + offset, [r["fdr"] for r in rows], width=.34, label=method)
    ax.axhline(.05, color="black", linestyle="--", label="q=0.05")
    ax.set(xticks=x, xticklabels=labels, ylabel="Mean false discovery proportion", title="Valid synthetic p-values only; not NASA inference release")
    ax.tick_params(axis="x", rotation=20)
    ax.legend()
    fig.savefig(OUT / "synthetic_fdr.png", dpi=150)
    plt.close(fig)


def main():
    start = time.perf_counter()
    config = json.loads((ROOT / "packages/science/config/inference_policy.json").read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    before = preserved_inputs()
    identity = {"policy_sha256": policy_hash(config), "implementation_sha256": sha(ROOT / "packages/science/src/inference.py"),
                "study_script_sha256": sha(Path(__file__))}
    write_json(OUT / "study_protocol.json", {"identity": identity, "config": config, "preserved_sha256": before})
    records = monte_carlo(config)
    fdr = fdr_study(config)
    gate = gate_results(records, config)
    diagnostics = nasa_diagnostics(config)
    plots(records, fdr)
    assert before == preserved_inputs(), "Earlier preparation/trend artifacts changed"
    result = {"revision": config["revision"], "identity": identity, "config": config,
              "candidate_calibration": gate, "simulation_records": records,
              "monte_carlo_total_records": sum(r["replications"] for r in records),
              "multiplicity_study": fdr, "nasa_candidate_diagnostics": diagnostics,
              "application_release": False, "real_cell_inference": "withheld pending marginal calibration",
              "real_multiplicity": "withheld; adjustment cannot repair miscalibrated marginal p-values",
              "default_changed": False, "software_versions": {p: importlib.metadata.version(p) for p in ("numpy", "scipy", "xarray")},
              "preserved_file_count": len(before), "all_earlier_sha256_unchanged": True, "preserved_sha256": before,
              "elapsed_seconds": time.perf_counter() - start}
    write_json(REPORTS / "PHASE_4_STUDY.json", result)
    print(f"Study complete: {len(records)} scenarios, {result['monte_carlo_total_records']} simulated annual records; "
          f"research screen={gate['passes_research_screen']}; earlier files preserved={len(before)}", flush=True)


if __name__ == "__main__":
    main()
