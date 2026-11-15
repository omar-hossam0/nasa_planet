"""Actual NASA inputs and the existing descriptive science kernels. No inference."""

from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import threading

import numpy as np
import xarray as xr

from app.adapters.mock_nasa_data import MockNASADataAdapter
from app.adapters.interfaces import ComputedAnalysis, ComputedSpin
from app.core.exceptions import DataNotAvailableError, UnsupportedAggregationPolicyError
from app.schemas.common import ApiWarning, DataMode, EvidenceState, TrendDirection
from app.schemas.results import (
    DatasetRevision,
    MethodRef,
    TimeSeriesPoint,
    TrendSummary,
    VariableResult,
)
from app.schemas.spin import SpinWindow, SpinSummary

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from packages.science.src.data_loader import input_entry, load_cube
from packages.science.src.preparation import prepare_series
from packages.science.src.regional_series import BoundingBox
from packages.science.src.preprocessing import load_policy, policy_hash
from packages.science.src.trend_estimation import (
    annual_elapsed_years,
    cell_trends,
    trend_series,
)

METHOD = "descriptive-sen-strict-1.0"
DISCLAIMER = "Real NASA inputs; descriptive estimates only. Statistical inference is not released."
# netCDF/HDF5 readers are not guaranteed thread-safe. Bound local science I/O and
# memory; scale with worker processes, each maintaining its own lock.
SCIENCE_LOCK = threading.RLock()


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def direction(value):
    if value is None:
        return TrendDirection.insufficient_data
    return (
        TrendDirection.increasing
        if value > 0
        else TrendDirection.decreasing if value < 0 else TrendDirection.inconclusive
    )


def numbers(array):
    values = np.asarray(array, dtype=float)
    return np.where(np.isfinite(values), values, None).tolist()


class ScienceDataAdapter(MockNASADataAdapter):
    def __init__(self, regions_file=None):
        super().__init__(regions_file)
        self._entries = {}
        for region in self.list_regions():
            for variable in region.supported_variable_ids:
                try:
                    entry = input_entry(variable, region.region_id)
                except ValueError:
                    continue  # A registered rectangle does not create a dataset.
                if (ROOT / entry["cube_file"]).is_file():
                    self._entries[variable, region.region_id] = entry
        self._hashes = {
            key: sha(ROOT / entry["cube_file"]) for key, entry in self._entries.items()
        }
        self._policy_hash = policy_hash(load_policy())
        self._scope_hash = sha(ROOT / "docs/architecture/scope.v2.json")

    def get_variable(self, variable_id):
        record = super().get_variable(variable_id)
        if record is None:
            return None
        entries = [e for (v, _), e in self._entries.items() if v == variable_id]
        if not entries:
            return replace(
                record,
                app_available=False,
                demo_available=False,
                measurement_ready=False,
            )
        entry = entries[0]
        unit = "mm" if variable_id == "precipitation" else entry["cube_units"]
        return replace(
            record,
            unit=unit,
            units_verified=True,
            unit_source="validated NetCDF metadata and explicit science conversion",
            native_grid=None,
            lineage_note={
                "air_temperature": "MERRA-2 reanalysis, not direct satellite observations. Values retain kelvin; strict reference support applied.",
                "soil_moisture": "GLDAS land-surface model output for 0-10 cm, not atmospheric humidity. Strict reference support applied.",
                "precipitation": "GPM IMERG satellite/gauge retrieval. Source monthly mean rates are integrated to monthly mm; annual amounts sum twelve months.",
                "vegetation_greenness": "MODIS monthly NDVI with the existing strict product QA policy; no second scaling or missing-value reconstruction.",
            }[variable_id],
            limitations=(
                "Descriptive estimates only; inference is not released.",
                "Native cell centres select full cells; study rectangles are not national masks.",
                "The regional series describes retained reference QA support, not necessarily the whole rectangle.",
            ),
            coverage_start=min(e["period"][0] for e in entries),
            coverage_end=max(e["period"][1] for e in entries),
            display_name=(
                "Monthly precipitation amount"
                if variable_id == "precipitation"
                else record.display_name
            ),
            source_variable=entry["source_variable"],
            version=entry["version"],
            app_available=True,
            demo_available=False,
            measurement_ready=True,
            method_ready=False,
        )

    def list_variables(self):
        return [self.get_variable(v.variable_id) for v in super().list_variables()]

    def supported_region_ids(self, variable_id):
        return [
            r
            for r in super().supported_region_ids(variable_id)
            if (variable_id, r) in self._entries
        ]

    def dataset_revision(self, variable_id, region_id):
        return (
            self._hashes[variable_id, region_id]
            + ":"
            + self._policy_hash
            + ":"
            + self._region_revision
            + ":"
            + self._scope_hash
        )

    def registry_snapshot(self):
        return "science-inputs:" + self._scope_hash

    def ensure_available(self, spec):
        if spec.aggregation_policy.value != "area_weighted":
            raise UnsupportedAggregationPolicyError(
                spec.aggregation_policy.value, ["area_weighted"]
            )
        with SCIENCE_LOCK:
            for variable in spec.variable_ids:
                entry = self._entries.get((variable, spec.region_id))
                if not entry:
                    raise DataNotAvailableError(
                        "No registered input for this region-variable pair."
                    )
                w, s, e, n = entry["bbox"]
                box = spec.aoi
                if box.west < w or box.south < s or box.east > e or box.north > n:
                    raise DataNotAvailableError("AOI exceeds actual source coverage.")
                if (
                    spec.start_month < entry["period"][0]
                    or spec.end_month > entry["period"][1]
                ):
                    raise DataNotAvailableError(
                        "Period exceeds actual source coverage."
                    )
                with xr.open_dataset(
                    ROOT / entry["cube_file"], decode_times=False
                ) as ds:
                    if not np.any(
                        (ds.lat.values >= box.south) & (ds.lat.values <= box.north)
                    ) or not np.any(
                        (ds.lon.values >= box.west) & (ds.lon.values <= box.east)
                    ):
                        raise DataNotAvailableError(
                            "No native grid-cell centres fall inside the selected area."
                        )


