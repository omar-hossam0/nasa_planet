"""Read-only checks of Phase 3 outputs plus the full scientific test suite."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.trend_estimation import annual_elapsed_years, trend_series
from review_sahel_ndvi import sha, write_json
from run_science_trends import FORBIDDEN, assert_no_inference, load_cases, load_prepared, stage2_snapshot


def main():
    results = json.loads((ROOT / "packages/science/phase_reports/PHASE_3_RESULTS.json").read_text())
    validation = json.loads((ROOT / "packages/science/phase_reports/PHASE_3_VALIDATION.json").read_text())
    assert stage2_snapshot() == validation["stage2_sha256"]
    for path, expected in results["code_sha256"].items():
        assert sha(ROOT / path) == expected, path
    assert_no_inference(results)
    grid_checks = []
    inputs = {case["key"]: case for case in load_cases()}
    for case in results["cases"]:
        assert sha(ROOT / case["grid_artifact"]) == case["grid_sha256"]
        prepared = load_prepared(inputs[case["case"]])
        with xr.open_dataset(ROOT / case["grid_artifact"]) as ds:
            assert not FORBIDDEN.intersection(ds.data_vars)
            eligible = ds.eligible_support.values.astype(bool)
            for frequency in ("monthly", "annual"):
                slope, count, ok = (ds[f"{frequency}_{name}"].values for name in ("slope", "n_valid", "computable"))
                field = "cell_monthly" if frequency == "monthly" else "cell_annual"
                np.testing.assert_array_equal(count, np.isfinite(prepared[field].values).sum(axis=0))
                np.testing.assert_array_equal(np.isfinite(slope), ok.astype(bool))
                np.testing.assert_array_equal(ok.astype(bool), count >= 3)
                assert not np.isfinite(slope[~eligible]).any()
                assert int(np.isfinite(slope).sum()) == case["grid"][frequency]["computable_cell_slopes"]
        grid_checks.append(case["case"])
    suite = unittest.defaultTestLoader.discover(str(ROOT / "packages/science/tests"))
    run = unittest.TextTestRunner(verbosity=1).run(suite)
    # Capture the two historical invariants in the repaired library without
    # invoking the legacy wrapper, which would also compute forbidden inference.
    time = np.arange(24)
    annual = trend_series(time.astype(float), annual_elapsed_years(2001 + time))
    from src.trend_estimation import sen_slopes
    short_values = np.arange(48, dtype=float) / 12
    region = trend_series(short_values, np.arange(48) / 12, min_points=60)
    grid = sen_slopes(short_values[:, None, None], np.arange(48) / 12, min_points=60)
    report = {"tests_run": run.testsRun, "failures": len(run.failures), "errors": len(run.errors),
              "skipped": len(run.skipped), "passed": run.wasSuccessful(),
              "annual_factor_of_twelve_regression": {"truth_per_year": 1., "actual_per_year": annual["slope_per_year"],
                                                     "passed": annual["slope_per_year"] == 1.},
              "explicit_60_point_guard_on_48_samples": {"regional_status": region["status"],
                                                       "computable_grid_cells": int(grid["computable"].sum()),
                                                       "passed": region["status"] == "insufficient_data" and not grid["computable"].any()},
              "all_case_grid_masks_counts_and_hashes_passed": grid_checks,
              "all_grid_valid_counts_match_original_prepared_values": True,
              "stage2_preserved_file_count": validation["stage2_preserved_file_count"],
              "stage2_hashes_unchanged": True, "inference_fields_absent": True}
    write_json(ROOT / "packages/science/phase_reports/PHASE_3_TESTS.json", report)
    if not report["passed"] or not report["annual_factor_of_twelve_regression"]["passed"] or not report["explicit_60_point_guard_on_48_samples"]["passed"]:
        raise SystemExit(1)
    print(f"PASS: {run.testsRun} tests; {len(grid_checks)} grid outputs; Stage 2 hashes unchanged; inference fields absent.")


if __name__ == "__main__":
    main()
