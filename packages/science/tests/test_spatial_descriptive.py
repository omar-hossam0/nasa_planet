import sys
from pathlib import Path
import unittest
import numpy as np
import xarray as xr
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.spatial_descriptive import directions, shares, analyze_window


class SpatialTests(unittest.TestCase):
    def fixture(self):
        years = np.arange(2001, 2009)
        values = np.arange(8.)[:, None, None]*np.array([1., -2., 0., np.nan])[None,None,:]
        cells = xr.DataArray(values, dims=('year','lat','lon'), coords={'year':years,'lat':[15.], 'lon':[1.,2.,3.,4.]}, attrs={'units':'K'})
        support = xr.DataArray([[1,1,1,1]],dims=('lat','lon'),coords={'lat':cells.lat,'lon':cells.lon})
        regional = xr.DataArray(np.arange(8.)*7, dims='year',coords={'year':years},attrs={'units':'K'})
        return cells, regional, support

    def test_four_directions_exact_zero(self):
        np.testing.assert_array_equal(directions([1,-1,0,np.nan,1e-30],[1]*5),[1,-1,2,0,1])

    def test_denominators_and_exclusions(self):
        a=shares([1,-1,0,np.nan,5],[1,1,1,1,0])
        self.assertEqual(a['eligible_cells'],4);self.assertEqual(a['excluded_cells'],1)
        self.assertEqual(sum(a['counts'].values()),4)
        self.assertEqual(a['percent_of_eligible_cells']['unavailable'],25)
        self.assertIsNone(shares([np.nan],[0])['percent_of_eligible_cells']['positive'])

    def test_region_separate_and_units(self):
        c,r,s=self.fixture();g,a=analyze_window(c,r,s,'annual',2001,2008)
        np.testing.assert_allclose(g.slope,[[1,-2,0,np.nan]],equal_nan=True)
        self.assertEqual(a['slope_per_year'],7);self.assertEqual(a['slope_units'],'K per year')

    def test_missing_and_insufficient(self):
        c,r,s=self.fixture();c.values[:6,0,0]=np.nan
        g,a=analyze_window(c,r,s,'annual',2001,2008)
        self.assertEqual(g.n_valid.values[0,0],2);self.assertTrue(np.isnan(g.slope.values[0,0]))

    def test_period_actual_reference(self):
        c,r,s=self.fixture();c.values[:,0,0]=[0,1,2,3,4,3,2,1]
        full,_=analyze_window(c,r,s,'annual',2001,2008)
        g,a=analyze_window(c,r,s,'annual',2005,2008,full)
        self.assertEqual(g.slope.values[0,0],-1)
        self.assertEqual(g.direction_agrees_full_period.values[0,0],0)
        self.assertEqual(a['n_valid'],4)

    def test_policy_isolation(self):
        c,r,s=self.fixture();before=c.copy(deep=True);s.values[0,0]=0
        g,_=analyze_window(c,r,s,'annual',2001,2008)
        self.assertTrue(np.isnan(g.slope.values[0,0]));xr.testing.assert_equal(c,before)

    def test_geographic_and_window_guards(self):
        c,r,s=self.fixture()
        with self.assertRaises(AssertionError):analyze_window(c,r,s.assign_coords(lon=[2,3,4,5]),'annual',2001,2008)
        with self.assertRaises(ValueError):analyze_window(c,r,s,'annual',2000,2008)

    def test_monthly_elapsed_years(self):
        c,r,s=self.fixture();time=np.arange('2001-01','2001-09',dtype='datetime64[M]')
        c=c.rename(year='time').assign_coords(time=time);r=r.rename(year='time').assign_coords(time=time)
        g,a=analyze_window(c,r,s,'monthly',2001,2001)
        self.assertEqual(g.slope.values[0,0],12);self.assertEqual(a['slope_per_year'],84)


if __name__=='__main__':unittest.main()
