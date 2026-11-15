"""Member 2 external reference comparison.

Three independent checks:
1. Theil-Sen slope against scipy.stats.theilslopes (different codebase).
2. Mann-Kendall and seasonal Mann-Kendall against pyMannKendall.
3. MERRA-2 Cairo grid cell trend against the NASA POWER Cairo point series
   already shipped in this repository.

Writes reference_comparison.json. Nothing here replaces the test suite: it
checks agreement with independent implementations and one independent data
path, and records exactly where they are not expected to agree.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats as sstats
import pymannkendall as pmk

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import trend as tr  # noqa: E402
import preprocess as pp  # noqa: E402

CFG = tr.load_config()
MONTHS = [f"{y}-{m:02d}" for y in range(2001, 2025) for m in range(1, 13)]


def check_theilsen() -> dict:
    """scipy's Theil-Sen must give the same slope as ours."""
    out = {"checks": []}
    rng = np.random.default_rng(5)
    cases = {
        "synthetic_linear": 0.5 * (np.arange(288) / 12.0) +
        rng.normal(0, 0.3, 288),
    }
    with pp.load_cube("M2TMNXSLV", "nile_corridor") as ds:
        clean = pp.apply_qa(ds, "M2TMNXSLV", CFG["qa"]["mode"])
        rs = tr.region_series(clean, CFG)
        anom = tr.anomalies(rs["series"])["anomalies"]
        cases["merra2_nile_region_anomalies"] = anom
    for name, x in cases.items():
        t = np.arange(len(x), dtype="f8") / 12.0
        ours = tr.sen_slope(x, MONTHS[:len(x)])["slope"]
        ref = sstats.theilslopes(x, t).slope
        out["checks"].append({
            "case": name,
            "ours": ours,
            "scipy": float(ref),
            "abs_diff": abs(ours - ref),
            "agree": bool(abs(ours - ref) < 1e-9),
        })
    out["note"] = ("scipy also returns an intercept; that intercept is not a "
                   "confidence interval and is not used anywhere in this "
                   "project.")
    return out


def check_mann_kendall() -> dict:
    """pyMannKendall must reproduce our MK and seasonal MK p-values."""
    out = {"checks": []}
    rng = np.random.default_rng(6)
    series = {
        "synthetic_ar_trend": (0.2 * np.arange(288) / 12.0 +
                               rng.normal(0, 1, 288)),
    }
    with pp.load_cube("M2TMNXSLV", "sahel_comparison") as ds:
        clean = pp.apply_qa(ds, "M2TMNXSLV", CFG["qa"]["mode"])
        rs = tr.region_series(clean, CFG)
        series["merra2_sahel_region"] = rs["series"]
    for name, x in series.items():
        ours = tr.mann_kendall(x)
        ref = pmk.original_test(x)
        ours_s = tr.seasonal_mann_kendall(x, 12)
        ref_s = pmk.seasonal_test(x, period=12)
        out["checks"].append({
            "case": name,
            "original": {
                "ours_S": ours["S"], "pmk_S": float(ref.s),
                "ours_p": ours["p"], "pmk_p": float(ref.p),
                "p_abs_diff": abs(ours["p"] - float(ref.p)),
                "S_equal": bool(abs(ours["S"] - float(ref.s)) < 1e-9),
            },
            "seasonal": {
                "ours_p": ours_s["p"], "pmk_p": float(ref_s.p),
                "p_abs_diff": abs(ours_s["p"] - float(ref_s.p)),
            },
        })
    return out


def check_power_vs_merra() -> dict:
    """Independent data path: NASA POWER Cairo point vs MERRA-2 Cairo cell."""
    csv_path = HERE.parent / "rag" / "cairo_temperature_monthly.csv"
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    power_months = [r["month"] for r in rows]
    power_c = np.array([float(r["T2M"]) for r in rows], dtype="f8")
    with pp.load_cube("M2TMNXSLV", "nile_corridor") as ds:
        cell = ds["T2M"].sel(lat=30.0, lon=31.25, method="nearest")
        cell_months = [str(t)[:7] for t in ds["time"].values]
        cell_k = cell.values.astype("f8")
    # align on the same months
    common = [m for m in cell_months if m in set(power_months)]
    idx_cell = [cell_months.index(m) for m in common]
    idx_power = [power_months.index(m) for m in common]
    cell_c = cell_k[idx_cell] - 273.15
    power_aligned = power_c[idx_power]
    res_cell = tr.trend_series(cell_c, common, CFG)
    res_power = tr.trend_series(power_aligned, common, CFG)
    diff = res_cell["slope"] - res_power["slope"]
    return {
        "merra2_cell": {
            "lat": float(cell.lat), "lon": float(cell.lon),
            "slope_C_per_year": res_cell["slope"],
            "p_value": res_cell["p_value"],
            "ci": [res_cell["ci_low"], res_cell["ci_high"]],
        },
        "power_point": {
            "slope_C_per_year": res_power["slope"],
            "p_value": res_power["p_value"],
            "ci": [res_power["ci_low"], res_power["ci_high"]],
        },
        "difference_C_per_year": float(diff),
        "months_compared": len(common),
        "reconciliation": [
            "Same period, same months, same method and same QA policy.",
            "POWER is a point request for the containing grid cell; it is not "
            "a station observation and not a city average.",
            "MERRA-2 cube value is the 0.5 x 0.625 deg cell centre nearest "
            "30.0N, 31.25E; POWER may use a different MERRA-2 vertical/level "
            "and bias-correction configuration.",
            "Agreement is expected in sign and order of magnitude, not to the "
            "third decimal.",
        ],
    }


def main() -> int:
    out = {
        "generated": "2026-11-14",
        "method_revision": CFG["method_revision"],
        "theilsen_vs_scipy": check_theilsen(),
        "mannkendall_vs_pymannkendall": check_mann_kendall(),
        "power_vs_merra2": check_power_vs_merra(),
    }
    path = HERE / "reference_comparison.json"
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    ok = all(c["agree"] for c in out["theilsen_vs_scipy"]["checks"])
    ok &= all(c["original"]["S_equal"] and c["original"]["p_abs_diff"] < 1e-9
              and c["seasonal"]["p_abs_diff"] < 1e-6
              for c in out["mannkendall_vs_pymannkendall"]["checks"])
    print("\nlibrary agreement:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
