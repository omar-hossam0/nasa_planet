"""Model-conditional linear-trend inference; NOT an application release.

Known covariance shape: exact Student t with n-2 degrees of freedom.
Unknown stationary Gaussian AR(1) rho in an externally specified compact range:
union of fixed-rho intervals and maximum fixed-rho p, with a Gaussian KL/Pinsker
guard for *continuous* rho between grid points. No fitted-rho plug-in shortcut.

Targets beta in Y = intercept + beta * year + Gaussian AR1 errors, not the
sampling distribution of the observed Sen median. Cannot establish that NASA
errors satisfy this model. Historical failed methods/artifacts remain unchanged.
"""
from functools import lru_cache
import numbers

import numpy as np
from scipy.stats import t as student

from .trend_estimation import annual_elapsed_years


def _data(values, years):
    x = annual_elapsed_years(years)
    y = np.asarray(values, dtype=float)
    single = y.ndim == 1
    if single:
        y = y[None, :]
    if y.ndim != 2 or y.shape[1] != len(x) or len(x) < 4:
        raise ValueError("Requires rows of >=4 complete annual observations")
    if not np.isfinite(y).all() or not np.all(np.diff(x) == 1):
        raise ValueError("Requires finite consecutive years; no missing-value imputation")
    # Removing a free intercept first improves numeric conditioning at Kelvin offsets.
    return y - y.mean(axis=1, keepdims=True), x, single


@lru_cache(maxsize=8)
def _geometry(n, lower, upper, grid_size):
    rho = np.linspace(lower, upper, grid_size)
    x = np.arange(n, dtype=float)
    design = np.column_stack([np.ones(n), x])
    # Innovation-variance precision; its global scale cancels in the Student pivot.
    transform = np.broadcast_to(np.eye(n), (grid_size, n, n)).copy()
    transform[:, 0, 0] = np.sqrt(1-rho*rho)
    transform[:, np.arange(1, n), np.arange(n-1)] = -rho[:, None]
    whitened = transform @ design
    inverse = np.linalg.inv(np.einsum("rni,rnj->rij", whitened, whitened))
    score = np.einsum("rni,rnm->rim", whitened, transform)
    for a in (rho, inverse, score):
        a.flags.writeable = False
    return rho, inverse, score


def _fits(y, rho, inverse, score):
    g = np.einsum("rin,bn->rib", score, y, optimize=True)
    beta = np.einsum("rij,rjb->rib", inverse, g, optimize=True)
    # Stationary first observation + conditional innovations.
    quadratic = ((y*y).sum(axis=1)[None, :]
                 + rho[:, None]**2 * (y[:, 1:-1]**2).sum(axis=1)[None, :]
                 - 2*rho[:, None]*(y[:, 1:]*y[:, :-1]).sum(axis=1)[None, :])
    sse = quadratic - np.sum(g*beta, axis=1)
    tolerance = 256*np.finfo(float).eps*np.maximum(quadratic, 1e-300)
    if np.any(sse <= tolerance):
        raise ValueError("Degenerate residual variation; no calibrated empirical uncertainty")
    se = np.sqrt(sse/(y.shape[1]-2)*inverse[:, 1, 1, None])
    return beta[:, 1], se


def _finish(result, single):
    if not single:
        return result
    return {k: (float(v[0]) if isinstance(v, np.ndarray) and v.ndim == 1 else
                v[0].tolist() if isinstance(v, np.ndarray) else v) for k, v in result.items()}


