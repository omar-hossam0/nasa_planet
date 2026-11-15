import sys
import unittest
from pathlib import Path
import numpy as np
from scipy.linalg import toeplitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.inference_candidates import adjusted_mk, ar1_regression, gls_fixed_rho


class FollowupTests(unittest.TestCase):
    def test_whitening_matches_dense_covariance_gls(self):
        y=np.random.default_rng(1).normal(size=24);x=np.arange(24)
        X=np.column_stack([np.ones(24),x])
        for rho in [-.5,0,.4,.8]:
            inv=np.linalg.inv(toeplitz(rho**np.arange(24)))
            expected=np.linalg.solve(X.T@inv@X,X.T@inv@y)
            np.testing.assert_allclose(gls_fixed_rho(y,x,rho)[0],expected,atol=1e-12)

    def test_missing_short_constant_no_fabricated_inference(self):
        for method in [adjusted_mk,ar1_regression]:
            for n in [0,2,19]:
                r=method(np.arange(n),np.arange(2001,2001+n))
                self.assertEqual(r['status'],'insufficient_data')
                self.assertIsNone(r['interval'])
            y=np.arange(24,dtype=float);y[3]=np.nan
            self.assertEqual(method(y,np.arange(2001,2025))['status'],'insufficient_data')
            self.assertTrue(np.isnan(y[3]))
            self.assertEqual(method(np.ones(24),np.arange(2001,2025))['status'],'no_variation')

    def test_offset_and_positive_scale(self):
        y=np.random.default_rng(3).normal(size=24);years=np.arange(2001,2025)
        for method in [adjusted_mk,ar1_regression]:
            a=method(y,years);b=method(y*10+273.15,years)
            self.assertAlmostEqual(a['slope']*10,b['slope'])
            self.assertAlmostEqual(a['p'],b['p'])
            np.testing.assert_allclose(np.array(a['interval'])*10,b['interval'],atol=1e-10)

    def test_mk_slope_matches_pair_median_with_ties(self):
        y=np.repeat(np.arange(10),2);x=np.arange(20)
        i,j=np.triu_indices(20,1)
        a=adjusted_mk(y,2001+x)
        self.assertAlmostEqual(a['slope'],np.median((y[j]-y[i])/(j-i)))
        self.assertGreaterEqual(a['variance_factor'],1)

    def test_invalid_time_or_infinity_rejected(self):
        for method in [adjusted_mk,ar1_regression]:
            with self.assertRaises(ValueError):method(np.ones(24),np.zeros(24))
            with self.assertRaises(ValueError):method(np.full(24,np.inf),np.arange(2001,2025))


if __name__=='__main__':unittest.main()
