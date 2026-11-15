"""Round-trip checks for generated Stage 2 artifacts, separate from inference."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.preprocessing import load_policy, policy_hash
from prepare_science_inputs import file_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "packages/science/phase_reports/PHASE_2_COVERAGE.json")
    parser.add_argument("--output", type=Path, default=ROOT / "packages/science/phase_reports/PHASE_2_VALIDATION.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    policy = load_policy()
    if manifest["policy_sha256"] != policy_hash(policy):
        raise ValueError("Prepared artifact policy differs from the current default")
    baseline = json.loads((ROOT / "packages/science/phase_reports/input_audit_current.json").read_text(encoding="utf-8"))
    source_hashes = {entry["cube_file"]: entry["sha256"] for entry in baseline["entries"]}
    checks = []
    for entry in manifest["entries"]:
        path = ROOT / entry["artifact"]
        source = ROOT / entry["source_cube_file"]
        assert file_hash(path) == entry["artifact_sha256"], "Prepared artifact hash mismatch"
        assert file_hash(source) == source_hashes[entry["source_cube_file"]] == entry["source_cube_sha256"], "Source bytes changed"
        with xr.open_dataset(path) as ds:
            assert dict(ds.sizes) == {"time": 288, "lat": entry["selected_grid"]["lat_count"],
                                      "lon": entry["selected_grid"]["lon_count"], "year": 24}
            np.testing.assert_array_equal(ds.year, np.arange(2001, 2025))
            assert ds.attrs["policy_sha256"] == manifest["policy_sha256"]
            for field in ("fixed_support", "normalized_support_weight", "qa_valid_fraction_by_cell", "qa_valid_area_fraction_by_month", "qa_accepted"):
                assert ds[field].attrs["units"] == "1", f"Dimensionless field has incorrect units: {field}"
            assert ds.native_cell_solid_angle.attrs["units"] == "sr"
            support = ds.fixed_support.values.astype(bool)
            assert int(support.sum()) == entry["eligible_fixed_support_cells"]
            np.testing.assert_array_equal(np.isfinite(ds.cell_monthly).all("time"), support)
            assert bool(ds.cell_monthly.where(~ds.fixed_support.astype(bool)).isnull().all())
            assert ds.attrs["inference_status"] == "not_computed"
            assert not {"slope", "p_value", "confidence_interval", "significant_fdr"}.intersection(ds.data_vars)
            if support.any():
                assert bool(np.isfinite(ds.regional_monthly).all())
                np.testing.assert_allclose(ds.normalized_support_weight.sum(), 1.0)
                np.testing.assert_allclose(ds.regional_monthly_anomaly.groupby("time.month").mean(), 0.0, atol=1e-10)
                assert int(ds.regional_annual.notnull().sum()) == 24
                first = ds.cell_monthly.isel(time=0).values
                w = ds.native_cell_solid_angle.values
                expected = np.sum(first[support] * w[support]) / np.sum(w[support])
                np.testing.assert_allclose(ds.regional_monthly.values[0], expected)
        checks.append({"variable_id": entry["variable_id"], "region_id": entry["region_id"],
                       "result": "PASS", "source_hash_unchanged": True,
                       "round_trip_months": 288, "round_trip_years": 24})
    if len(checks) != 12:
        raise ValueError("Expected all twelve default-policy artifacts")
    result = {"purpose": "prepared artifact verification, not statistical method validation",
              "policy_sha256": manifest["policy_sha256"], "passed": len(checks), "total": 12,
              "checks": checks}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"{len(checks)}/12 prepared artifacts validated; all source hashes unchanged.")


if __name__ == "__main__":
    main()
