"""Check annual completeness and distinguish temporal and spatial estimands."""
import unittest
import sys
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
from src.annual_coverage_review import annual_support_review
from review_sahel_ndvi_annual import month_records


class AnnualCoverageReviewTests(unittest.TestCase):
    def fixture(self, n=12, start="2004-01"):
        time = np.arange(np.datetime64(start), np.datetime64(start) + np.timedelta64(n, "M")).astype("datetime64[ns]")
        values = np.broadcast_to([.2, .8], (n, 1, 2)).copy()
        cells = xr.DataArray(values, dims=("time", "lat", "lon"),
                             coords={"time": time, "lat": [14.], "lon": [0., 1.]}, attrs={"units": "1"})
        weights = xr.DataArray([[1., 3.]], dims=("lat", "lon"), coords={"lat": cells.lat, "lon": cells.lon})
        eligible = xr.ones_like(weights, dtype="int8")
        return cells, weights, eligible

    def review(self, cells, weights, eligible):
        valid_area = weights.where(cells.notnull(), 0).sum(("lat", "lon"))
        region = (cells * weights).sum(("lat", "lon"), min_count=1) / valid_area.where(valid_area > 0)
        region.attrs["units"] = "1"
        return annual_support_review(cells, region, eligible, weights)

    def test_complete_year_estimands_match(self):
        cells, weights, eligible = self.fixture()
        result = self.review(cells, weights, eligible)
        np.testing.assert_allclose(result.regional_annual_from_monthly, [.65])
        np.testing.assert_allclose(result.regional_annual_complete_cell_years, [.65])
        np.testing.assert_array_equal(result.incomplete_eligible_cell_count, [0])

    def test_one_gap_stays_missing_and_changes_annual_interpretation(self):
        cells, weights, eligible = self.fixture()
        cells[1, 0, 1] = np.nan  # February in leap year 2004.
        result = self.review(cells, weights, eligible)
        self.assertTrue(np.isnan(result.cell_annual.values[0, 0, 1]))
        np.testing.assert_array_equal(result.valid_month_count_by_cell_year, [[[12, 11]]])
        np.testing.assert_array_equal(result.incomplete_eligible_cell_count, [1])
        np.testing.assert_allclose(result.regional_annual_from_monthly, [(.65 * (366 - 29) + .2 * 29) / 366])
        np.testing.assert_allclose(result.regional_annual_complete_cell_years, [.2])
        self.assertTrue(np.isnan(cells.values[1, 0, 1]))

    def test_no_complete_cells_is_missing_not_zero(self):
        cells, weights, eligible = self.fixture()
        cells[0, 0, 0] = np.nan
        cells[1, 0, 1] = np.nan
        result = self.review(cells, weights, eligible)
        self.assertTrue(bool(result.cell_annual.isnull().all()))
        self.assertTrue(bool(result.regional_annual_complete_cell_years.isnull().all()))
        self.assertTrue(bool(result.regional_annual_from_monthly.notnull().all()))

    def test_empty_month_and_partial_calendar_year_are_incomplete(self):
        cells, weights, eligible = self.fixture()
        cells[2] = np.nan
        result = self.review(cells, weights, eligible)
        self.assertTrue(bool(result.regional_annual_from_monthly.isnull().all()))
        partial = self.review(cells.isel(time=slice(0, 11)), weights, eligible)
        self.assertTrue(bool(partial.cell_annual.isnull().all()))
        self.assertTrue(bool(partial.regional_annual_from_monthly.isnull().all()))

    def test_ineligible_cells_are_separate_from_incomplete(self):
        cells, weights, eligible = self.fixture()
        eligible[0, 1] = 0
        cells[:, 0, 1] = np.nan
        result = self.review(cells, weights, eligible)
        np.testing.assert_array_equal(result.incomplete_eligible_cell_count, [0])
        np.testing.assert_allclose(result.complete_cell_area_fraction_selected, [.25])
        np.testing.assert_allclose(result.regional_annual_from_monthly, [.2])

    def test_bad_regional_series_or_weights_are_rejected(self):
        cells, weights, eligible = self.fixture()
        wrong = xr.zeros_like(cells[:, 0, 0])
        wrong.attrs["units"] = "1"
        with self.assertRaises(ValueError):
            annual_support_review(cells, wrong, eligible, weights)
        with self.assertRaises(ValueError):
            self.review(cells, weights * 0, eligible)

    def test_year_coverage_uses_only_that_years_months(self):
        cells, weights, eligible = self.fixture(n=24)
        cells[0, 0, 1] = np.nan
        a = self.review(cells, weights, eligible)
        region = (cells * weights).sum(("lat", "lon"), min_count=1) / weights.where(cells.notnull(), 0).sum(("lat", "lon"))
        ds = xr.Dataset({"cell_monthly": cells, "regional_monthly": region, "eligible": eligible})
        records = month_records(ds, a, weights)["annual"]
        self.assertEqual(records[0]["year"], 2004)
        self.assertEqual(records[1]["year"], 2005)
        self.assertAlmostEqual(records[0]["mean_monthly_valid_area_fraction_selected"], .9375)
        self.assertAlmostEqual(records[0]["minimum_monthly_valid_area_fraction_selected"], .25)
        self.assertAlmostEqual(records[1]["mean_monthly_valid_area_fraction_selected"], 1.)
        self.assertAlmostEqual(records[1]["minimum_monthly_valid_area_fraction_selected"], 1.)


if __name__ == "__main__":
    unittest.main()
