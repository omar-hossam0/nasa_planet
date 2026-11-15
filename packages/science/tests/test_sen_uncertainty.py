import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from src.sen_uncertainty import sen_pivot,calibrated_sen,subsampling_sen
from src.trend_estimation import sen_slopes


class SenUncertaintyTests(unittest.TestCase):
    def setUp(self):self.y=np.random.default_rng(3).normal(size=(8,24))

    def test_point_is_exact_descriptive_sen(self):
        slope,scale=sen_pivot(self.y)
        np.testing.assert_array_equal(slope,sen_slopes(self.y.T,np.arange(24))['slope'])
        self.assertTrue((scale>0).all())
        for f in [.35,.5,.65]:np.testing.assert_array_equal(subsampling_sen(self.y,f)['slope'],slope)

    def test_affine_scale_equivariance(self):
        a,s=sen_pivot(self.y);b,t=sen_pivot(3*self.y+273.15+.02*np.arange(24))
        np.testing.assert_allclose(b,3*a+.02,atol=1e-12)
        np.testing.assert_allclose(t,3*s,atol=1e-12)

    def test_envelope_dominates_plugin(self):
        d=[np.linspace(0,1,100),np.linspace(0,3,100)]
        full=calibrated_sen(self.y,[0,.7],d)
        plugin=calibrated_sen(self.y,[0,.7],d,np.zeros(8))
        self.assertTrue((full['p']>=plugin['p']).all())
        self.assertTrue((full['radius']>=plugin['radius']).all())

    def test_missing_and_degenerate_not_filled(self):
        for y in [np.ones((1,24)),np.full((1,24),np.nan)]:
            with self.assertRaises(ValueError):sen_pivot(y)


if __name__=='__main__':unittest.main()
