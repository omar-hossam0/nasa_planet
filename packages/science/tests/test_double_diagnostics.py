import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.double_bootstrap_diagnostics import geometry,fit,build_cache,probabilities
from src.reml_uncertainty import fit_reml
from src.trend_estimation import sen_slopes


class DoubleDiagnosticsTests(unittest.TestCase):
    def test_original_grid_reproduces_original_fit(self):
        y=np.random.default_rng(72).normal(size=(20,24))
        a=fit(y,geometry(24,[-.5,.95,.025]));b=fit_reml(y)
        for k in ['slope','se','rho']:np.testing.assert_allclose(a[k],b[k],atol=1e-11)

    def test_grids_ordered_and_include_endpoints(self):
        for spec in [[-.5,.95,.025],[-.5,.95,.0125],[-.9,.99,.025]]:
            g=geometry(20,spec)[0]
            self.assertTrue((np.diff(g)>0).all())
            self.assertAlmostEqual(g[0],spec[0]);self.assertAlmostEqual(g[-1],spec[1])

    def test_cache_reproducibility_and_monotone_p(self):
        cache=build_cache(20,[-.5,.95,.25],23,199,199)
        geo,inner,outer,c,inv=cache
        stat=np.linspace(0,20,100);indices=np.full(100,2)
        p=probabilities(stat,indices,inner,outer)
        self.assertTrue((np.diff(p)<=0).all())
        self.assertTrue(((p>=1/200)&(p<=1)).all())
        again=build_cache(20,[-.5,.95,.25],23,199,199)
        np.testing.assert_array_equal(c,again[3])

    def test_sen_and_regression_are_not_interchangeable(self):
        y=.03*np.arange(20);y[-1]+=6
        sen=sen_slopes(y,np.arange(20))['slope'].item()
        regression=fit(y[None,:],geometry(20,[-.5,.95,.025]))['slope'][0]
        self.assertAlmostEqual(sen,.03)
        self.assertGreater(abs(sen-regression),.01)

    def test_no_missing_observation_filled(self):
        y=np.ones((1,20));y[0,3]=np.nan
        with self.assertRaises(ValueError):fit(y,geometry(20,[-.5,.95,.025]))
        self.assertTrue(np.isnan(y[0,3]))


if __name__=='__main__':unittest.main()