def known_rho_inference(values, years, *, rho, confidence=.95):
    """Reference path: rho must be known independently, never estimated then fixed."""
    if not np.isfinite(rho) or not -1 < rho < 1 or not 0 < confidence < 1:
        raise ValueError("Invalid rho or confidence")
    y, _, single = _data(values, years)
    grid, inverse, score = _geometry(y.shape[1], float(rho), float(rho), 1)
    slope, se = _fits(y, grid, inverse, score)
    p = 2*student.sf(abs(slope[0]/se[0]), y.shape[1]-2)
    radius = student.ppf((1+confidence)/2, y.shape[1]-2)*se[0]
    return _finish({"slope": slope[0], "p": p,
        "interval": np.column_stack([slope[0]-radius, slope[0]+radius]),
        "confidence": confidence, "rho": float(rho), "df": y.shape[1]-2,
        "status": "model_conditional_known_rho", "application_release": False,
        "estimand": "linear mean-trend coefficient; covariance shape independently known"}, single)


def continuous_rho_guard(n, lower, upper, grid_size):
    """TV guard for closest grid normal with the SAME mean and marginal scale.

    KL(r||s) = (n-1)/2 * [2s(s-r)/(1-s²) + log(1-s²)-log(1-r²)].
    For fixed s this is convex in r, so each nearest-grid cell's endpoints bound
    the entire cell. Pinsker gives TV <= sqrt(KL/2), uniform in mean/scale.
    """
    grid = np.linspace(lower, upper, grid_size)
    edges = np.r_[lower, (grid[:-1]+grid[1:])/2, upper]
    maximum = 0.
    for actual in (edges[:-1], edges[1:]):
        divergence = (n-1)/2*(2*grid*(grid-actual)/(1-grid*grid)
            + np.log1p(-grid*grid)-np.log1p(-actual*actual))
        maximum = max(maximum, float(divergence.max()))
    return min(1., np.sqrt(maximum/2)+1e-10)


def bounded_ar1_inference(values, years, *, rho_bounds=(-.95, .95),
                          grid_size=4001, confidence=.95, batch_size=128):
    """Conservative p/CI for explicitly bounded stationary Gaussian AR1 errors.

    If s is nearest the true rho, P_r(p_s<=u) <= u+epsilon. Since max_grid p>=p_s,
    p_bound=min(1,max_grid p+epsilon) is super-uniform. The interval envelope uses
    alpha-epsilon, giving at least requested coverage under the same model.
    This is conservative, not a promise of exactly 5%/95% or good power.
    """
    lower, upper = rho_bounds
    if not np.isfinite([lower, upper]).all() or not -1 < lower < upper < 1:
        raise ValueError("Specify a finite external rho range strictly inside (-1,1)")
    for value, minimum in ((grid_size, 3), (batch_size, 1)):
        if isinstance(value, bool) or not isinstance(value, numbers.Integral) or value < minimum:
            raise ValueError("Invalid grid or batch size")
    if not 0 < confidence < 1:
        raise ValueError("Invalid confidence")
    y, x, single = _data(values, years)
    epsilon = continuous_rho_guard(len(x), lower, upper, grid_size)
    tail = 1-confidence-epsilon
    if tail <= 0:
        raise ValueError("Grid too coarse for requested confidence; increase grid_size")
    grid, inverse, score = _geometry(len(x), float(lower), float(upper), grid_size)
    probability, lows, highs = [], [], []
    critical = student.ppf(1-tail/2, len(x)-2)
    for start in range(0, len(y), batch_size):
        slope, se = _fits(y[start:start+batch_size], grid, inverse, score)
        probabilities = 2*student.sf(abs(slope/se), len(x)-2)
        probability.extend(np.minimum(1, probabilities.max(axis=0)+epsilon))
        lows.extend((slope-critical*se).min(axis=0))
        highs.extend((slope+critical*se).max(axis=0))
    centered_x = x-x.mean()
    ols_slope = y@centered_x/(centered_x@centered_x)
    return _finish({"slope": ols_slope, "p": np.asarray(probability),
        "interval": np.column_stack([lows, highs]), "confidence": confidence,
        "rho_bounds": [lower, upper], "grid_size": grid_size,
        "continuous_rho_TV_guard": epsilon, "df": len(x)-2,
        "status": "model_conditional_bounded_rho", "application_release": False,
        "estimand": "linear mean-trend coefficient; point estimate OLS, interval GLS envelope"}, single)
