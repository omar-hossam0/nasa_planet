"""Experimental annual slope inference; calibration is a separate release gate.

Complete equally spaced annual series only. No missing residual is replaced or
compressed. Multiplicity adjustment is a mathematical operation, not a repair
for invalid marginal p-values or a statement that assumptions hold in NASA data.
"""
from __future__ import annotations

import numbers
import numpy as np

from .trend_estimation import annual_elapsed_years, sen_slopes, trend_series


def circular_block_indices(n: int, replicates: int, block_length: int,
                           rng: np.random.Generator) -> np.ndarray:
    for value in (n, replicates, block_length):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral) or value < 1:
            raise ValueError("Lengths and replicate counts must be positive integers")
    if block_length > n:
        raise ValueError("Block length cannot exceed the record")
    starts = rng.integers(0, n, size=(replicates, (n + block_length - 1) // block_length))
    return ((starts[:, :, None] + np.arange(block_length)) % n).reshape(replicates, -1)[:, :n]


def annual_inference(values, years, *, block_length=4, replicates=999,
                     confidence=.95, seed=0, min_points=20) -> dict:
    t = annual_elapsed_years(years)
    y = np.asarray(values, dtype="float64")
    if y.ndim != 1 or y.shape != t.shape or np.isinf(y).any():
        raise ValueError("Expected aligned annual values; infinity is invalid")
    if not 0 < confidence < 1:
        raise ValueError("Confidence must lie in (0, 1)")
    for value, lower in ((min_points, 3), (replicates, 99), (block_length, 1)):
        if isinstance(value, (bool, np.bool_)) or not isinstance(value, numbers.Integral) or value < lower:
            raise ValueError("Invalid minimum count, replicate count or block length")
    base = {"status": "insufficient_data", "slope_per_year": None, "p_value_candidate": None,
            "interval_candidate": None, "n_records": len(y), "n_valid": int(np.isfinite(y).sum()),
            "block_length_years": block_length, "bootstrap_replicates": replicates,
            "confidence_level": confidence, "seed": int(seed), "application_release": False}
    if len(y) < min_points or not np.isfinite(y).all():
        return {**base, "reason": "requires a complete annual record meeting the candidate minimum; missing values are not filled"}
    if not np.all(np.diff(t) == 1):
        return {**base, "reason": "requires consecutive annual labels; missing years are not compressed"}
    if block_length > len(y):
        raise ValueError("Block length exceeds record")
    slope = trend_series(y, t)["slope_per_year"]
    if np.ptp(y) == 0:
        return {**base, "status": "no_variation", "slope_per_year": slope,
                "reason": "zero empirical variation does not validate an uncertainty interval"}
    residual = y - slope * t
    residual = residual - np.median(residual)
    if np.ptp(residual) <= 64 * np.finfo(float).eps * max(1., float(np.abs(y).max())):
        return {**base, "status": "no_residual_variation", "slope_per_year": slope,
                "reason": "empirical residual variation is zero; uncertainty is not calibrated"}
    indices = circular_block_indices(len(y), replicates, block_length, np.random.default_rng(seed))
    errors = sen_slopes(residual[indices].T, t)["slope"]
    # Affine equivariance: Sen(slope*t + resampled residual) - slope equals
    # Sen(resampled residual). This avoids rebuilding a fitted series and never
    # changes the estimator or invents observations in a source-data artifact.
    alpha = 1 - confidence
    lower, upper = np.quantile(errors, [alpha / 2, 1 - alpha / 2])
    interval = [float(slope - upper), float(slope - lower)]
    p = (1 + int((np.abs(errors) >= abs(slope)).sum())) / (replicates + 1)
    return {**base, "status": "candidate_diagnostic", "slope_per_year": slope,
            "p_value_candidate": float(p), "interval_candidate": interval,
            "reason": "experimental calibration-dependent estimates; not released",
            "interval_definition": "basic bootstrap using residual slope errors",
            "p_definition": "plus-one two-sided absolute residual slope tail",
            "residual_lag1_correlation": float(np.corrcoef(residual[:-1], residual[1:])[0, 1]) if np.ptp(residual) > 0 else None}


def adjust_fdr(p_values, *, method="BY", q=.05) -> dict:
    p = np.asarray(p_values, dtype="float64")
    if method not in ("BH", "BY") or not 0 < q < 1:
        raise ValueError("Expected BH/BY and q in (0, 1)")
    if np.isinf(p).any() or np.any((p < 0) | (p > 1)):
        raise ValueError("P-values must be in [0, 1]; NaN denotes untested")
    valid = np.isfinite(p)
    raw = p[valid]
    m = len(raw)
    adjusted = np.full(p.shape, np.nan)
    decisions = np.zeros(p.shape, dtype=bool)
    if m:
        order = np.argsort(raw, kind="stable")
        factor = np.sum(1 / np.arange(1, m + 1)) if method == "BY" else 1.
        ordered = raw[order] * m * factor / np.arange(1, m + 1)
        ordered = np.minimum.accumulate(ordered[::-1])[::-1].clip(0, 1)
        restored = np.empty(m)
        restored[order] = ordered
        adjusted[valid] = restored
        decisions[valid] = restored <= q
    return {"adjusted_p": adjusted, "reject": decisions, "tested_count": m,
            "untested_count": int((~valid).sum()), "method": method, "q": q}


def wilson_interval(successes: int, trials: int) -> list[float]:
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError("Invalid Monte Carlo counts")
    z = 1.959963984540054
    p = successes / trials
    denominator = 1 + z * z / trials
    centre = (p + z * z / (2 * trials)) / denominator
    radius = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / denominator
    return [float(max(0, centre - radius)), float(min(1, centre + radius))]
