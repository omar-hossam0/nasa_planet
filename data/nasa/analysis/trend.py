"""Role 02 (statistics) analysis library - Trend Detective.

One implementation for both the region evidence card and the spatial map, so
the map and the card can never disagree.

Statistical choices are frozen in method_config.json (method_revision).
Nothing here invents a confidence interval, and no p-value is described as a
probability that a trend is real.

Main entry points
-----------------
    trend_series(x, months, cfg)          -> evidence-card numbers for a series
    spatial_trend(cube, cfg)              -> per-cell slopes + FDR decision
    period_sensitivity(x, months, cfg)    -> "Spin It" window matrix
    evidence_card(product, window, cfg)   -> full result payload for M3/M4/M5/M6

References for the implemented methods
--------------------------------------
Mann (1945); Kendall (1975) - rank correlation test for trend.
Hirsch & Slack (1984)       - seasonal Mann-Kendall.
Hamed & Rao (1998)          - variance correction for serial dependence.
Theil (1950); Sen (1968)    - robust slope estimator.
Benjamini & Hochberg (1995) - false discovery rate control.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT.parent
sys.path.insert(0, str(DATA_DIR))

import preprocess as pp  # noqa: E402  (shared data access layer)

METHOD_REVISION = "m2-1.0.0"
CONFIG_PATH = ROOT / "method_config.json"


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

def load_config(path: Path | str = CONFIG_PATH) -> dict:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    if cfg.get("method_revision") != METHOD_REVISION:
        raise ValueError(
            f"method_config revision {cfg.get('method_revision')} does not "
            f"match library revision {METHOD_REVISION}")
    return cfg


# --------------------------------------------------------------------------
# Core statistics
# --------------------------------------------------------------------------

def _as_float_series(x) -> np.ndarray:
    a = np.asarray(x, dtype="f8").ravel()
    return a


def _tie_correction(values: np.ndarray) -> float:
    """Sum of t(t-1)(2t+5) over tie groups of the finite values."""
    v = values[np.isfinite(values)]
    if v.size < 2:
        return 0.0
    v = np.sort(v)
    _, counts = np.unique(v, return_counts=True)
    return float(np.sum(counts * (counts - 1) * (2 * counts + 5)))


def mann_kendall(x) -> dict:
    """Original (non-seasonal) Mann-Kendall test with tie correction.

    Returns S, Var(S), z and the two-sided p-value. NaN values are dropped
    before the test; the caller must enforce a minimum number of valid values.
    """
    v = _as_float_series(x)
    v = v[np.isfinite(v)]
    n = v.size
    if n < 3:
        return {"S": 0.0, "var": float("nan"), "z": float("nan"),
                "p": float("nan"), "n": n, "status": "insufficient_data"}
    # S = sum of signs of all later-minus-earlier pairs
    s = 0.0
    for i in range(n - 1):
        s += float(np.sum(np.sign(v[i + 1:] - v[i])))
    var = (n * (n - 1) * (2 * n + 5) - _tie_correction(v)) / 18.0
    if var <= 0:
        return {"S": s, "var": 0.0, "z": float("nan"), "p": float("nan"),
                "n": n, "status": "no_variance"}
    if s > 0:
        z = (s - 1) / math.sqrt(var)
    elif s < 0:
        z = (s + 1) / math.sqrt(var)
    else:
        z = 0.0
    p = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return {"S": s, "var": var, "z": z, "p": p, "n": n, "status": "ok"}


def seasonal_mann_kendall(x, period: int = 12) -> dict:
    """Seasonal Mann-Kendall (Hirsch & Slack 1984).

    The series is split into `period` seasons; S and Var(S) are summed across
    seasons. This is what keeps a strong annual cycle from being read as a
    trend.
    """
    v = _as_float_series(x)
    n = v.size
    if n < period * 3:
        return {"S": 0.0, "var": float("nan"), "z": float("nan"),
                "p": float("nan"), "n": n, "status": "insufficient_data"}
    s_total = 0.0
    var_total = 0.0
    used = 0
    for season in range(period):
        sub = v[season::period]
        r = mann_kendall(sub)
        if r["status"] != "ok":
            continue
        s_total += r["S"]
        var_total += r["var"]
        used += 1
    if var_total <= 0 or used < 3:
        return {"S": s_total, "var": var_total, "z": float("nan"),
                "p": float("nan"), "n": n, "status": "no_variance"}
    if s_total > 0:
        z = (s_total - 1) / math.sqrt(var_total)
    elif s_total < 0:
        z = (s_total + 1) / math.sqrt(var_total)
    else:
        z = 0.0
    p = 2.0 * (1.0 - _normal_cdf(abs(z)))
    return {"S": s_total, "var": var_total, "z": z, "p": p, "n": n,
            "seasons_used": used, "status": "ok"}


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def hamed_rao_factor(x, max_lag: int = 24, alpha: float = 0.05) -> dict:
    """Hamed & Rao (1998) variance-inflation factor n/n*.

    Only autocorrelations that are themselves significant are used, which is
    the recommended conservative form. Applied to the deseasonalised series so
    the annual cycle is not mistaken for serial dependence.
    """
    v = _as_float_series(x)
    v = v[np.isfinite(v)]
    n = v.size
    if n < 10:
        return {"factor": 1.0, "lags_used": [], "rhos": {}, "status":
                "insufficient_data"}
    lag_max = int(min(max_lag, n // 4))
    mean = v.mean()
    dev = v - mean
    denom = float(np.sum(dev ** 2))
    if denom <= 0:
        return {"factor": 1.0, "lags_used": [], "rhos": {},
                "status": "no_variance"}
    crit = 1.96 / math.sqrt(n)
    rhos = {}
    for lag in range(1, lag_max + 1):
        r = float(np.sum(dev[:-lag] * dev[lag:]) / denom)
        rhos[lag] = r
    used = [lag for lag, r in rhos.items() if abs(r) > crit]
    if not used:
        return {"factor": 1.0, "lags_used": [], "rhos": rhos,
                "status": "no_significant_autocorrelation"}
    total = 0.0
    for lag in used:
        total += (n - lag) * (n - lag - 1) * (n - lag - 2) * rhos[lag]
    factor = 1.0 + (2.0 / (n * (n - 1) * (n - 2))) * total
    factor = max(1.0, float(factor))
    return {"factor": factor, "lags_used": used, "rhos": rhos,
            "status": "corrected"}


def sen_slope(x, months=None) -> dict:
    """Theil-Sen slope in units per year (time axis in years)."""
    v = _as_float_series(x)
    n = v.size
    if months is None:
        t = np.arange(n, dtype="f8") / 12.0
    else:
        t = _time_in_years(months)
    mask = np.isfinite(v)
    v = v[mask]
    t = t[mask]
    if v.size < 3:
        return {"slope": float("nan"), "n": int(v.size),
                "status": "insufficient_data"}
    iu = np.triu_indices(v.size, 1)
    dt = t[iu[1]] - t[iu[0]]
    dy = v[iu[1]] - v[iu[0]]
    good = dt != 0
    slopes = dy[good] / dt[good]
    return {"slope": float(np.median(slopes)), "n": int(v.size),
            "status": "ok"}


def _time_in_years(months) -> np.ndarray:
    """Month labels ('YYYY-MM') to decimal years (month centre)."""
    out = []
    for m in months:
        y = int(str(m)[:4])
        mo = int(str(m)[5:7])
        out.append(y + (mo - 0.5) / 12.0)
    return np.asarray(out, dtype="f8")


def anomalies(x, period: int = 12) -> dict:
    """Remove the per-season climatology computed over the given series.

    Anomalies are what the slope is estimated on, so a strong annual cycle
    cannot leak into the slope. The baseline is reported, never hidden.
    """
    v = _as_float_series(x)
    n = v.size
    clim = np.full(period, np.nan)
    for s in range(period):
        sub = v[s::period]
        finite = sub[np.isfinite(sub)]
        if finite.size:
            clim[s] = float(finite.mean())
    anom = v.copy()
    for s in range(period):
        idx = np.arange(s, n, period)
        anom[idx] = v[idx] - clim[s]
    return {"anomalies": anom, "climatology": clim,
            "baseline": "seasonal mean over the analysed series"}


def block_bootstrap_ci(x, cfg: dict, months=None) -> dict:
    """Percentile CI for the Theil-Sen slope via block-residual bootstrap.

    Estimand: the Theil-Sen slope in units/year of the analysed series.
    Dependence: residuals are resampled in circular blocks so serial
    dependence and seasonality are preserved; block length is fixed in the
    config, not chosen after seeing the answer.
    """
    bs = cfg["bootstrap"]
    v = _as_float_series(x)
    n = v.size
    mask = np.isfinite(v)
    if mask.sum() < cfg["minimum_series"]["min_valid_months"]:
        return {"ci_low": None, "ci_high": None, "status":
                "insufficient_data"}
    t = (_time_in_years(months) if months is not None
         else np.arange(n, dtype="f8") / 12.0)
    base = sen_slope(v, months)
    slope = base["slope"]
    fitted = slope * (t - t[mask].mean()) + np.nanmean(v)
    resid = v - fitted
    # centre residuals on the finite ones so missing values do not bias them
    r_finite = resid[mask]
    r_finite = r_finite - np.mean(r_finite)
    rng = np.random.default_rng(bs["seed"])
    block = int(bs["block_length_months"])
    reps = int(bs["replicates"])
    idx_all = np.arange(n)
    slopes = np.empty(reps)
    n_blocks = int(math.ceil(n / block))
    for b in range(reps):
        starts = rng.integers(0, n, size=n_blocks)
        idx = np.concatenate([(starts[i] + np.arange(block)) % n
                              for i in range(n_blocks)])[:n]
        r = r_finite[idx % r_finite.size] if r_finite.size else np.zeros(n)
        synth = fitted + r
        synth[~mask] = np.nan
        slopes[b] = sen_slope(synth, months)["slope"]
    lo, hi = np.percentile(slopes, [100 * (1 - bs["confidence"]) / 2,
                                    100 * (1 + bs["confidence"]) / 2])
    return {
        "ci_low": float(lo), "ci_high": float(hi),
        "estimand": "Theil-Sen slope, units per year",
        "interval_method": "percentile block-residual bootstrap",
        "block_length_months": block, "replicates": reps,
        "seed": bs["seed"], "confidence": bs["confidence"],
        "status": "ok",
    }


def benjamini_hochberg(p_values, q: float = 0.10) -> dict:
    """BH step-up FDR control. Returns the decision mask and threshold."""
    p = np.asarray(p_values, dtype="f8")
    valid = np.isfinite(p)
    m = int(valid.sum())
    if m == 0:
        return {"reject": np.zeros(p.shape, dtype=bool), "m": 0,
                "threshold": None, "status": "no_valid_tests"}
    pv = p[valid]
    order = np.argsort(pv)
    ranked = pv[order]
    crit = q * (np.arange(1, m + 1) / m)
    below = ranked <= crit
    if not below.any():
        return {"reject": np.zeros(p.shape, dtype=bool), "m": m,
                "threshold": float(q / m), "status": "none_significant"}
    k = int(np.max(np.nonzero(below)[0]))
    thresh = float(ranked[k])
    reject_valid = pv <= thresh
    reject = np.zeros(p.shape, dtype=bool)
    reject[valid] = reject_valid
    return {"reject": reject, "m": m, "threshold": thresh,
            "status": "ok", "q": q}


# --------------------------------------------------------------------------
# Series-level trend
# --------------------------------------------------------------------------

def trend_series(x, months, cfg: dict, basis: str | None = None,
                 with_ci: bool = True) -> dict:
    """Full trend result for one series (region aggregate or a single cell).

    basis:
      'seasonal' (default) - seasonal Mann-Kendall on the monthly series,
                             slope from Theil-Sen on anomalies.
      'annual'             - Mann-Kendall on annual means.
    """
    basis = basis or cfg["inference"]["basis"]
    v = _as_float_series(x)
    n = v.size
    n_valid = int(np.isfinite(v).sum())
    minv = cfg["minimum_series"]
    out = {
        "n_months": n,
        "n_valid_months": n_valid,
        "basis": basis,
        "method_revision": cfg["method_revision"],
    }
    if n < minv["min_months"] or n_valid < minv["min_valid_months"] or \
            n_valid / n < minv["min_valid_fraction"]:
        out.update({
            "state": "insufficient_data",
            "reason": (f"needs >= {minv['min_months']} months and "
                       f">= {minv['min_valid_fraction']:.0%} valid values"),
            "slope": None, "p_value": None,
            "ci_low": None, "ci_high": None,
        })
        return out

    an = anomalies(v, period=cfg["inference"]["season_period"])
    if basis == "annual":
        years = sorted({str(m)[:4] for m in months})
        annual = []
        for y in years:
            sel = [i for i, m in enumerate(months) if str(m)[:4] == y]
            vals = v[sel]
            vals = vals[np.isfinite(vals)]
            annual.append(float(vals.mean()) if vals.size >= 6 else np.nan)
        annual = np.asarray(annual, dtype="f8")
        test = mann_kendall(annual)
        slope = sen_slope(annual, None)
        n_eff = len(annual)
    else:
        test = seasonal_mann_kendall(v, period=cfg["inference"]["season_period"])
        slope = sen_slope(an["anomalies"], months)
        n_eff = n

    p_raw = test["p"]
    p_adj = p_raw
    correction = None
    if cfg["dependence"]["apply_hamed_rao"] and basis == "seasonal":
        hr = hamed_rao_factor(an["anomalies"],
                              max_lag=cfg["dependence"]["max_lag"])
        if hr["status"] == "corrected" and math.isfinite(test["var"]) and \
                test["var"] > 0:
            var_c = test["var"] * hr["factor"]
            if test["S"] > 0:
                z = (test["S"] - 1) / math.sqrt(var_c)
            elif test["S"] < 0:
                z = (test["S"] + 1) / math.sqrt(var_c)
            else:
                z = 0.0
            p_adj = 2.0 * (1.0 - _normal_cdf(abs(z)))
            correction = {"method": "hamed_rao",
                          "factor": hr["factor"],
                          "lags_used": hr["lags_used"],
                          "p_uncorrected": p_raw}
    if with_ci:
        if basis == "annual":
            ci = block_bootstrap_ci(annual, cfg, None)
        else:
            ci = block_bootstrap_ci(an["anomalies"], cfg, months)
    else:
        ci = {"ci_low": None, "ci_high": None}
    out.update({
        "state": "succeeded",
        "slope": slope["slope"],
        "slope_units": "units per year",
        "p_value": p_adj,
        "p_value_uncorrected": p_raw,
        "dependence_correction": correction,
        "ci_low": ci["ci_low"],
        "ci_high": ci["ci_high"],
        "ci_meta": {k: ci[k] for k in ("estimand", "interval_method",
                                       "block_length_months", "replicates",
                                       "seed", "confidence")
                    if k in ci},
        "test": {"name": "seasonal_mann_kendall" if basis == "seasonal"
                 else "mann_kendall_annual",
                 "S": test["S"], "z": test["z"], "n": n_eff},
        "anomaly_baseline": an["baseline"],
        "significant_at": _significance_label(p_adj, cfg),
    })
    return out


def _significance_label(p, cfg: dict) -> str | None:
    """Label for display. Never phrased as a probability of a true trend."""
    if p is None or not math.isfinite(p):
        return None
    alpha = cfg["inference"]["alpha"]
    if p < alpha:
        return f"trend detected at alpha={alpha} (p={p:.4g})"
    return f"no trend detected at alpha={alpha} (p={p:.4g})"


# --------------------------------------------------------------------------
# Spatial trends
# --------------------------------------------------------------------------

def anomalies_matrix(flat: np.ndarray, period: int = 12) -> np.ndarray:
    """Seasonal anomalies for a (n_time, n_cells) matrix, per cell.

    Needed because the map path must subtract each cell's own seasonal cycle;
    using one regional climatology for all cells would mix climates.
    """
    flat = np.asarray(flat, dtype="f8")
    nt, nc = flat.shape
    clim = np.full((period, nc), np.nan)
    with np.errstate(invalid="ignore"):
        for s in range(period):
            clim[s] = np.nanmean(flat[s::period], axis=0)
    reps = int(np.ceil(nt / period))
    tiled = np.tile(clim, (reps, 1))[:nt]
    return flat - tiled


def _seasonal_mk_matrix(flat: np.ndarray, period: int):
    """Vectorised seasonal Mann-Kendall S and Var(S) for many cells.

    `flat` is (n_time, n_cells) with NaN for missing values. Pairs involving a
    missing value contribute zero, and Var(S) uses the per-cell valid count,
    so a partially missing cell is not treated as complete.
    """
    nt, nc = flat.shape
    ny = nt // period
    S = np.zeros(nc)
    Var = np.zeros(nc)
    for season in range(period):
        sub = flat[season:season + ny * period:period]
        valid = np.isfinite(sub)
        for i in range(ny - 1):
            d = sub[i + 1:] - sub[i]
            c = np.sign(d)
            c[~np.isfinite(c)] = 0.0
            S += c.sum(axis=0)
        srt = np.sort(sub, axis=0)  # NaN sorts last
        eq = np.zeros_like(srt, dtype=bool)
        eq[1:] = srt[1:] == srt[:-1]
        gid = np.cumsum(~eq, axis=0) - 1
        counts = np.zeros(ny * nc, dtype=np.int64)
        cells = np.tile(np.arange(nc), ny)
        np.add.at(counts, gid.ravel() * nc + cells, 1)
        counts = counts.reshape(ny, nc)
        tcount = counts[gid, np.arange(nc)[None, :]]
        contrib = np.where(~eq & np.isfinite(srt),
                           tcount * (tcount - 1) * (2 * tcount + 5), 0)
        tie = contrib.sum(axis=0)
        n = valid.sum(axis=0).astype("f8")
        Var += (n * (n - 1) * (2 * n + 5) - tie) / 18.0
    return S, Var


def _hamed_rao_matrix(anom: np.ndarray, max_lag: int, alpha: float = 0.05):
    """Vectorised Hamed-Rao variance-inflation factor per cell."""
    nt, nc = anom.shape
    lag_max = int(min(max_lag, nt // 4))
    dev = np.where(np.isfinite(anom), anom, 0.0)
    denom = np.sum(dev ** 2, axis=0)
    n = np.isfinite(anom).sum(axis=0).astype("f8")
    crit = 1.96 / np.sqrt(np.maximum(n, 1))
    total = np.zeros(nc)
    with np.errstate(invalid="ignore", divide="ignore"):
        for lag in range(1, lag_max + 1):
            rho = np.sum(dev[:-lag] * dev[lag:], axis=0) / denom
            sig = np.abs(rho) > crit
            coef = (n - lag) * (n - lag - 1) * (n - lag - 2)
            total += np.where(sig, coef * rho, 0.0)
        factor = 1.0 + (2.0 / (n * (n - 1) * (n - 2))) * total
    factor = np.where(np.isfinite(factor), np.maximum(factor, 1.0), 1.0)
    return factor


def spatial_trend(cube, cfg: dict, chunk_cells: int = 250) -> dict:
    """Per-cell Theil-Sen slope and seasonal MK p-value with BH-FDR.

    Same estimator and same dependence correction as the region card, so a
    map and a card can never disagree about method. `cube` must come from
    preprocess.load_cube with QA already applied. Cells below the coverage
    threshold get null, never zero.
    """
    product = cube.attrs.get("product")
    var = [v for v in cube.data_vars][0]
    data = cube[var].values  # (time, lat, lon)
    nt = data.shape[0]
    flat = data.reshape(nt, -1)
    nc = flat.shape[1]
    months = [str(t)[:7] for t in cube["time"].values]
    period = cfg["inference"]["season_period"]

    S, Var = _seasonal_mk_matrix(flat, period)
    anom = anomalies_matrix(flat, period)
    factor = _hamed_rao_matrix(anom, cfg["dependence"]["max_lag"]) \
        if cfg["dependence"]["apply_hamed_rao"] else np.ones(nc)
    Var_c = Var * factor
    with np.errstate(invalid="ignore", divide="ignore"):
        z = np.where(S > 0, (S - 1) / np.sqrt(Var_c),
                     np.where(S < 0, (S + 1) / np.sqrt(Var_c), 0.0))
        pval = 2.0 * (1.0 - np.vectorize(_normal_cdf)(np.abs(z)))

    nvalid = np.isfinite(flat).sum(axis=0)
    minv = cfg["minimum_series"]
    eligible = ((nvalid >= minv["min_valid_months"]) &
                (nvalid / nt >= minv["min_valid_fraction"]) &
                np.isfinite(pval))
    pval = np.where(eligible, pval, np.nan)

    # vectorised Theil-Sen slope on anomalies, chunked over cells
    iu = np.triu_indices(nt, 1)
    t = _time_in_years(months)
    dt = t[iu[1]] - t[iu[0]]
    slope = np.full(nc, np.nan)
    anom32 = anom.astype("f4")
    dt32 = dt.astype("f4")
    for start in range(0, nc, chunk_cells):
        block = anom32[:, start:start + chunk_cells]
        diff = block[iu[1]] - block[iu[0]]
        slopes = diff / dt32[:, None]
        with np.errstate(invalid="ignore"):
            slope[start:start + block.shape[1]] = np.nanmedian(slopes, axis=0)

    fdr = benjamini_hochberg(pval, q=cfg["multiplicity"]["q"])
    shape = data.shape[1:]
    return {
        "product": product,
        "variable": var,
        "shape": list(data.shape),
        "months": nt,
        "slope": slope.reshape(shape),
        "p_value": pval.reshape(shape),
        "significant_fdr": fdr["reject"].reshape(shape),
        "n_valid_months": nvalid.reshape(shape),
        "dependence_factor": factor.reshape(shape),
        "fdr": {"m_tested": fdr["m"], "threshold": fdr["threshold"],
                "q": cfg["multiplicity"]["q"],
                "family": "all valid cells in this variable x window"},
        "method_revision": cfg["method_revision"],
    }


# --------------------------------------------------------------------------
# Period sensitivity ("Spin It")
# --------------------------------------------------------------------------

def period_sensitivity(x, months, cfg: dict) -> dict:
    """Slopes for a fixed set of sub-periods plus the full-period reference.

    The set of windows is fixed in the config so the answer cannot be steered
    by choosing windows after seeing results. Sign agreement is descriptive,
    not a calibrated probability.
    """
    v = _as_float_series(x)
    months = list(months)
    out = []
    for w in cfg["period_sensitivity"]["windows"]:
        idx = [i for i, m in enumerate(months)
               if w["start"] <= m <= w["end"]]
        if len(idx) < cfg["period_sensitivity"]["min_months"]:
            out.append({"start": w["start"], "end": w["end"],
                        "state": "insufficient_data"})
            continue
        sub = v[idx]
        res = trend_series(sub, [months[i] for i in idx], cfg, with_ci=False)
        out.append({
            "start": w["start"], "end": w["end"],
            "state": res["state"],
            "slope": res.get("slope"),
            "p_value": res.get("p_value"),
            "ci_low": res.get("ci_low"), "ci_high": res.get("ci_high"),
        })
    full = trend_series(v, months, cfg)
    slopes = [r["slope"] for r in out if r.get("slope") is not None]
    pos = sum(1 for s in slopes if s > 0)
    neg = sum(1 for s in slopes if s < 0)
    return {
        "full_period": {"start": months[0], "end": months[-1],
                        "slope": full.get("slope"),
                        "p_value": full.get("p_value"),
                        "ci_low": full.get("ci_low"),
                        "ci_high": full.get("ci_high")},
        "windows": out,
        "sign_agreement": {
            "n_windows": len(slopes),
            "positive": pos,
            "negative": neg,
            "fraction_same_sign_as_full": (
                round(max(pos, neg) / len(slopes), 4) if slopes else None),
            "note": ("descriptive only; depends on the fixed window set and "
                     "is not a calibrated confidence"),
        },
        "method_revision": cfg["method_revision"],
    }


# --------------------------------------------------------------------------
# Evidence card
# --------------------------------------------------------------------------

def region_series(cube, cfg: dict) -> dict:
    """Area-weighted regional mean series (cos-lat weights on native grid)."""
    var = [v for v in cube.data_vars][0]
    lat = cube["lat"].values
    w = np.cos(np.deg2rad(lat))
    w = w / w.sum()
    data = cube[var].values
    series = np.nansum(data * w[None, :, None], axis=(1, 2)) / \
        np.sum(np.isfinite(data) * w[None, :, None], axis=(1, 2))
    valid = np.isfinite(data).sum(axis=(1, 2))
    total = data.shape[1] * data.shape[2]
    return {
        "series": series,
        "valid_cells_per_month": valid,
        "valid_fraction_per_month": valid / total,
        "months": [str(t)[:7] for t in cube["time"].values],
        "weighting": cfg["aggregation"]["weighting"],
    }


def evidence_card(product: str, region_key: str, cfg: dict,
                  with_sensitivity: bool = True) -> dict:
    """Result payload matching the backend contract (M3) and card text (M4)."""
    with pp.load_cube(product, region_key) as ds:
        clean = pp.apply_qa(ds, product, mode=cfg["qa"]["mode"])
        rs = region_series(clean, cfg)
        spec = pp.PRODUCTS[product]
        units = spec["units"]
        series_res = trend_series(rs["series"], rs["months"], cfg)
        card = {
            "variable_id": spec["variable"],
            "product_id": product,
            "version": spec["version"],
            "region_id": region_key,
            "period": {"start": rs["months"][0], "end": rs["months"][-1],
                       "months": len(rs["months"])},
            "units": units,
            "aggregation_policy_id": cfg["aggregation"]["policy_id"],
            "qa_policy_mode": cfg["qa"]["mode"],
            "method_revision": cfg["method_revision"],
            "counts": {
                "months": len(rs["months"]),
                "cells_per_month": int(rs["valid_cells_per_month"].max()),
                "valid_fraction_overall": round(
                    float(np.mean(rs["valid_fraction_per_month"])), 6),
                "min_valid_fraction_month": round(
                    float(np.min(rs["valid_fraction_per_month"])), 6),
            },
            "trend": {
                "slope_per_year": series_res.get("slope"),
                "slope_units": f"{units} per year",
                "p_value": series_res.get("p_value"),
                "p_value_uncorrected": series_res.get("p_value_uncorrected"),
                "ci_low": series_res.get("ci_low"),
                "ci_high": series_res.get("ci_high"),
                "ci_meta": series_res.get("ci_meta"),
                "test": series_res.get("test"),
                "dependence_correction": series_res.get("dependence_correction"),
                "state": series_res.get("state"),
            },
            "interpretation": {
                "headline": _headline(series_res, units, cfg),
                "caveats": _caveats(product, cfg),
            },
            "warnings": [],
        }
        if card["trend"]["state"] != "succeeded":
            card["warnings"].append("insufficient_data: no slope is reported")
        if with_sensitivity:
            card["period_sensitivity"] = period_sensitivity(
                rs["series"], rs["months"], cfg)
    return card


def _headline(res: dict, units: str, cfg: dict) -> str:
    if res.get("state") != "succeeded":
        return "Insufficient data for a trend estimate in this period."
    s = res["slope"]
    lo, hi = res.get("ci_low"), res.get("ci_high")
    p = res.get("p_value")
    if s is None:
        return "Insufficient data for a trend estimate in this period."
    base = f"Estimated change {s:+.4g} {units}/year"
    if lo is not None and hi is not None:
        base += f" (95% interval {lo:+.4g} to {hi:+.4g})"
    if p is not None and math.isfinite(p):
        if p < cfg["inference"]["alpha"]:
            base += (f". The seasonal Mann-Kendall test gives p={p:.3g}, "
                     f"below the frozen threshold {cfg['inference']['alpha']}; "
                     "this is evidence against the no-trend null, not the "
                     "probability that a trend is real.")
        else:
            base += (f". The seasonal Mann-Kendall test gives p={p:.3g}, "
                     "which does not reach the frozen threshold; the effect "
                     "size is still shown but is inconclusive.")
    return base


def _caveats(product: str, cfg: dict) -> list:
    common = [
        "Slope is a descriptive linear-in-time summary, not a forecast or a "
        "causal claim.",
        "Region slope comes from the area-weighted regional series, not from "
        "averaging cell slopes.",
    ]
    specific = {
        "M2TMNXSLV": ["Reanalysis product, not a station observation.",
                      "Kelvin and Celsius give identical slopes; convert only "
                      "for display."],
        "GLDAS_NOAH025_M": ["Land-surface model output; sea cells are missing.",
                            "Not a percentage and not relative humidity."],
        "GPM_3IMERGM": ["Monthly mean rate in mm/hr; multiply by hours in the "
                        "month for mm/month.",
                        "Quality index is reported, not used to exclude cells."],
        "MOD13C2": ["NDVI is a vegetation index, not yield or biomass.",
                    "Default QA mode applied; strict mode changes coverage.",
                    "Morocco window includes ocean cells that carry no NDVI."],
    }
    return common + specific.get(product, [])


def build_spatial_outputs(cfg: dict, out_dir: Path) -> dict:
    """Run the map path on every cube and save compact per-cube arrays."""
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {"method_revision": cfg["method_revision"], "cubes": {}}
    for product in pp.PRODUCTS:
        for region in pp.WINDOWS:
            with pp.load_cube(product, region) as ds:
                clean = pp.apply_qa(ds, product, mode=cfg["qa"]["mode"])
                res = spatial_trend(clean, cfg)
                lat = clean["lat"].values
                lon = clean["lon"].values
            name = f"{product}_{region}"
            np.savez_compressed(
                out_dir / f"{name}.npz",
                slope=res["slope"].astype("f4"),
                p_value=res["p_value"].astype("f4"),
                significant_fdr=res["significant_fdr"].astype("u1"),
                n_valid_months=res["n_valid_months"].astype("i2"),
                dependence_factor=res["dependence_factor"].astype("f4"),
                lat=lat.astype("f4"), lon=lon.astype("f4"))
            s = res["slope"]
            summary["cubes"][name] = {
                "shape": res["shape"],
                "cells_total": int(s.size),
                "cells_eligible": int(res["fdr"]["m_tested"]),
                "cells_significant_fdr": int(res["significant_fdr"].sum()),
                "fdr_threshold": res["fdr"]["threshold"],
                "median_slope": float(np.nanmedian(s)),
                "slope_units": f"{pp.PRODUCTS[product]['units']} per year",
                "file": f"spatial_trends/{name}.npz",
            }
            print(f"map {name}: {summary['cubes'][name]}", flush=True)
    (out_dir.parent / "spatial_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--card", nargs=2, metavar=("PRODUCT", "WINDOW"))
    ap.add_argument("--all-cards", action="store_true")
    ap.add_argument("--spatial", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "evidence_cards.json"))
    args = ap.parse_args(argv)
    cfg = load_config()
    if args.card:
        print(json.dumps(evidence_card(*args.card, cfg), indent=2))
        return 0
    if args.all_cards:
        cards = []
        for product in pp.PRODUCTS:
            for region in pp.WINDOWS:
                cards.append(evidence_card(product, region, cfg))
                print(f"card {product}/{region}", flush=True)
        payload = {"method_revision": cfg["method_revision"],
                   "generated": "2026-11-14", "cards": cards}
        Path(args.out).write_text(json.dumps(payload, indent=2),
                                  encoding="utf-8")
        print(f"wrote {len(cards)} cards to {args.out}")
        return 0
    if args.spatial:
        build_spatial_outputs(cfg, ROOT / "spatial_trends")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
