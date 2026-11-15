"""Research-only Sen-centered Berger--Boos test on a finite AR(1) grid.

No public inference adapter or release flag is changed by this module.
Rows are complete, equally spaced annual records. Missing/degenerate inputs fail.
"""
import numpy as np

from .double_bootstrap_diagnostics import geometry
from .sen_uncertainty import sen_pivot


def profile_scores(y, geo):
    """Profile -2 restricted log likelihood, up to rho-independent constants."""
    y = np.asarray(y, dtype=float)
    rho, a, inv, penalty = geo
    if (y.ndim != 2 or y.shape[1] not in (20, 24)
            or a.shape[-1] != y.shape[1] or not np.isfinite(y).all()):
        raise ValueError('Requires complete 20- or 24-year rows')
    n = y.shape[1]
    g = np.einsum('rkn,bn->rbk', a, y, optimize=True)
    beta = np.einsum('rkl,rbl->rbk', inv, g, optimize=True)
    q = ((y*y).sum(1)[None, :]
         + rho[:, None]**2*((y[:, :-1]**2).sum(1)-y[:, 0]**2)[None, :]
         - 2*rho[:, None]*(y[:, 1:]*y[:, :-1]).sum(1)[None, :])
    sse = q-(g*beta).sum(2)
    if np.any(sse <= 1e-12):
        raise ValueError('Degenerate residual fit')
    return (n-2)*np.log(sse/(n-2)) + penalty[:, None]


def research_geometry(n, grid):
    grid = np.asarray(grid, dtype=float)
    if (grid.ndim != 1 or len(grid) < 2 or not np.isfinite(grid).all()
            or np.any(abs(grid) >= 1) or np.any(np.diff(grid) <= 0)
            or not np.allclose(np.diff(grid), grid[1]-grid[0])):
        raise ValueError('Requires a sorted equally spaced stationary rho grid')
    geo = geometry(n, [grid[0], grid[-1], grid[1]-grid[0]])
    if not np.allclose(geo[0], grid):
        raise ValueError('Grid construction mismatch')
    return geo


def upper_tail(sorted_values, statistic):
    """Conservative plus-one simulated p-value, including ties in the tail."""
    d = np.asarray(sorted_values, dtype=float)
    if (d.ndim != 1 or len(d) < 1 or not np.isfinite(d).all()
            or np.any(np.diff(d) < 0)):
        raise ValueError('Requires a finite sorted calibration distribution')
    return (1+len(d)-np.searchsorted(d, statistic, side='left'))/(len(d)+1)


def inverted_critical(sorted_values, alpha):
    """Exact closed CI endpoint for inversion of the plus-one tail convention.

    With continuous simulated pivots rejection starts immediately above this
    endpoint. Calibration ties make the test conservative. No interpolation.
    """
    d = np.asarray(sorted_values, dtype=float)
    upper_tail(d, 0.)  # validate the calibration input
    if not 0 < alpha < 1:
        raise ValueError('Invalid test level')
    rejected_ranks = int(np.floor(alpha*(len(d)+1) + 1e-10))
    if rejected_ranks == 0:
        raise ValueError('Insufficient simulations for finite interval inversion')
    return float(d[len(d)-rejected_ranks])


def correlation_set(y, geo, lr_distributions, gamma=0.005):
    if not 0 < gamma < 1 or len(lr_distributions) != len(geo[0]):
        raise ValueError('Invalid nuisance calibration')
    scores = profile_scores(y, geo)
    delta = np.maximum(0., scores-scores.min(axis=0, keepdims=True))
    p = np.stack([upper_tail(d, delta[j]) for j, d in enumerate(lr_distributions)])
    members = (p > gamma).T
    empty = ~members.any(axis=1)
    # Fail conservatively if a numerical/calibration anomaly creates an empty C.
    members[empty] = True
    return {'members': members, 'empty_fallback': empty, 'nuisance_p': p.T}


def berger_boos(y, geo, lr_distributions, pivot_distributions,
                gamma=0.005, alpha=0.05):
    if not 0 < gamma < alpha < 1 or len(pivot_distributions) != len(geo[0]):
        raise ValueError('Invalid error budget or calibration dimensions')
    slope, scale = sen_pivot(y)
    c = correlation_set(y, geo, lr_distributions, gamma)
    p = np.stack([upper_tail(d, abs(slope/scale))
                  for d in pivot_distributions], axis=1)
    critical = np.array([inverted_critical(d, alpha-gamma)
                         for d in pivot_distributions])
    probability = np.minimum(1., np.where(c['members'], p, -np.inf).max(axis=1)+gamma)
    radius = np.where(c['members'], critical[None, :], -np.inf).max(axis=1)*scale
    return {'slope': slope, 'scale': scale, 'p': probability,
            'radius': radius, **c}
