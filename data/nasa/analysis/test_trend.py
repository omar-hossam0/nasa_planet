"""Member 2 test suite: the statistical pipeline must earn its claims.

Run:  python test_trend.py
Exit code 0 means every check passed. Each test states what it proves and
what it does NOT prove.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import trend as tr  # noqa: E402

CFG = tr.load_config()
MONTHS = [f"{y}-{m:02d}" for y in range(2001, 2025) for m in range(1, 13)]
N = len(MONTHS)
YEARS = np.arange(N) / 12.0
RESULTS = []


def check(name: str, condition: bool, detail: str, proves: str) -> None:
    RESULTS.append((name, bool(condition), detail))
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}: {detail}")
    print(f"        proves: {proves}")


def test_known_slope() -> None:
    rng = np.random.default_rng(11)
    truth = 0.5
    x = truth * YEARS + rng.normal(0, 0.2, N)
    res = tr.trend_series(x, MONTHS, CFG)
    err = abs(res["slope"] - truth)
    check("known_slope", err < 0.05 and res["state"] == "succeeded",
          f"recovered {res['slope']:.4f} vs truth {truth} (err {err:.4f}), "
          f"p={res['p_value']:.2g}",
          "the estimator recovers a known linear slope within tolerance")


def test_no_trend() -> None:
    rng = np.random.default_rng(22)
    x = rng.normal(0, 1, N)
    res = tr.trend_series(x, MONTHS, CFG)
    check("no_trend_null", res["p_value"] > 0.05 and abs(res["slope"]) < 0.05,
          f"slope={res['slope']:.4f}, p={res['p_value']:.3f}",
          "a white-noise series is not labelled a trend")


def test_seasonality() -> None:
    rng = np.random.default_rng(33)
    seasonal = 10 * np.sin(2 * np.pi * (np.arange(N) % 12) / 12)
    x_null = seasonal + rng.normal(0, 0.5, N)
    res_null = tr.trend_series(x_null, MONTHS, CFG)
    x_trend = seasonal + 0.1 * YEARS + rng.normal(0, 0.5, N)
    res_trend = tr.trend_series(x_trend, MONTHS, CFG)
    ok = (res_null["p_value"] > 0.05 and abs(res_null["slope"]) < 0.02 and
          abs(res_trend["slope"] - 0.1) < 0.02 and res_trend["p_value"] < 0.05)
    check("seasonality", ok,
          f"null: slope={res_null['slope']:.4f} p={res_null['p_value']:.3f}; "
          f"trend: slope={res_trend['slope']:.4f} p={res_trend['p_value']:.2g}",
          "a strong annual cycle alone is not a trend, and it does not hide "
          "a real trend of 0.1/year")


def test_serial_dependence() -> None:
    """AR(1) null: the correction must inflate variance and reduce false positives."""
    factors = []
    uncorrected_hits = 0
    corrected_hits = 0
    trials = 40
    for seed in range(trials):
        rng = np.random.default_rng(1000 + seed)
        e = rng.normal(0, 1, N)
        x = np.zeros(N)
        for i in range(1, N):
            x[i] = 0.6 * x[i - 1] + e[i]
        res = tr.trend_series(x, MONTHS, CFG, with_ci=False)
        corr = res.get("dependence_correction")
        if corr:
            factors.append(corr["factor"])
        if res["p_value_uncorrected"] < 0.05:
            uncorrected_hits += 1
        if res["p_value"] < 0.05:
            corrected_hits += 1
    ok = (len(factors) > trials * 0.8 and min(factors) >= 1.0 and
          corrected_hits <= uncorrected_hits)
    check("serial_dependence", ok,
          f"factors>1 in {len(factors)}/{trials}, "
          f"false positives uncorrected={uncorrected_hits}/{trials} "
          f"corrected={corrected_hits}/{trials}",
          "Hamed-Rao correction is applied and does not increase false "
          "positives on AR(1) null series; it does not prove correctness for "
          "every dependence structure")


def test_missingness() -> None:
    rng = np.random.default_rng(44)
    truth = 0.3
    base = truth * YEARS + rng.normal(0, 0.3, N)
    # 15% missing: above the 80% coverage rule, slope must still be recovered
    x_ok = base.copy()
    mask_ok = rng.random(N) < 0.15
    x_ok[mask_ok] = np.nan
    res_ok = tr.trend_series(x_ok, MONTHS, CFG)
    # 30% missing: below the coverage rule, must return insufficient_data
    x_bad = base.copy()
    mask_bad = rng.random(N) < 0.30
    x_bad[mask_bad] = np.nan
    res_bad = tr.trend_series(x_bad, MONTHS, CFG)
    ok = (res_ok["state"] == "succeeded" and
          abs(res_ok["slope"] - truth) < 0.06 and
          res_ok["n_valid_months"] == int((~mask_ok).sum()) and
          res_bad["state"] == "insufficient_data")
    check("missingness", ok,
          f"15% missing: slope={res_ok['slope']:.4f} vs {truth}, valid="
          f"{res_ok['n_valid_months']}/{N}; 30% missing: "
          f"state={res_bad['state']}",
          "missing values are skipped and counted, and the frozen coverage "
          "threshold is enforced instead of silently estimating anyway")


def test_insufficient_data() -> None:
    rng = np.random.default_rng(55)
    x = rng.normal(0, 1, 24)
    res = tr.trend_series(x, MONTHS[:24], CFG)
    ok = (res["state"] == "insufficient_data" and res["slope"] is None and
          res["p_value"] is None)
    check("insufficient_data", ok, f"state={res['state']}",
          "short series return an explicit insufficient_data state, never a "
          "silent number")


def test_fdr() -> None:
    """BH controls the FDR in expectation, so the test averages realisations.

    A single realisation may exceed q; the property under test is the mean
    false discovery proportion across independent families, plus power.
    """
    m = 200
    n_true = 20
    trials = 200
    fdps = []
    power = []
    for seed in range(trials):
        rng = np.random.default_rng(7000 + seed)
        p = rng.random(m)
        true_alt = np.zeros(m, dtype=bool)
        idx = rng.choice(m, n_true, replace=False)
        p[idx] = rng.random(n_true) * 1e-4
        true_alt[idx] = True
        res = tr.benjamini_hochberg(p, q=0.10)
        rejected = res["reject"]
        false_disc = int((rejected & ~true_alt).sum())
        fdps.append(false_disc / max(int(rejected.sum()), 1))
        power.append(float(rejected[idx].mean()))
    mean_fdp = float(np.mean(fdps))
    mean_power = float(np.mean(power))
    ok = mean_fdp <= 0.10 and mean_power >= 0.9
    check("fdr_control", ok,
          f"{trials} families of m={m}: mean FDP={mean_fdp:.3f} (q=0.10), "
          f"mean power={mean_power:.3f}",
          "BH keeps the mean false discovery proportion at or below q with "
          "high power on this simulated family; it does not guarantee the "
          "same under real spatial dependence")


def test_spatial() -> None:
    import xarray as xr
    rng = np.random.default_rng(77)
    nlat, nlon = 10, 8
    truth = np.zeros((nlat, nlon))
    truth[:, :4] = 0.2
    data = (truth[None, :, :] * YEARS[:, None, None] +
            rng.normal(0, 0.2, (N, nlat, nlon)))
    ds = xr.Dataset(
        {"X": (("time", "lat", "lon"), data, {"units": "u"})},
        coords={"time": np.array([np.datetime64(m + "-01") for m in MONTHS]),
                "lat": np.arange(nlat, dtype="f8"),
                "lon": np.arange(nlon, dtype="f8")},
        attrs={"product": "SYNTHETIC"})
    res = tr.spatial_trend(ds, CFG)
    left = res["slope"][:, :4]
    right = res["slope"][:, 4:]
    ok = (abs(np.nanmedian(left) - 0.2) < 0.03 and
          abs(np.nanmedian(right)) < 0.03 and
          int(res["significant_fdr"][:, :4].sum()) >
          int(res["significant_fdr"][:, 4:].sum()))
    check("spatial_map", ok,
          f"trend half median={np.nanmedian(left):.3f}, null half "
          f"median={np.nanmedian(right):.3f}, FDR cells "
          f"{int(res['significant_fdr'][:, :4].sum())} vs "
          f"{int(res['significant_fdr'][:, 4:].sum())} of "
          f"{nlat*nlon}",
          "the per-cell map recovers planted slopes and FDR separates them "
          "from null cells")


def test_period_sensitivity() -> None:
    rng = np.random.default_rng(88)
    x = np.where(YEARS < 12, 0.15 * YEARS, 0.15 * 12 - 0.15 * (YEARS - 12))
    x = x + rng.normal(0, 0.1, N)
    res = tr.period_sensitivity(x, MONTHS, CFG)
    sa = res["sign_agreement"]
    ok = sa["n_windows"] >= 10 and sa["fraction_same_sign_as_full"] < 1.0
    check("period_sensitivity", ok,
          f"{sa['n_windows']} windows, {sa['positive']} positive / "
          f"{sa['negative']} negative, same-sign fraction="
          f"{sa['fraction_same_sign_as_full']}",
          "a series with a mid-record reversal shows mixed signs across the "
          "frozen window set; the fraction is descriptive, not a probability")


def main() -> int:
    for fn in (test_known_slope, test_no_trend, test_seasonality,
               test_serial_dependence, test_missingness,
               test_insufficient_data, test_fdr, test_spatial,
               test_period_sensitivity):
        fn()
    passed = sum(1 for _, ok, _ in RESULTS if ok)
    total = len(RESULTS)
    print(f"\n{passed}/{total} checks passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
