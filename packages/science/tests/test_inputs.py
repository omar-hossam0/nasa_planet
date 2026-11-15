"""Scientific input tests: real contracts and intentionally broken fixtures."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import xarray as xr

SCIENCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCIENCE))
sys.path.insert(0, str(SCIENCE.parents[1] / "tools"))
from src.data_loader import (REPOSITORY, calendar_months, input_entry, load_cube,
                             monthly_precipitation_amount, validate_cube)
from audit_science_inputs import audit


class RealInputTests(unittest.TestCase):
    def test_current_twelve_cube_contracts(self):
        result = audit(REPOSITORY)
        self.assertEqual(result["scope_entries"], 12)
        self.assertEqual(result["issue_count"], 0)
        self.assertEqual(result["entries_without_contract_issues"], 12)

    def test_real_precipitation_loads_with_ancillary_fields(self):
        ds = load_cube("precipitation", "nile_corridor")
        self.assertEqual(ds.precipitation.shape, (288, 80, 40))
        self.assertEqual(ds.precipitation.attrs["units"], "mm/hr")
        self.assertIn("precipitationQualityIndex", ds)
        self.assertIn("randomError", ds)
        self.assertEqual(ds.attrs["inference_status"], "not_computed")
        amount = monthly_precipitation_amount(ds.precipitation)
        np.testing.assert_allclose(amount.isel(time=0), ds.precipitation.isel(time=0) * 31 * 24)
        np.testing.assert_allclose(amount.isel(time=37), ds.precipitation.isel(time=37) * 29 * 24)

    def test_all_products_load_without_changing_values(self):
        entries = json.loads((REPOSITORY / "docs/architecture/scope.v2.json").read_text())["entries"]
        for entry in entries:
            with self.subTest(variable=entry["variable_id"], region=entry["region_id"]):
                loaded = load_cube(entry["variable_id"], entry["region_id"])
                with xr.open_dataset(REPOSITORY / entry["cube_file"]) as source:
                    for name in source.data_vars:
                        np.testing.assert_array_equal(loaded[name].values, source[name].values)

    def test_ndvi_identity_is_explicit(self):
        entry = input_entry("vegetation_greenness", "nile_corridor")
        self.assertEqual(entry["source_variable"], "CMG_0_05_Deg_Monthly_NDVI")
        self.assertEqual(entry["cube_variable"], "NDVI")
        ds = load_cube("vegetation_greenness", "nile_corridor")
        self.assertEqual(ds.attrs["provider_variable"], entry["source_variable"])
        self.assertGreater(float(ds.NDVI.max()), 0.1)  # already scaled, not scaled twice

    def test_corrected_morocco_missing_values_remain_missing(self):
        ds = load_cube("soil_moisture", "morocco_comparison")
        values = ds.SoilMoi0_10cm_inst.values
        self.assertEqual(int(np.isnan(values).sum()), 32544)
        self.assertFalse(bool((values == -9999).any()))

    def test_unknown_pair_is_rejected(self):
        with self.assertRaises(ValueError):
            load_cube("unknown_variable", "nile_corridor")


class BrokenInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = load_cube("precipitation", "nile_corridor").isel(time=slice(0, 3), lat=slice(0, 2), lon=slice(0, 2))
        cls.entry = input_entry("precipitation", "nile_corridor")
        cls.entry["period"] = ["2001-01", "2001-03"]

    def test_gap_duplicate_and_reversed_time_are_rejected(self):
        for indices in ([0, 2], [0, 0, 2], [2, 1, 0]):
            with self.subTest(indices=indices), self.assertRaises(ValueError):
                validate_cube(self.valid.isel(time=indices), self.entry)

    def test_wrong_units_are_rejected(self):
        ds = self.valid.copy(deep=True)
        ds.precipitation.attrs["units"] = "mm"
        with self.assertRaises(ValueError):
            validate_cube(ds, self.entry)

    def test_missing_field_is_not_guessed(self):
        entry = copy.deepcopy(self.entry)
        entry["cube_variable"] = "invented_field"
        with self.assertRaises(ValueError):
            validate_cube(self.valid, entry)

    def test_missing_qa_field_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_cube(self.valid.drop_vars("randomError"), self.entry)

    def test_reversed_latitude_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_cube(self.valid.isel(lat=slice(None, None, -1)), self.entry)

    def test_out_of_bounds_coordinates_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_cube(self.valid.assign_coords(lat=[-70, -69]), self.entry)

    def test_cf_source_fill_is_decoded_without_becoming_zero(self):
        with tempfile.TemporaryDirectory(prefix="synthetic-input-fixture-") as temp:
            root = Path(temp)
            entry = copy.deepcopy(self.entry)
            entry.update({"period": ["2001-01", "2001-02"], "cube_file": "synthetic.nc"})
            (root / "docs/architecture").mkdir(parents=True)
            (root / "docs/architecture/scope.v2.json").write_text(json.dumps({"entries": [entry]}))
            shape = (2, 1, 1)
            ds = xr.Dataset({
                "precipitation": (("time", "lat", "lon"), np.array([1.0, -9999.0]).reshape(shape), {"units": "mm/hr"}),
                "precipitationQualityIndex": (("time", "lat", "lon"), np.ones(shape)),
                "randomError": (("time", "lat", "lon"), np.ones(shape)),
            }, coords={"time": np.array(["2001-01-01", "2001-02-01"], dtype="datetime64[D]"),
                       "lat": [25.0], "lon": [30.0]}, attrs={"product": "GPM_3IMERGM"})
            ds.to_netcdf(root / "synthetic.nc", encoding={"precipitation": {"_FillValue": -9999.0}})
            loaded = load_cube("precipitation", "nile_corridor", root=root)
            self.assertEqual(float(loaded.precipitation.values[0, 0, 0]), 1.0)
            self.assertTrue(np.isnan(loaded.precipitation.values[1, 0, 0]))
            self.assertTrue(np.isnan(monthly_precipitation_amount(loaded.precipitation).values[1, 0, 0]))


class RateConversionTests(unittest.TestCase):
    @staticmethod
    def rate(months, values):
        return xr.DataArray(values, dims="time", coords={"time": np.array(months, dtype="datetime64[D]")}, attrs={"units": "mm/hr"})

    def test_leap_and_nonleap_february(self):
        for year, expected in ((2000, 696), (2001, 672), (2004, 696)):
            with self.subTest(year=year):
                rate = self.rate([f"{year}-02-01"], [1.0])
                self.assertEqual(float(monthly_precipitation_amount(rate).item()), expected)

    def test_month_lengths_and_missing_values(self):
        rate = self.rate(["2001-01-01", "2001-02-01", "2001-03-01", "2001-04-01"], [1.0, 1.0, np.nan, 1.0])
        amount = monthly_precipitation_amount(rate)
        np.testing.assert_allclose(amount, [744, 672, np.nan, 720], equal_nan=True)
        self.assertEqual(amount.attrs["units"], "mm")
        self.assertEqual(rate.attrs["units"], "mm/hr")

    def test_wrong_units_and_invalid_rates_are_rejected(self):
        for month in ("2001-+1", "2001-1", "2001-13", "0000-01"):
            with self.subTest(month=month), self.assertRaises(ValueError):
                calendar_months(month, "2001-12")
        for value in (-1.0, np.inf):
            with self.subTest(value=value), self.assertRaises(ValueError):
                monthly_precipitation_amount(self.rate(["2001-01-01"], [value]))
        rate = self.rate(["2001-01-01"], [1.0])
        rate.attrs["units"] = "mm"
        with self.assertRaises(ValueError):
            monthly_precipitation_amount(rate)


if __name__ == "__main__":
    unittest.main()
