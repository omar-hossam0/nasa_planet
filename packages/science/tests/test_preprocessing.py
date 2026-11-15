"""Stage 2 checks use hand-calculated cases, not only generated outputs."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.data_loader import calendar_months, input_entry, load_cube, monthly_precipitation_amount
from src.preparation import prepare_registered, prepare_series
from src.preprocessing import (annual_summary, apply_product_qa, calendar_anomalies,
                               load_policy, policy_hash, select_period)
from src.regional_series import BoundingBox, cell_solid_angles, fixed_support_mean, select_bbox


def series(values, start="2001-01", units="K"):
    data = np.asarray(values, dtype="float64")
    if data.ndim == 1:
        dims, coords = ("time",), {}
    else:
        dims, coords = ("time", "lat", "lon"), {"lat": np.arange(data.shape[1]), "lon": np.arange(data.shape[2])}
    first = np.datetime64(start, "M")
    coords["time"] = (first + np.arange(data.shape[0])).astype("datetime64[ns]")
    return xr.DataArray(data, dims=dims, coords=coords, attrs={"units": units})


class GeographyTests(unittest.TestCase):
    def setUp(self):
        self.ds = xr.Dataset({"X": (("time", "lat", "lon"), np.zeros((1, 3, 3)))},
                             coords={"time": [np.datetime64("2001-01-01")], "lat": [0, 1, 2], "lon": [10, 11, 12]})
        self.supported = BoundingBox(9, -1, 13, 3)

    def test_bbox_inclusive_centres_and_order(self):
        result = select_bbox(self.ds, BoundingBox(10, 0, 11, 1), self.supported)
        np.testing.assert_array_equal(result.lat, [0, 1])
        np.testing.assert_array_equal(result.lon, [10, 11])

    def test_bad_bbox_values_rejected(self):
        for coords in [(12, 0, 10, 1), (10, 1, 11, 0), (170, 0, -170, 1),
                       (10, 0, 181, 1), (10, -91, 11, 1), (10, 0, np.nan, 1),
                       (True, 0, 11, 1), ("10", 0, 11, 1)]:
            with self.subTest(coords=coords), self.assertRaises(ValueError):
                BoundingBox(*coords)

    def test_outside_empty_reversed_and_wrapped_grids_rejected(self):
        for bbox in (BoundingBox(8, 0, 11, 1), BoundingBox(10.1, 0.1, 10.2, 0.2)):
            with self.assertRaises(ValueError):
                select_bbox(self.ds, bbox, self.supported)
        for ds in (self.ds.isel(lat=slice(None, None, -1)), self.ds.assign_coords(lon=[350, 351, 352])):
            with self.assertRaises(ValueError):
                select_bbox(ds, BoundingBox(10, 0, 11, 1), self.supported)

    def test_spherical_weights_match_hand_area_ratio(self):
        data = series(np.array([[[10.0], [20.0]]])).assign_coords(lat=[0.0, 60.0], lon=[0.0])
        weights = cell_solid_angles(data.lat, data.lon, (60.0, 1.0))
        self.assertAlmostEqual(float(weights.values[0, 0] / weights.values[1, 0]), 2.0)
        result = fixed_support_mean(data, weights)
        self.assertAlmostEqual(float(result.regional_monthly.item()), 40.0 / 3.0)
        self.assertAlmostEqual(float(result.normalized_support_weight.sum()), 1.0)

    def test_native_spacing_and_weight_alignment_rejected(self):
        lat, lon = self.ds.lat, self.ds.lon
        with self.assertRaises(ValueError):
            cell_solid_angles(lat, lon, (0.25, 1.0))
        data = self.ds.X
        weights = xr.DataArray(np.ones((3, 3)), dims=("lat", "lon"), coords={"lat": lat, "lon": [11, 12, 13]})
        with self.assertRaises(ValueError):
            fixed_support_mean(data, weights)


class QualityTests(unittest.TestCase):
    @staticmethod
    def modis(values, q, r):
        data = series(np.array(values, dtype="float64").reshape(1, 1, -1), units="1")
        return xr.Dataset({"NDVI": data, "VI_Quality": xr.DataArray(np.array(q).reshape(data.shape), dims=data.dims, coords=data.coords),
                           "pixel_reliability": xr.DataArray(np.array(r).reshape(data.shape), dims=data.dims, coords=data.coords)})

    def test_strict_and_standard_flags_and_cmg_high_bits(self):
        ds = self.modis([0.3] * 6, [0, 1, 2, 3, 0, 49152], [0, 1, 0, 0, 4, 0])
        entry = {"product_id": "MOD13C2", "cube_variable": "NDVI"}
        strict, _ = apply_product_qa(ds, entry, load_policy())
        np.testing.assert_array_equal(strict.qa_accepted.values.ravel(), [1, 0, 0, 0, 0, 1])
        policy = load_policy()
        policy["qa"]["modis_mode"] = "standard"
        standard, _ = apply_product_qa(ds, entry, policy)
        np.testing.assert_array_equal(standard.qa_accepted.values.ravel(), [1, 1, 0, 0, 0, 1])
        np.testing.assert_array_equal(ds.NDVI.values.ravel(), [0.3] * 6)

    def test_fill_nonintegral_flags_and_range_are_masked(self):
        ds = self.modis([0.3, 0.3, 0.3, 1.5, -0.3, np.nan, 0.3, 0.3],
                        [65535, np.nan, 0.5, 0, 0, 0, -1, 0], [0, 0, 0, 0, 0, 0, 0, 0.5])
        out, metadata = apply_product_qa(ds, {"product_id": "MOD13C2", "cube_variable": "NDVI"}, load_policy())
        self.assertEqual(int(out.NDVI.notnull().sum()), 0)
        self.assertEqual(metadata["accepted_values"], 0)

    def test_precip_quality_retained_without_unsupported_cutoff(self):
        data = series([0.0, 1.0, -9999.0, np.nan], units="mm/hr")
        ds = xr.Dataset({"precipitation": data, "precipitationQualityIndex": xr.zeros_like(data), "randomError": xr.ones_like(data)})
        out, metadata = apply_product_qa(ds, {"product_id": "GPM_3IMERGM", "cube_variable": "precipitation"}, load_policy())
        np.testing.assert_allclose(out.precipitation, [0, 1, np.nan, np.nan], equal_nan=True)
        np.testing.assert_array_equal(out.precipitationQualityIndex, ds.precipitationQualityIndex)
        self.assertFalse(metadata["ancillary_threshold_applied"])

    def test_soil_fill_and_zero_are_distinct(self):
        ds = xr.Dataset({"SoilMoi0_10cm_inst": series([-9999, 0, 1, np.inf], units="kg m-2")})
        out, _ = apply_product_qa(ds, {"product_id": "GLDAS_NOAH025_M", "cube_variable": "SoilMoi0_10cm_inst"}, load_policy())
        np.testing.assert_allclose(out.SoilMoi0_10cm_inst, [np.nan, 0, 1, np.nan], equal_nan=True)

    def test_policy_changes_cannot_be_silently_ignored(self):
        ds = xr.Dataset({"T2M": series([290.0])})
        for section, key, value in [("coverage", "annual_required_months", 6), ("qa", "imerg_quality_threshold", 50),
                                    ("spatial", "boundary_intersection", True)]:
            policy = load_policy()
            before = policy_hash(policy)
            policy[section][key] = value
            self.assertNotEqual(before, policy_hash(policy))
            with self.assertRaises(ValueError):
                apply_product_qa(ds, {"product_id": "M2TMNXSLV", "cube_variable": "T2M"}, policy)


class SupportTests(unittest.TestCase):
    def test_diagnostic_metadata_is_dimensionless(self):
        data = series(np.array([[[10.0, 20.0]], [[12.0, 22.0]]]))
        data.attrs["long_name"] = "air temperature"
        weights = xr.ones_like(data.isel(time=0, drop=True))
        weights.attrs = {"units": "sr", "long_name": "native cell area"}
        result = fixed_support_mean(data, weights)
        for field in ("fixed_support", "normalized_support_weight", "qa_valid_fraction_by_cell", "qa_valid_area_fraction_by_month"):
            with self.subTest(field=field):
                self.assertEqual(result[field].attrs["units"], "1")
                self.assertNotEqual(result[field].attrs.get("long_name"), "air temperature")
        self.assertEqual(result.native_cell_solid_angle.attrs["units"], "sr")
        self.assertEqual(result.regional_monthly.attrs["units"], "K")

    def test_fixed_support_prevents_composition_change(self):
        data = series(np.array([[[0.0, 10.0]], [[100.0, np.nan]]]))
        weights = xr.ones_like(data.isel(time=0, drop=True))
        result = fixed_support_mean(data, weights)
        np.testing.assert_allclose(result.regional_monthly, [0, 100])
        np.testing.assert_array_equal(result.fixed_support, [[1, 0]])
        np.testing.assert_allclose(result.qa_valid_area_fraction_by_month, [1, 0.5])

    def test_empty_support_has_nan_series_not_zero(self):
        data = series(np.array([[[0.0, np.nan]], [[np.nan, 10.0]]]))
        result = fixed_support_mean(data, xr.ones_like(data.isel(time=0, drop=True)))
        self.assertTrue(bool(result.regional_monthly.isnull().all()))
        self.assertEqual(int(result.fixed_support.sum()), 0)
        self.assertTrue(bool(result.normalized_support_weight.isnull().all()))

    def test_subperiod_does_not_change_reference_support(self):
        entry = input_entry("precipitation", "nile_corridor")
        ds = load_cube("precipitation", "nile_corridor").isel(time=slice(0, 24), lat=slice(0, 2), lon=slice(0, 2)).copy(deep=True)
        entry = copy.deepcopy(entry)
        entry["period"] = ["2001-01", "2002-12"]
        ds.precipitation.values[-1, 0, 0] = np.nan
        full, _ = prepare_series(ds, entry)
        short, _ = prepare_series(ds, entry, start_month="2001-01", end_month="2001-12")
        np.testing.assert_array_equal(full.fixed_support, short.fixed_support)
        self.assertEqual(int(short.fixed_support.values[0, 0]), 0)
        np.testing.assert_allclose(full.regional_monthly.values[:12], short.regional_monthly)
        with self.assertRaises(ValueError):
            prepare_series(ds, entry, start_month="")

    def test_preparation_with_no_fixed_support_reports_insufficient_data(self):
        values = series(np.full((12, 1, 1), np.nan), units="mm/hr").assign_coords(lat=[25.0], lon=[30.0])
        ds = xr.Dataset({"precipitation": values, "precipitationQualityIndex": xr.ones_like(values),
                         "randomError": xr.ones_like(values)}, attrs={"product": "GPM_3IMERGM"})
        entry = input_entry("precipitation", "nile_corridor")
        entry["period"] = ["2001-01", "2001-12"]
        prepared, meta = prepare_series(ds, entry)
        self.assertEqual(meta["preparation_state"], "insufficient_data")
        self.assertEqual(meta["eligible_fixed_support_cells"], 0)
        self.assertTrue(bool(prepared.regional_monthly.isnull().all()))
        self.assertTrue(bool(prepared.regional_annual.isnull().all()))


class TemporalTests(unittest.TestCase):
    def test_annual_rainfall_constant_rate_accounts_for_leap_days(self):
        rate = series(np.ones(48), start="1999-01", units="mm/hr")
        amount = monthly_precipitation_amount(rate)
        annual = annual_summary(amount, "precipitation")
        np.testing.assert_allclose(annual, [8760, 8784, 8760, 8760])
        np.testing.assert_array_equal(annual.year, [1999, 2000, 2001, 2002])
        self.assertEqual(annual.attrs["units"], "mm")

    def test_annual_mean_has_calendar_day_weights(self):
        values = [1.0] + [0.0] * 11
        for variable, units in [("air_temperature", "K"), ("soil_moisture", "kg m-2"), ("vegetation_greenness", "1")]:
            with self.subTest(variable=variable):
                result = annual_summary(series(values, units=units), variable)
                self.assertAlmostEqual(float(result.item()), 31.0 / 365.0)
                self.assertEqual(result.attrs["units"], units)

    def test_incomplete_and_missing_years_are_nan(self):
        values = np.ones(24)
        values[3] = np.nan
        result = annual_summary(series(values, units="mm"), "precipitation")
        self.assertTrue(np.isnan(result.values[0]))
        self.assertEqual(result.values[1], 12)
        partial = annual_summary(series(np.ones(10), start="2001-03", units="mm"), "precipitation")
        self.assertTrue(bool(partial.isnull().all()))
        with self.assertRaises(ValueError):
            annual_summary(series(np.ones(12), units="mm/hr"), "precipitation")
        with self.assertRaises(ValueError):
            annual_summary(series([np.inf] + [1.0] * 11), "air_temperature")
        with self.assertRaises(ValueError):
            annual_summary(series(np.ones(12), units="mm"), "air_temperature")

    def test_climatology_uses_calendar_labels_and_fixed_reference(self):
        reference = series(np.tile(np.arange(12), 2) + np.repeat([0, 2], 12))
        query = reference.isel(time=slice(2, 8))
        anomalies = calendar_anomalies(query, reference)
        np.testing.assert_allclose(anomalies, -np.ones(6))
        full = calendar_anomalies(reference, reference)
        np.testing.assert_allclose(full.groupby("time.month").mean(), np.zeros(12))

    def test_missing_baseline_season_stays_nan(self):
        reference = series(np.ones(24))
        reference.values[[1, 13]] = np.nan
        query = series(np.ones(12))
        anomalies = calendar_anomalies(query, reference)
        self.assertTrue(np.isnan(anomalies.values[1]))
        self.assertEqual(float(anomalies.values[0]), 0.0)

    def test_bad_period_and_gapped_months_rejected(self):
        data = series(np.ones(24))
        for start, end in [("2000-01", "2001-12"), ("2002-12", "2002-01"), ("2001-01", "2003-01")]:
            with self.assertRaises(ValueError):
                select_period(data, start, end)
        with self.assertRaises(ValueError):
            annual_summary(data.isel(time=[0, 2, 3]), "air_temperature")


class RealPreparationTests(unittest.TestCase):
    def test_real_nile_precipitation_is_prepared_without_inference(self):
        prepared, meta = prepare_registered("precipitation", "nile_corridor")
        self.assertEqual(meta["eligible_fixed_support_cells"], 3200)
        self.assertEqual(meta["regional_valid_annual_count"], 24)
        self.assertEqual(meta["inference_status"], "not_computed")
        self.assertEqual(meta["monthly_units"], "mm")
        np.testing.assert_allclose(prepared.regional_monthly_anomaly.groupby("time.month").mean(), 0, atol=1e-12)
        self.assertIn("randomError", prepared)


if __name__ == "__main__":
    unittest.main()
