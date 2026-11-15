"""Independent Phase 4 arithmetic/reference checks and classical IID benchmark."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import numpy as np
from scipy.stats import kendalltau, theilslopes

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.inference import wilson_interval
from src.preprocessing import policy_hash
from src.trend_estimation import trend_series
from review_sahel_ndvi import sha, write_json
from run_science_inference_study import ar1, preserved_inputs


def iid_reference_benchmarks(config):
    """Classical IID methods are benchmarks, never dependence corrections.

    Reuses the exact seeded null records from the study. This post-study
    benchmark diagnoses whether poor coverage is specific to the candidate;
    it does not replace its prespecified acceptance criteria or select a method.
    """
    mc, rows = config["monte_carlo"], []
    max_slope_error = 0.
    for n in mc["null_lengths"]:
        for phi in mc["ar1_phi"]:
            rng = np.random.default_rng(np.random.SeedSequence([mc["seed"], n, int(phi * 100), 0]))
            series = ar1(rng, mc["replications_per_scenario"], n, phi)
            covered, rejected = 0, 0
            widths = []
            for y in series:
                ref = theilslopes(y, np.arange(n), alpha=config["confidence_level"])
                slope = trend_series(y, np.arange(n))["slope_per_year"]
                max_slope_error = max(max_slope_error, abs(ref.slope - slope))
                covered += ref.low_slope <= 0 <= ref.high_slope
                rejected += kendalltau(np.arange(n), y, method="exact").pvalue <= config["alpha"]
                widths.append(ref.high_slope - ref.low_slope)
            count = len(series)
            rows.append({"n_years": n, "phi": phi, "replications": count,
                         "classical_iid_sen_coverage": float(covered / count),
                         "coverage_mc95": wilson_interval(int(covered), count),
                         "classical_iid_kendall_false_positive_rate": float(rejected / count),
                         "false_positive_mc95": wilson_interval(int(rejected), count),
                         "mean_interval_width": float(np.mean(widths)),
                         "assumptions": "independent observations; invalid as a dependence correction when phi is nonzero"})
    return {"rows": rows, "slope_reference_max_absolute_difference": float(max_slope_error),
            "role": "post-study numerical/interpretation benchmark, not a replacement candidate or gate"}


def main():
    study = json.loads((ROOT / "packages/science/phase_reports/PHASE_4_STUDY.json").read_text())
    assert study["config"] == json.loads((ROOT / "packages/science/config/inference_policy.json").read_text())
    assert study["identity"]["policy_sha256"] == policy_hash(study["config"])
    assert study["identity"]["implementation_sha256"] == sha(ROOT / "packages/science/src/inference.py")
    assert study["identity"]["study_script_sha256"] == sha(ROOT / "tools/run_science_inference_study.py")
    assert preserved_inputs() == study["preserved_sha256"]
    assert len(study["simulation_records"]) == 48
    assert study["monte_carlo_total_records"] == 24_000
    for row in study["simulation_records"]:
        assert row["replications"] == 500
        assert row["coverage"] == row["covered"] / row["replications"]
        assert row["rejection_rate"] == row["rejected"] / row["replications"]
        assert row["coverage_mc95"][0] <= row["coverage"] <= row["coverage_mc95"][1]
        assert row["rejection_mc95"][0] <= row["rejection_rate"] <= row["rejection_mc95"][1]
    assert not study["application_release"]
    assert study["default_changed"] is False
    withheld = [r for r in study["nasa_candidate_diagnostics"] if r["status"] == "inference_withheld"]
    assert len(withheld) == 1 and "standard_95" in withheld[0]["case"]
    candidates = [r for r in study["nasa_candidate_diagnostics"] if r["status"] == "candidate_diagnostic"]
    assert len(candidates) == 39  # 12 strict + separate standard sensitivity, 3 blocks.
    assert not any("significant" in r or "classification" in r for r in candidates)
    assert study["multiplicity_study"]["max_reference_absolute_difference"] <= 1e-12
    references = iid_reference_benchmarks(study["config"])
    assert references["slope_reference_max_absolute_difference"] <= 1e-12
    suite = unittest.defaultTestLoader.discover(str(ROOT / "packages/science/tests"))
    run = unittest.TextTestRunner(verbosity=1).run(suite)
    unique_series_groups = {(r["model"], tuple(r["record_seed_components"]), r["true_slope_per_year"])
                            for r in study["simulation_records"]}
    independent_noise_groups = {(r["model"], tuple(r["record_seed_components"]))
                                for r in study["simulation_records"]}
    assert len(unique_series_groups) == 14 and len(independent_noise_groups) == 11
    result = {"passed": run.wasSuccessful(), "tests_run": run.testsRun,
              "failures": len(run.failures), "errors": len(run.errors), "skipped": len(run.skipped),
              "simulation_accounting_verified": True, "prior_artifact_hashes_unchanged": True,
              "scenario_record_evaluations": study["monte_carlo_total_records"],
              "distinct_synthetic_input_series": len(unique_series_groups) * 500,
              "independent_noise_trajectories": len(independent_noise_groups) * 500,
              "paired_block_comparisons": "same records reused across block lengths; power signs also share noise",
              "prior_artifact_count": study["preserved_file_count"],
              "classical_iid_reference_benchmark": references,
              "candidate_research_screen_passes": study["candidate_calibration"]["passes_research_screen"],
              "software_checks_passed_does_not_imply_scientific_calibration": True,
              "application_release": False}
    write_json(ROOT / "packages/science/phase_reports/PHASE_4_VALIDATION.json", result)
    print(f"Software/reference checks: {run.testsRun} tests, pass={run.wasSuccessful()}. "
          f"Candidate calibration screen={result['candidate_research_screen_passes']}; application release remains disabled.")
    if not run.wasSuccessful():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
