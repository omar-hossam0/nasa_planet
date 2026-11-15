"""Descriptive slope validation, independent references and inherited regressions."""
import json
from fractions import Fraction
from pathlib import Path
import statistics
import sys
import unittest

import numpy as np
import xarray as xr
from scipy.stats.mstats import sen_seasonal_slopes

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.preprocessing import annual_summary
from src.trend_estimation import (annual_elapsed_years, cell_trends,
                                 monthly_elapsed_years, sen_slopes, trend_series)


def scipy_slope_only(values, samples_per_year):
    """One column yields the ordinary Sen slope; no interval/test is computed.

    Retain masked rows to preserve their original time distances. For regular
    calendar samples convert the reference's per-row slope to per-year units.
    """
    values = np.asarray(values, dtype="float64")
    masked = np.ma.masked_invalid(values[:, None])
    return float(sen_seasonal_slopes(masked).intra_slope[0]) * samples_per_year


class TimeAxisTests(unittest.TestCase):
    def test_monthly_calendar_distances_and_leap_year(self):
        t = monthly_elapsed_years(["2000-01", "2000-02", "2000-03", "2001-01"])
        np.testing.assert_allclose(t, [0, 1 / 12, 2 / 12, 1])

    def test_annual_missing_labels_do_not_compress_time(self):
        np.testing.assert_allclose(annual_elapsed_years([2001, 2003, 2008]), [0, 2, 7])

    def test_source_submonth_clock_offsets_are_aggregate_labels(self):
        values = np.array(["2001-01-01T00:30", "2001-02-15T12:00"], dtype="datetime64[m]")
        np.testing.assert_allclose(monthly_elapsed_years(values), [0, 1 / 12])

    def test_invalid_month_axes_rejected(self):
        for values in (["2001-01", "2001-01"], ["2001-02", "2001-01"], ["2001-13"],
                       ["not-a-month"], [2001, 2002], np.array(["NaT"], dtype="datetime64[M]")):
            with self.subTest(values=str(values)), self.assertRaises(ValueError):
                monthly_elapsed_years(values)

    def test_invalid_annual_axes_rejected(self):
        for values in ([2001, 2001], [2002, 2001], [2001.5], [np.nan], [True], ["2001"]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                annual_elapsed_years(values)


class SlopeTests(unittest.TestCase):
    def test_increasing_decreasing_constant_monthly_and_annual(self):
        for scale, t in ((12, np.arange(288) / 12), (1, np.arange(24))):
            for slope in (2., -1.25, 0.):
                values = 7 + slope * t
                with self.subTest(scale=scale, slope=slope):
                    result = trend_series(values, t)
                    self.assertAlmostEqual(result["slope_per_year"], slope)
                    self.assertAlmostEqual(result["slope_per_year"], scipy_slope_only(values, scale))

    def test_hand_calculated_median_and_tied_values(self):
        # Six pair slopes: 1, 2.5, 2, 4, 2.5, 1; median 2.25.
        self.assertEqual(trend_series([0, 1, 5, 6], [0, 1, 2, 3])["slope_per_year"], 2.25)
        self.assertEqual(trend_series([3, 3, 3, 3], [0, 1, 4, 8])["slope_per_year"], 0)

    def test_rational_reference_for_irregular_times_and_outlier(self):
        times, values = [0, 1, 3, 6, 10], [2, 4, 9, 100, 23]
        reference = statistics.median([Fraction(values[j] - values[i], times[j] - times[i])
                                       for i in range(5) for j in range(i + 1, 5)])
        self.assertAlmostEqual(trend_series(values, times)["slope_per_year"], float(reference))

    def test_missing_values_keep_original_time_distances(self):
        values = np.arange(36, dtype=float) / 12
        values[[0, 2, 3, 12, 20, 35]] = np.nan
        result = trend_series(values, np.arange(36) / 12)
        self.assertAlmostEqual(result["slope_per_year"], 1.)
        self.assertAlmostEqual(result["slope_per_year"], scipy_slope_only(values, 12))
        self.assertEqual(result["n_valid"], 30)
        self.assertAlmostEqual(result["valid_span_years"], 33 / 12)

    def test_short_empty_all_missing_are_insufficient(self):
        for values in ([], [1.], [1., 2.], [np.nan] * 20):
            result = trend_series(values, np.arange(len(values), dtype=float))
            self.assertEqual(result["status"], "insufficient_data")
            self.assertIsNone(result["slope_per_year"])
            json.dumps(result, allow_nan=False)
        # Two-point computation is available only through an explicit guard.
        self.assertEqual(trend_series([1., 3.], [0., 1.], min_points=2)["slope_per_year"], 2.)

    def test_random_reference_with_seasonality_outliers_and_gaps(self):
        rng = np.random.default_rng(831)
        t = np.arange(120) / 12
        for k in range(6):
            values = .03 * t + np.sin(2 * np.pi * t) + rng.normal(0, .2, len(t))
            values[k] += 20
            values[rng.choice(len(t), 15, replace=False)] = np.nan
            self.assertAlmostEqual(trend_series(values, t)["slope_per_year"], scipy_slope_only(values, 12), places=12)

    def test_known_trend_with_large_repeating_seasonal_cycle(self):
        t = np.arange(288) / 12
        for slope in (0., 1., -.3):
            values = 10 * np.sin(2 * np.pi * t) + slope * t
            self.assertAlmostEqual(trend_series(values, t)["slope_per_year"], slope, places=12)

    def test_invalid_inputs_are_errors_not_insufficient_data(self):
        for time in ([0, 0, 1], [0, 2, 1], [0, np.nan, 1], [0, np.inf, 1]):
            with self.assertRaises(ValueError):
                trend_series([1., 2., 3.], time)
        with self.assertRaises(ValueError):
            trend_series([1, np.inf, 3], [0, 1, 2])
        with self.assertRaises(ValueError):
            trend_series([[1, 2], [3, 4]], [0, 1])
        with self.assertRaises(ValueError):
            trend_series([1, 2, 3], [0, 1])
        for minimum in (True, 1, 2.5):
            with self.assertRaises(ValueError):
                trend_series([1, 2, 3], [0, 1, 2], min_points=minimum)

    def test_time_axis_is_mandatory(self):
        with self.assertRaises(TypeError):
            trend_series([1, 2, 3])

    def test_offset_invariance_and_units_scaling(self):
        time = np.arange(10, dtype=float)
        values = np.array([2, 5, 4, 8, 3, 9, 9, 10, 13, 15.])
        a = trend_series(values, time)["slope_per_year"]
        self.assertAlmostEqual(trend_series(values - 273.15, time + 2001)["slope_per_year"], a)
        self.assertAlmostEqual(trend_series(values * 10, time)["slope_per_year"], a * 10)

    def test_no_inference_fields(self):
        result = trend_series([1, 3, 4], [0, 1, 2])
        for field in ("p_value", "ci_low", "ci_high", "significant", "classification"):
            self.assertNotIn(field, result)
        self.assertEqual(result["inference_status"], "not_computed")


class SharedKernelRegressionTests(unittest.TestCase):
    def cube(self, values, years=False):
        n = len(values)
        dim = "year" if years else "time"
        coord = np.arange(2001, 2001 + n) if years else np.arange(np.datetime64("2001-01"), np.datetime64("2001-01") + np.timedelta64(n, "M")).astype("datetime64[ns]")
        return xr.DataArray(np.asarray(values)[:, None, None], dims=(dim, "lat", "lon"),
                            coords={dim: coord, "lat": [14.], "lon": [0.]}, attrs={"units": "1"})

    def test_factor_of_twelve_annual_regression(self):
        cells = self.cube(np.arange(288) / 12)
        annual = annual_summary(cells, "vegetation_greenness")
        # Leap-year day weights slightly alter annual intercepts, not by 12x.
        raw = self.cube(np.arange(24), years=True)
        grid = cell_trends(raw, frequency="annual")
        self.assertAlmostEqual(grid.slope.item(), 1.)
        self.assertAlmostEqual(trend_series(raw.values[:, 0, 0], annual_elapsed_years(raw.year))["slope_per_year"], 1.)
        expected = scipy_slope_only(annual.values[:, 0, 0], 1)
        self.assertAlmostEqual(cell_trends(annual, frequency="annual").slope.item(), expected)
        self.assertLess(abs(expected - 1), .001)

    def test_48_month_guard_same_in_region_and_grid(self):
        values = np.arange(48) / 12
        cells = self.cube(values)
        region = trend_series(values, monthly_elapsed_years(cells.time), min_points=60)
        grid = cell_trends(cells, frequency="monthly", min_points=60)
        self.assertEqual(region["status"], "insufficient_data")
        self.assertFalse(bool(grid.computable))
        self.assertTrue(np.isnan(grid.slope.item()))

    def test_grid_scalar_parity_with_variable_missingness(self):
        rng = np.random.default_rng(38)
        values = rng.normal(size=(36, 2, 3))
        values[::3, 0, 1] = np.nan
        values[:, 1, 0] = np.nan
        values[:-2, 1, 1] = np.nan
        values[:, 1, 2] = 4
        result = sen_slopes(values, np.arange(36) / 12, batch_size=1)
        batched = sen_slopes(values, np.arange(36) / 12, batch_size=64)
        np.testing.assert_array_equal(result["slope"], batched["slope"])
        for i in range(2):
            for j in range(3):
                scalar = trend_series(values[:, i, j], np.arange(36) / 12)
                self.assertEqual(scalar["n_valid"], result["n_valid"][i, j])
                if scalar["slope_per_year"] is None:
                    self.assertTrue(np.isnan(result["slope"][i, j]))
                else:
                    self.assertEqual(scalar["slope_per_year"], result["slope"][i, j])

    def test_incomplete_cell_year_remains_missing_in_annual_trend(self):
        cells = self.cube(np.arange(60, dtype=float) / 12)
        cells[2] = np.nan
        annual = annual_summary(cells, "vegetation_greenness")
        self.assertTrue(np.isnan(annual.values[0, 0, 0]))
        result = cell_trends(annual, frequency="annual")
        self.assertEqual(result.n_valid.item(), 4)
        self.assertAlmostEqual(result.valid_span_years.item(), 3.)

    def test_regional_slope_is_not_average_of_cell_slopes(self):
        values = np.array([[7, 12], [6, 13], [17, 12], [2, 12], [2, 7]], dtype=float)
        cells = sen_slopes(values, np.arange(5))["slope"]
        region = trend_series(values.mean(axis=1), np.arange(5))["slope_per_year"]
        self.assertNotEqual(region, float(cells.mean()))


if __name__ == "__main__":
    unittest.main()
