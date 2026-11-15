"""Independent references and admission checks, not empirical calibration."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest
from scipy.linalg import toeplitz, solve_triangular
from scipy.stats import linregress, t as student

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.gaussian_ar1_inference import (known_rho_inference, bounded_ar1_inference,
                                       continuous_rho_guard)


def test_iid_matches_independent_scipy_regression():
    x = np.arange(24)
    y = 290+.08*x+np.random.default_rng(51).normal(size=24)
    reference = linregress(x, y)
    actual = known_rho_inference(y, x+2001, rho=0)
    assert actual['slope'] == pytest.approx(reference.slope, abs=1e-13)
    assert actual['p'] == pytest.approx(reference.pvalue, abs=1e-13)
    radius = student.ppf(.975, 22)*reference.stderr
    np.testing.assert_allclose(actual['interval'], [reference.slope-radius, reference.slope+radius], atol=1e-13)


@pytest.mark.parametrize('rho', [-.8, .4, .9, .9333])
def test_known_rho_matches_independent_dense_cholesky_reference(rho):
    rng = np.random.default_rng(82)
    x = np.arange(24)
    y = 300+.08*x+rng.normal(size=24)
    covariance = toeplitz(rho**x)
    lower = np.linalg.cholesky(covariance)
    design = solve_triangular(lower, np.column_stack([np.ones(24), x]), lower=True)
    values = solve_triangular(lower, y, lower=True)
    coefficients = np.linalg.lstsq(design, values, rcond=None)[0]
    residual = values-design@coefficients
    se = math.sqrt((residual@residual)/22*np.linalg.inv(design.T@design)[1, 1])
    expected_p = 2*student.sf(abs(coefficients[1]/se), 22)
    actual = known_rho_inference(y, x+2001, rho=rho)
    assert actual['p'] == pytest.approx(expected_p, abs=1e-12)
    assert actual['slope'] == pytest.approx(coefficients[1], abs=1e-12)


def test_manufactured_t_statistic_has_known_numeric_p():
    x = np.arange(8, dtype=float)
    centered = x-x.mean()
    design = np.column_stack([np.ones(8), x])
    residual = np.array([1., -1, 1, -1, 1, -1, 1, -1])
    residual -= design@np.linalg.lstsq(design, residual, rcond=None)[0]
    residual /= np.linalg.norm(residual)
    residual *= .1*np.linalg.norm(centered)*math.sqrt(6)/3
    y = 290+.1*x+residual
    actual = known_rho_inference(y, x+2001, rho=0)
    assert actual['p'] == pytest.approx(0.024008196755730942, abs=1e-13)


def test_continuous_guard_bounds_independent_dense_kl():
    n, count = 24, 101
    grid = np.linspace(-.95, .95, count)
    bound = continuous_rho_guard(n, -.95, .95, count)
    for actual_rho in [-.949, -.931, -.017, .3333, .932, .949]:
        nearest = grid[np.argmin(abs(grid-actual_rho))]
        a, b = toeplitz(actual_rho**np.arange(n)), toeplitz(nearest**np.arange(n))
        kl = .5*(np.trace(np.linalg.solve(b, a))-n+np.linalg.slogdet(b)[1]-np.linalg.slogdet(a)[1])
        assert math.sqrt(max(0, kl)/2) <= bound+1e-12


def test_envelope_contains_grid_intervals_and_is_not_smaller_p():
    y = np.random.default_rng(3).normal(size=24)+.1*np.arange(24)
    years = np.arange(2001, 2025)
    actual = bounded_ar1_inference(y, years)
    eps = actual['continuous_rho_TV_guard']
    for rho in [-.95, 0., .95]:
        ref = known_rho_inference(y, years, rho=rho, confidence=.95+eps)
        assert actual['p'] >= ref['p']-1e-12
        assert actual['interval'][0] <= ref['interval'][0]+1e-12
        assert actual['interval'][1] >= ref['interval'][1]-1e-12
    assert actual['application_release'] is False


def test_batch_scale_offset_and_sign_equivariance():
    y = np.random.default_rng(123).normal(size=(3, 24))+.08*np.arange(24)
    years = np.arange(2001, 2025)
    a = bounded_ar1_inference(y, years, batch_size=1)
    b = bounded_ar1_inference(273.15-10*y, years, batch_size=2)
    np.testing.assert_allclose(a['p'], b['p'], atol=1e-12)
    np.testing.assert_allclose(-10*a['slope'], b['slope'], atol=1e-12)
    np.testing.assert_allclose(-10*a['interval'][:, ::-1], b['interval'], atol=1e-10)


def test_missing_gaps_degenerate_and_invalid_parameters_rejected():
    years = np.arange(2001, 2025)
    y = np.random.default_rng(8).normal(size=24)
    for data, axis in [(np.ones(24), years), (.1*np.arange(24), years),
                       (np.where(np.arange(24)==3, np.nan, y), years),
                       (y, years+np.where(np.arange(24)>12, 1, 0))]:
        with pytest.raises(ValueError):
            bounded_ar1_inference(data, axis)
    for kwargs in [{'grid_size': 3}, {'grid_size': True}, {'batch_size': 0},
                   {'rho_bounds': (-1, .9)}, {'confidence': 1}]:
        with pytest.raises(ValueError):
            bounded_ar1_inference(y, years, **kwargs)