class ScienceStatisticsAdapter:
    method_version = METHOD

    def __init__(self, data):
        self.data = data

    def prepare(self, spec, variable):
        if sha(ROOT / "docs/architecture/scope.v2.json") != self.data._scope_hash:
            raise DataNotAvailableError(
                "Input contract changed after startup; restart API and workers."
            )
        if policy_hash(load_policy()) != self.data._policy_hash:
            raise DataNotAvailableError(
                "Preparation policy changed after startup; restart API and workers."
            )
        entry = input_entry(variable, spec.region_id)
        if (
            sha(ROOT / entry["cube_file"])
            != self.data._hashes[variable, spec.region_id]
        ):
            raise DataNotAvailableError(
                "Source changed after startup; restart API and workers before analysis."
            )
        prepared, metadata = prepare_series(
            load_cube(variable, spec.region_id),
            entry,
            bbox=BoundingBox(*spec.aoi.canonical()),
            start_month=spec.start_month,
            end_month=spec.end_month,
        )
        return prepared, metadata

    def compute_analysis(self, spec, *, result_id):
        self.data.ensure_available(spec)
        variables, datasets, artifacts, warnings = [], [], {}, []
        with SCIENCE_LOCK:
            for variable in spec.variable_ids:
                prepared, metadata = self.prepare(spec, variable)
                annual = prepared.regional_annual
                trend = trend_series(annual.values, annual_elapsed_years(prepared.year))
                grid = cell_trends(prepared.cell_annual, frequency="annual")
                months = (
                    prepared.time.values.astype("datetime64[M]").astype(str).tolist()
                )
                values = numbers(prepared.regional_monthly.values)
                record = self.data.get_variable(variable)
                slope = trend["slope_per_year"]
                units = prepared.cell_annual.attrs["units"] + " per year"
                variables.append(
                    VariableResult(
                        variable_id=variable,
                        display_name=record.display_name,
                        unit=metadata["monthly_units"],
                        units_verified=True,
                        series=[
                            TimeSeriesPoint(month=m, value=v, missing=v is None)
                            for m, v in zip(months, values)
                        ],
                        trend=TrendSummary(
                            method_id="theil_sen",
                            method_version=METHOD,
                            direction=direction(slope),
                            slope_per_year=slope,
                            slope_unit=units,
                            n_months=sum(v is not None for v in values),
                            n_years=trend["n_valid"],
                            inference_status="not_computed",
                            evidence_state=EvidenceState.descriptive_only,
                            notes=[
                                "Annual Theil–Sen estimate on actual elapsed years. Descriptive only.",
                                metadata["annual_aggregation"],
                                *metadata["warnings"],
                            ],
                        ),
                    )
                )
                entry = self.data._entries[variable, spec.region_id]
                datasets.append(
                    DatasetRevision(
                        variable_id=variable,
                        product_id=entry["product_id"],
                        version=entry["version"],
                        source_variable=entry["source_variable"],
                        revision=self.data.dataset_revision(variable, spec.region_id),
                        source="NASA NetCDF; source SHA256 in revision",
                    )
                )
                finite = np.isfinite(grid.slope.values)
                artifacts[variable] = {
                    "metadata": metadata,
                    "lat": prepared.lat.values.tolist(),
                    "lon": prepared.lon.values.tolist(),
                    "native_spacing_degrees": list(
                        load_policy()["spatial"]["native_spacing_degrees"][
                            entry["product_id"]
                        ]
                    ),
                    "annual_slope": numbers(grid.slope.values),
                    "eligible": prepared.fixed_support.values.astype(bool).tolist(),
                    "annual_years": prepared.year.values.tolist(),
                    "regional_annual": numbers(annual.values),
                    "positive_cells": int((finite & (grid.slope.values > 0)).sum()),
                    "negative_cells": int((finite & (grid.slope.values < 0)).sum()),
                    'zero_cells': int((finite & (grid.slope.values == 0)).sum()),
                    'unavailable_eligible_cells': int((~finite & prepared.fixed_support.values.astype(bool)).sum()),
                    "source_file": entry["cube_file"],
                    "source_sha256": self.data._hashes[variable, spec.region_id],
                    "preparation_policy_sha256": self.data._policy_hash,
                }
                warnings.extend(
                    ApiWarning(code="SCIENCE_LIMITATION", message=message)
                    for message in metadata["warnings"]
                )
        return ComputedAnalysis(
            variables=variables,
            datasets=datasets,
            warnings=warnings,
            science=artifacts,
            method=MethodRef(
                method_id="theil_sen",
                method_version=METHOD,
                aggregation_policy=spec.aggregation_policy,
                status="descriptive_only_inference_withheld",
                approved=False,
                note=DISCLAIMER,
            ),
        )

    def compute_spin(self, spec, *, result_id, request):
        with SCIENCE_LOCK:
            p, _ = self.prepare(spec, spec.variable_ids[0])
            windows = []
            low = request.start_year_min or int(spec.start_month[:4])
            high = request.end_year_max or int(spec.end_month[:4])
            for year in range(low, high - request.minimum_window_years + 2):
                end = year + request.minimum_window_years - 1
                series = p.regional_annual.sel(year=slice(year, end))
                trend = trend_series(series.values, annual_elapsed_years(series.year))
                value = trend["slope_per_year"]
                windows.append(
                    SpinWindow(
                        window_id=f"window_{year}_{end}",
                        start_month=f"{year}-01",
                        end_month=f"{end}-12",
                        years=request.minimum_window_years,
                        trend_value=value,
                        direction=direction(value),
                        evidence_state=EvidenceState.descriptive_only,
                    )
                )
            values = [w.trend_value for w in windows if w.trend_value is not None]
            return ComputedSpin(
                windows=windows,
                summary=SpinSummary(
                    window_count=len(windows),
                    min_trend=min(values) if values else None,
                    max_trend=max(values) if values else None,
                    mean_trend=float(np.mean(values)) if values else None,
                    sign_agreement_share=None,
                    note="Recomputed on fixed reference QA support; descriptive only, no calibrated uncertainty.",
                ),
                warnings=[],
            )
