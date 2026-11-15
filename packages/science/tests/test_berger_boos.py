import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.berger_boos import (profile_scores, research_geometry, upper_tail,
                             inverted_critical, correlation_set, berger_boos)
from src.sen_uncertainty import sen_pivot
from src.reml_uncertainty import simulate_ar


class BergerBoosTests(unittest.TestCase):
    def setUp(self):
        self.grid = [-.5, 0., .5]
        self.geo = research_geometry(20, self.grid)
        self.y = np.random.default_rng(87).normal(size=(12, 20))
        self.lr = [np.linspace(0, 20, 999) for _ in self.grid]
        self.pivot = [np.linspace(0, 1+i, 999) for i in range(3)]

    def test_profile_score_against_independent_dense_covariance(self):
        x = np.column_stack([np.ones(20), np.arange(20)])
        expected = []
        for r in self.grid:
            covariance = r**abs(np.arange(20)[:, None]-np.arange(20))/(1-r*r)
            precision = np.linalg.inv(covariance)
            normal = x.T@precision@x
            beta = np.linalg.solve(normal, x.T@precision@self.y.T).T
            residual = self.y-beta@x.T
            sse = np.einsum('bi,ij,bj->b', residual, precision, residual)
            expected.append(18*np.log(sse/18)+np.linalg.slogdet(covariance)[1]
                            +np.linalg.slogdet(normal)[1])
        np.testing.assert_allclose(profile_scores(self.y, self.geo), expected, atol=1e-12)

    def test_profile_delta_and_set_affine_invariance(self):
        a = profile_scores(self.y, self.geo)
        b = profile_scores(3*self.y+4+.1*np.arange(20), self.geo)
        np.testing.assert_allclose(a-a.min(0), b-b.min(0), atol=1e-11)
        ca = correlation_set(self.y, self.geo, self.lr)
        cb = correlation_set(3*self.y+4+.1*np.arange(20), self.geo, self.lr)
        np.testing.assert_array_equal(ca['members'], cb['members'])

    def test_tail_ties_and_exact_inversion(self):
        np.testing.assert_allclose(upper_tail([1, 1, 2], [0, 1, 1.5, 2, 3]),
                                   [1, 1, .5, .5, .25])
        d = np.arange(1., 1000.)
        q = inverted_critical(d, .045)
        self.assertEqual(q, 955.)
        self.assertGreater(upper_tail(d, q), .045)
        self.assertLessEqual(upper_tail(d, np.nextafter(q, np.inf)), .045)
        with self.assertRaises(ValueError):
            inverted_critical([1, 2], .045)

    def test_point_estimator_budget_and_ci_test_duality(self):
        out = berger_boos(self.y, self.geo, self.lr, self.pivot)
        np.testing.assert_array_equal(out['slope'], sen_pivot(self.y)[0])
        np.testing.assert_array_equal(out['p'] <= .05, abs(out['slope']) > out['radius'])
        self.assertTrue((out['p'] >= .005).all())
        self.assertTrue((out['p'] <= 1).all())
        self.assertFalse(out['empty_fallback'].any())
        changed = berger_boos(2*self.y+8+.08*np.arange(20), self.geo, self.lr, self.pivot)
        np.testing.assert_allclose(changed['radius'], 2*out['radius'])
        np.testing.assert_allclose(changed['slope'], 2*out['slope']+.08)

    def test_manual_maximum_over_members_and_gamma(self):
        rng = np.random.default_rng(54)
        lr = [np.sort(rng.uniform(0, .02, 999)) for _ in self.grid]
        out = berger_boos(self.y, self.geo, lr, self.pivot)
        for i in range(len(self.y)):
            indices = np.flatnonzero(out['members'][i])
            p = max(upper_tail(self.pivot[j], abs(out['slope'][i]/out['scale'][i]))
                    for j in indices)
            self.assertAlmostEqual(out['p'][i], min(1, p+.005))
            radius = max(inverted_critical(self.pivot[j], .045) for j in indices)*out['scale'][i]
            self.assertAlmostEqual(out['radius'][i], radius)

    def test_missing_short_degenerate_and_bad_grid_fail(self):
        for y in [np.full((1, 20), np.nan), np.ones((1, 20)), self.y[:, :19]]:
            with self.assertRaises(ValueError):
                berger_boos(y, self.geo, self.lr, self.pivot)
        for grid in [[0, 1], [.2, .1], [0, .2, .7]]:
            with self.assertRaises(ValueError):
                research_geometry(20, grid)

    def test_stationary_ar_simulator_against_direct_recursion(self):
        z = np.random.default_rng(42).normal(size=(10, 24))
        for rho in [-.4, 0, .7, .9]:
            expected = np.empty_like(z)
            expected[:, 0] = z[:, 0]/np.sqrt(1-rho*rho)
            for k in range(1, 24):
                expected[:, k] = rho*expected[:, k-1]+z[:, k]
            np.testing.assert_array_equal(simulate_ar(z, rho), expected)


if __name__ == '__main__':
    unittest.main()
