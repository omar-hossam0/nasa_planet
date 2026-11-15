"""Reproduce two Phase 0 review findings without checking out another branch.

Only the three named Python/config files are copied to a temporary directory.
No source measurements are read, and no method configuration is changed.
Exit 1 indicates that at least one expected scientific invariant failed.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import xarray as xr

REVIEWED_REVISION = "486fe73551b3239bab172d26fe94979402c81e4e"


def probe(ref: str, repository: Path) -> dict:
    revision = subprocess.check_output(
        ["git", "rev-parse", "--verify", f"{ref}^{{commit}}"],
        cwd=repository, text=True).strip()
    with tempfile.TemporaryDirectory(prefix="nasa-statistics-audit-") as temp:
        snapshot = Path(temp)
        for name in ("preprocess.py", "analysis/trend.py", "analysis/method_config.json"):
            output = snapshot / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(subprocess.check_output(
                ["git", "show", f"{revision}:data/nasa/{name}"], cwd=repository))
        sys.path.insert(0, str(snapshot))
        previous_preprocess = sys.modules.pop("preprocess", None)
        try:
            spec = importlib.util.spec_from_file_location(
                "audited_trend", snapshot / "analysis/trend.py")
            trend = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(trend)
            config = trend.load_config()
            months = [f"{year}-{month:02d}" for year in range(2001, 2025)
                      for month in range(1, 13)]
            values = np.arange(len(months)) / 12
            annual = trend.trend_series(values, months, config,
                                        basis="annual", with_ci=False)
            short_months = months[:48]
            regional = trend.trend_series(values[:48], short_months, config, with_ci=False)
            cube = xr.Dataset(
                {"X": (("time", "lat", "lon"), values[:48, None, None])},
                coords={"time": np.array([np.datetime64(m + "-01") for m in short_months]),
                        "lat": [25.0], "lon": [30.0]})
            spatial = trend.spatial_trend(cube, config)
        finally:
            sys.path.remove(str(snapshot))
            sys.modules.pop("preprocess", None)
            if previous_preprocess is not None:
                sys.modules["preprocess"] = previous_preprocess
    return {
        "source_revision": revision,
        "annual_time_basis": {
            "synthetic_truth_per_year": 1.0,
            "actual_slope": annual["slope"], "actual_state": annual["state"],
            "passed": bool(np.isclose(annual["slope"], 1.0)),
        },
        "minimum_months_parity": {
            "configured_min_months": config["minimum_series"]["min_months"],
            "supplied_months": 48, "regional_state": regional["state"],
            "spatial_tests_admitted": spatial["fdr"]["m_tested"],
            "passed": regional["state"] == "insufficient_data" and spatial["fdr"]["m_tested"] == 0,
        },
        "scope": "Synthetic read-only regression probes against the other branch; "
                 "not real climate results and not a full method validation.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default=REVIEWED_REVISION)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = probe(args.ref, Path(__file__).resolve().parents[1])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if all(result[key]["passed"] for key in
                    ("annual_time_basis", "minimum_months_parity")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
