import sys
from pathlib import Path
import unittest
import numpy as np
from scipy.linalg import toeplitz
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.reml_uncertainty import fit_reml, geometry, refitted_t_errors


class REMLTests(unittest.TestCase):
    def test_profile_matches_independent_dense_reml(self):
        y=np.random.default_rng(91).normal(size=20);x=np.column_stack([np.ones(20),np.arange(20)])
        scores=[];betas=[]
        for rho in geometry(20)[0]:
            cov=toeplitz(rho**np.arange(20))/(1-rho*rho);w=np.linalg.inv(cov)
            g=x.T@w@x;beta=np.linalg.solve(g,x.T@w@y);res=y-x@beta
            scores.append(18*np.log(res@w@res/18)+np.linalg.slogdet(cov)[1]+np.linalg.slogdet(g)[1]);betas.append(beta)
        best=np.argmin(scores);actual=fit_reml(y[None,:])
        self.assertAlmostEqual(actual['rho'][0],geometry(20)[0][best])
        self.assertAlmostEqual(actual['slope'][0],betas[best][1])

    def test_affine_equivariance_preserves_nuisance_fit(self):
        y=np.random.default_rng(1).normal(size=(10,24));a=fit_reml(y)
        b=fit_reml(y*10+273.15+.08*np.arange(24))
        np.testing.assert_allclose(a['rho'],b['rho'],atol=1e-12)
        np.testing.assert_allclose(a['slope']*10+.08,b['slope'],atol=1e-10)
        np.testing.assert_allclose(a['se']*10,b['se'],rtol=1e-9)

    def test_bootstrap_refits_dependence_in_each_draw(self):
        a,bound=refitted_t_errors(.7,20,199,32)
        b,_=refitted_t_errors(.7,20,199,32)
        np.testing.assert_array_equal(a,b)
        self.assertTrue(np.isfinite(a).all())
        self.assertTrue(0<=bound<=1)

    def test_missing_short_and_degenerate_rejected(self):
        for y in [np.ones((1,19)),np.ones((1,20)),np.full((1,24),np.nan)]:
            with self.assertRaises(ValueError):fit_reml(y)


if __name__=='__main__':unittest.main()
