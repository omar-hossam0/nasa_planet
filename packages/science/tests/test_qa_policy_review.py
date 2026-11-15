"""Controlled tests for relaxed coverage, gaps and MOD13C2-specific flags."""
import unittest

import numpy as np
import xarray as xr

from src.qa_policy_review import coverage_experiment, decode_cmg_quality, missingness_groups


class CoverageReviewTests(unittest.TestCase):
    def fixture(self, values):
        values = np.asarray(values, dtype=float)
        ntime, nlon = values.shape
        time = np.arange(np.datetime64("2001-01"), np.datetime64("2001-01") + np.timedelta64(ntime, "M")).astype("datetime64[ns]")
        data = xr.DataArray(values[:, None, :], dims=("time", "lat", "lon"),
                            coords={"time": time, "lat": [14.], "lon": np.arange(nlon)}, attrs={"units": "1"})
        weights = xr.DataArray(np.arange(1, nlon + 1, dtype=float)[None, :], dims=("lat", "lon"),
                               coords={"lat": data.lat, "lon": data.lon})
        return data, weights

    def test_288_month_integer_boundaries(self):
        values = np.ones((288, 5))
        for column, missing in enumerate((0, 14, 15, 28, 29)):
            values[:missing, column] = np.nan
        data, weights = self.fixture(values)
        a = coverage_experiment(data, weights, .95)
        b = coverage_experiment(data, weights, .90)
        self.assertEqual(a.attrs["required_valid_reference_months"], 274)
        self.assertEqual(b.attrs["required_valid_reference_months"], 260)
        np.testing.assert_array_equal(a.eligible_support, [[1, 1, 0, 0, 0]])
        np.testing.assert_array_equal(b.eligible_support, [[1, 1, 1, 1, 0]])

    def test_observed_weights_renormalize_without_filling(self):
        data, weights = self.fixture([[.1, np.nan], [.1, .4], [.1, .4], [.1, .4]])
        out = coverage_experiment(data, weights, .75)
        np.testing.assert_allclose(out.regional_monthly, [.1, .3, .3, .3])
        self.assertTrue(np.isnan(out.cell_monthly.values[0, 0, 1]))
        np.testing.assert_allclose(out.observed_area_fraction_eligible, [1 / 3, 1, 1, 1])
        np.testing.assert_allclose(out.normalized_observed_weight.sum(("lat", "lon")), 1)
        np.testing.assert_array_equal(np.isfinite(out.cell_monthly), np.isfinite(data))

    def test_no_observations_produce_nan_not_zero(self):
        data, weights = self.fixture([[np.nan, np.nan], [.1, .3]])
        out = coverage_experiment(data, weights, .5)
        self.assertTrue(np.isnan(out.regional_monthly.values[0]))
        np.testing.assert_allclose(out.regional_monthly.values[1], (.1 + 2 * .3) / 3)
        self.assertTrue(bool(out.normalized_observed_weight.isel(time=0).isnull().all()))
        empty = coverage_experiment(data, weights, 1)
        self.assertTrue(bool(empty.regional_monthly.isnull().all()))
        self.assertTrue(bool(empty.observed_area_fraction_eligible.isnull().all()))

    def test_missingness_count_and_area_denominators(self):
        data, weights = self.fixture([[.1, np.nan], [.1, .4], [.1, .4], [.1, .4]])
        out = coverage_experiment(data, weights, .75)
        grouped = missingness_groups(out.observed_support.values, out.eligible_support.values, weights.values, data.time.dt.month.values)
        djf = grouped["season"]["DJF"]
        self.assertEqual(djf["month_count"], 2)
        self.assertEqual(djf["eligible_cell_months"], 4)
        self.assertEqual(djf["missing_cell_months"], 1)
        self.assertAlmostEqual(djf["missing_cell_month_fraction"], .25)
        self.assertAlmostEqual(djf["missing_area_time_fraction"], 1 / 3)
        self.assertEqual(grouped["calendar_month"]["1"]["eligible_cells_with_no_observations_in_group"], 1)
        self.assertIsNone(grouped["season"]["SON"]["missing_area_time_fraction"])

    def test_thresholds_and_bad_inputs_rejected(self):
        data, weights = self.fixture([[.1, .2], [.1, .2]])
        for threshold in (0, -1, 1.01, float("nan"), True):
            with self.assertRaises(ValueError):
                coverage_experiment(data, weights, threshold)
        with self.assertRaises(ValueError):
            coverage_experiment(data, weights * 0, .9)
        with self.assertRaises(ValueError):
            coverage_experiment(data.isel(time=[1, 0]), weights, .9)
        data[0, 0, 0] = np.inf
        with self.assertRaises(ValueError):
            coverage_experiment(data, weights, .9)

    def test_cmg_high_bits_and_fill_do_not_become_snow_or_good_data(self):
        # CMG >75% finer-pixel contribution, marginal, usefulness 9, high aerosol,
        # adjacent cloud, mixed cloud and land: a deliberately auditable word.
        word = (3 << 14) | (1 << 11) | (1 << 10) | (1 << 8) | (3 << 6) | (9 << 2) | 1
        fields = decode_cmg_quality(np.array([word, 65535, -1, np.nan, 1.5]))
        for key, expected in {"cmg_geospatial": 3, "land_water": 1, "mixed_cloud": 1,
                              "adjacent_cloud": 1, "aerosol": 3, "usefulness": 9, "modland": 1}.items():
            self.assertEqual(fields[key][0], expected)
            np.testing.assert_array_equal(fields[key][1:], -1)
        self.assertNotIn("snow", fields)
        self.assertNotIn("shadow", fields)


if __name__ == "__main__":
    unittest.main()
