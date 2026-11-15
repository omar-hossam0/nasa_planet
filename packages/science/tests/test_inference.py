"""Experimental inference mechanics; empirical calibration is checked separately."""
import sys
import unittest
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, false_discovery_control

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.inference import adjust_fdr, annual_inference, circular_block_indices, wilson_interval
from src.trend_estimation import sen_slopes


class AnnualInferenceTests(unittest.TestCase):
    def series(self):
        rng = np.random.default_rng(43)
        return .06 * np.arange(24) + rng.normal(0, 1, 24), np.arange(2001, 2025)

    def test_seed_reproducibility_and_input_unchanged(self):
        y, years = self.series()
        original = y.copy()
        a = annual_inference(y, years, replicates=199, seed=18)
        b = annual_inference(y, years, replicates=199, seed=18)
        self.assertEqual(a, b)
        np.testing.assert_array_equal(y, original)
        self.assertEqual(a["status"], "candidate_diagnostic")
        self.assertFalse(a["application_release"])

    def test_complete_annual_admission_and_gaps_not_filled(self):
        y, years = self.series()
        y[3] = np.nan
        result = annual_inference(y, years)
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(result["n_valid"], 23)
        self.assertIsNone(result["p_value_candidate"])
        self.assertIsNone(result["interval_candidate"])
        self.assertTrue(np.isnan(y[3]))
        for count in (0, 1, 2, 19):
            self.assertEqual(annual_inference(np.arange(count), np.arange(2001, 2001 + count))["status"], "insufficient_data")

    def test_nonconsecutive_years_are_not_compressed(self):
        y, years = self.series()
        years[12:] += 1
        r = annual_inference(y, years)
        self.assertEqual(r["status"], "insufficient_data")
        self.assertIn("consecutive", r["reason"])

    def test_constant_and_perfect_line_do_not_imply_certain_intervals(self):
        years = np.arange(2001, 2025)
        self.assertEqual(annual_inference(np.ones(24), years)["status"], "no_variation")
        result = annual_inference(.05 * np.arange(24), years)
        self.assertEqual(result["status"], "no_residual_variation")
        self.assertIsNone(result["interval_candidate"])
        self.assertIsNone(result["p_value_candidate"])

    def test_basic_interval_and_tail_against_explicit_reconstruction(self):
        y, years = self.series()
        r = annual_inference(y, years, block_length=3, replicates=199, seed=62)
        t = np.arange(24)
        residual = y - r["slope_per_year"] * t
        residual -= np.median(residual)
        indices = circular_block_indices(24, 199, 3, np.random.default_rng(62))
        synthetic = r["slope_per_year"] * t[:, None] + residual[indices].T
        slopes = sen_slopes(synthetic, t)["slope"]
        error = slopes - r["slope_per_year"]
        low, high = np.quantile(error, [.025, .975])
        np.testing.assert_allclose(r["interval_candidate"], [r["slope_per_year"] - high, r["slope_per_year"] - low], atol=1e-14)
        p = (1 + (np.abs(error) >= abs(r["slope_per_year"])).sum()) / 200
        self.assertAlmostEqual(r["p_value_candidate"], p)

    def test_shift_and_scale_equivariance(self):
        y, years = self.series()
        a = annual_inference(y, years, replicates=199, seed=15)
        b = annual_inference(y * 10 + 273.15, years, replicates=199, seed=15)
        self.assertAlmostEqual(b["slope_per_year"], a["slope_per_year"] * 10)
        np.testing.assert_allclose(b["interval_candidate"], np.array(a["interval_candidate"]) * 10)
        self.assertEqual(b["p_value_candidate"], a["p_value_candidate"])

    def test_circular_blocks_have_correct_contiguity_and_range(self):
        indices = circular_block_indices(24, 200, 4, np.random.default_rng(1))
        self.assertEqual(indices.shape, (200, 24))
        self.assertTrue(((indices >= 0) & (indices < 24)).all())
        blocks = indices.reshape(200, 6, 4)
        np.testing.assert_array_equal(np.diff(blocks, axis=2) % 24, 1)
        self.assertTrue((np.diff(blocks, axis=2) == -23).any())

    def test_invalid_inputs_rejected(self):
        y, years = self.series()
        for kwargs in ({"replicates": 20}, {"block_length": 0}, {"block_length": 25}, {"confidence": 1.}, {"min_points": True}):
            with self.assertRaises(ValueError):
                annual_inference(y, years, **kwargs)
        y[0] = np.inf
        with self.assertRaises(ValueError):
            annual_inference(y, years)


class MultiplicityTests(unittest.TestCase):
    def test_hand_calculation_bh_and_by(self):
        values = [.001, .01, .03, .2]
        bh = adjust_fdr(values, method="BH")
        by = adjust_fdr(values, method="BY")
        np.testing.assert_allclose(bh["adjusted_p"], [.004, .02, .04, .2])
        np.testing.assert_allclose(by["adjusted_p"], np.array([.004, .02, .04, .2]) * (1 + 1/2 + 1/3 + 1/4))
        np.testing.assert_array_equal(bh["reject"], [1, 1, 1, 0])
        np.testing.assert_array_equal(by["reject"], [1, 1, 0, 0])

    def test_scipy_reference_random_ties_zero_one_and_missing(self):
        rng = np.random.default_rng(29)
        for n in (1, 2, 12, 200, 2000):
            for method in ("BH", "BY"):
                values = rng.uniform(size=n)
                if n > 2:
                    values[:3] = [0., 1., np.nan]
                if n > 12:
                    values[4:12] = .01
                good = np.isfinite(values)
                result = adjust_fdr(values, method=method)
                np.testing.assert_allclose(result["adjusted_p"][good], false_discovery_control(values[good], method=method.lower()), atol=1e-15)
                self.assertTrue(np.isnan(result["adjusted_p"][~good]).all())
                self.assertFalse(result["reject"][~good].any())

    def test_all_untested_is_not_a_family_of_zeros(self):
        result = adjust_fdr([np.nan, np.nan])
        self.assertEqual(result["tested_count"], 0)
        self.assertTrue(np.isnan(result["adjusted_p"]).all())
        self.assertFalse(result["reject"].any())

    def test_invalid_probabilities_and_settings_rejected(self):
        for p in ([-.1], [1.1], [np.inf]):
            with self.assertRaises(ValueError):
                adjust_fdr(p)
        with self.assertRaises(ValueError):
            adjust_fdr([.1], method="unknown")
        with self.assertRaises(ValueError):
            adjust_fdr([.1], q=0)

    def test_monte_carlo_wilson_intervals_match_scipy(self):
        for count in (0, 1, 25, 250, 500):
            expected = binomtest(count, 500).proportion_ci(confidence_level=.95, method="wilson")
            np.testing.assert_allclose(wilson_interval(count, 500), [expected.low, expected.high], atol=1e-14)


if __name__ == "__main__":
    unittest.main()
