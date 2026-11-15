import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
NASA_DIR = ROOT / "data" / "nasa"
MEASUREMENT_DIR = NASA_DIR / "measurements"
REPORT_PATH = ROOT / "tests" / "qa_audit_cubes_report.json"

PRODUCTS = {
    "M2TMNXSLV": {
        "variable": "T2M",
        "regions": ["Nile", "Morocco", "Sahel"],
        "expected_range": (180.0, 350.0),
    },
    "GLDAS_NOAH025_M": {
        "variable": "SoilMoi0_10cm_inst",
        "regions": ["Nile", "Morocco", "Sahel"],
        "expected_range": (0.0, 1000.0),
    },
    "GPM_3IMERGM": {
        "variable": "precipitation",
        "regions": ["Nile", "Morocco", "Sahel"],
        "expected_range": (0.0, 10.0),
    },
    "MOD13C2": {
        "variable": "NDVI",
        "regions": ["Nile", "Morocco", "Sahel"],
        "expected_range": (-0.2, 1.0),
    },
}

EXPECTED_MONTHS = []
start_year, start_month = 2001, 1
end_year, end_month = 2024, 12
current_year, current_month = start_year, start_month
while (current_year, current_month) <= (end_year, end_month):
    EXPECTED_MONTHS.append(f"{current_year:04d}-{current_month:02d}")
    if current_month == 12:
        current_year += 1
        current_month = 1
    else:
        current_month += 1


def find_coord_key(ds, names):
    for name in names:
        if name in ds.coords:
            return name
    for key in ds.coords:
        key_lower = key.lower()
        for candidate in names:
            if candidate.lower() in key_lower:
                return key
    return None


def to_month_strings(time_values):
    month_strings = []
    for value in np.asarray(time_values):
        try:
            if hasattr(value, "to_datetime64"):
                value = value.to_datetime64()
        except Exception:
            pass
        if hasattr(value, "astype"):
            try:
                dt_value = np.datetime_as_string(value, unit="M")
                if isinstance(dt_value, bytes):
                    dt_value = dt_value.decode("utf-8")
                month_strings.append(dt_value[:7])
                continue
            except Exception:
                pass
        try:
            if isinstance(value, str):
                month_strings.append(value[:7])
                continue
            month_strings.append(np.datetime_as_string(np.asarray(value), unit="M")[:7])
        except Exception:
            try:
                month_strings.append(str(value)[:7])
            except Exception:
                month_strings.append("unknown")
    return month_strings


def compute_month_sequence_problems(ds, time_name):
    problems = []
    if time_name is None:
        return ["Missing time coordinate."]

    time_values = ds[time_name].values
    if len(time_values) != 288:
        problems.append(
            "Time length mismatch: expected 288 months, found "
            f"{len(time_values)}."
        )

    month_strings = to_month_strings(time_values)
    unique_count = len(set(month_strings))
    if unique_count != len(month_strings):
        problems.append("Time coordinate contains duplicate month values.")

    expected_sequence = EXPECTED_MONTHS[: len(month_strings)]
    if month_strings and month_strings != expected_sequence:
        problems.append(
            "Time coordinate does not match the expected 2001-01 through "
            "2024-12 sequence."
        )

    if len(time_values) > 1:
        try:
            normalized = np.asarray(time_values)
            if np.any(np.diff(normalized) <= 0):
                problems.append(
                    "Time coordinate is not strictly increasing across the "
                    "monthly sequence."
                )
        except Exception:
            pass

    return problems


def get_spatial_axis_order(ds, var_name):
    dims = tuple(ds[var_name].dims)
    lat_name = find_coord_key(ds, ["lat", "latitude"])
    lon_name = find_coord_key(ds, ["lon", "longitude"])
    if lat_name is None or lon_name is None:
        return "unknown"
    if lat_name in dims and lon_name in dims:
        if dims.index(lat_name) < dims.index(lon_name):
            return "lat/lon"
        return "lon/lat"
    return "unknown"


def check_coordinate_order(ds, var_name):
    warnings = []
    lat_name = find_coord_key(ds, ["lat", "latitude"])
    lon_name = find_coord_key(ds, ["lon", "longitude"])
    if lat_name is None or lon_name is None:
        return warnings

    lat_values = np.asarray(ds[lat_name].values)
    lon_values = np.asarray(ds[lon_name].values)

    if lat_values.size > 1:
        lat_diff = np.diff(lat_values)
        if not np.all(lat_diff >= 0) and not np.all(lat_diff <= 0):
            warnings.append(
                "Latitude coordinate is not monotonic; verify the native grid "
                "orientation before aggregation."
            )

    if lon_values.size > 1 and np.any(np.diff(lon_values) < 0):
        warnings.append(
            "Longitude is not increasing across the grid; verify the "
            "coordinate order or wrap handling."
        )

    if ds[var_name].ndim >= 2:
        spatial_order = get_spatial_axis_order(ds, var_name)
        if spatial_order == "lat/lon":
            warnings.append(
                "Native grid dimension order is lat/lon; this is acceptable "
                "when the downstream code explicitly handles it, but the "
                "regional analysis must not assume lon/lat without checking."
            )

    return warnings


def check_value_ranges(ds, product_name, variable_name):
    problems = []
    if variable_name not in ds.data_vars:
        return [f"Expected variable {variable_name} is missing."]

    values = np.asarray(ds[variable_name].values)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return [f"Variable {variable_name} contains no finite values."]

    min_value = float(finite.min())
    max_value = float(finite.max())
    lower_bound, upper_bound = {
        "M2TMNXSLV": (180.0, 350.0),
        "GLDAS_NOAH025_M": (0.0, 1000.0),
        "GPM_3IMERGM": (0.0, 10.0),
        "MOD13C2": (-0.2, 1.0),
    }.get(product_name, (-1e12, 1e12))

    if min_value < lower_bound or max_value > upper_bound:
        problems.append(
            f"Variable {variable_name} exceeds the expected physical range: "
            f"[{min_value}, {max_value}] outside [{lower_bound}, "
            f"{upper_bound}]."
        )

    if product_name == "MOD13C2" and "pixel_reliability" in ds.data_vars:
        rel = np.asarray(ds["pixel_reliability"].values)
        good_mask = np.isin(rel, [0, 1])
        if good_mask.size > 0:
            ratio = float(good_mask.mean())
            if ratio < 0.5:
                problems.append(
                    "MODIS QA mask ratio is low: "
                    f"{ratio:.3f} of cells are marked good or marginal."
                )

    if product_name == "GLDAS_NOAH025_M":
        suspicious_fills = values[(values <= -999.0) & np.isfinite(values)]
        if suspicious_fills.size > 0:
            problems.append(
                "Variable "
                f"{variable_name} still contains suspicious fill values "
                f"below -999: {suspicious_fills.size} cells."
            )

    if product_name == "MOD13C2":
        fill_values = values[(values <= -3000.0) & np.isfinite(values)]
        if fill_values.size > 0:
            problems.append(
                f"Variable {variable_name} contains MODIS fill values below "
                f"-3000: {fill_values.size} cells."
            )

    return problems


def expected_file_manifest():
    manifest = {}
    for product_name, config in PRODUCTS.items():
        for region in config["regions"]:
            file_name = f"{product_name}_{region}_2001_2024.nc"
            manifest[file_name] = {
                "product": product_name,
                "variable": config["variable"],
                "region": region,
            }
    return manifest


EXPECTED_FILES = expected_file_manifest()


def audit_one_cube(file_path):
    product_name = None
    region_name = None
    variable_name = None
    for item_name, payload in EXPECTED_FILES.items():
        if file_path.name == item_name:
            product_name = payload["product"]
            region_name = payload["region"]
            variable_name = payload["variable"]
            break

    result = {
        "file": str(file_path.relative_to(ROOT)),
        "product": product_name,
        "region": region_name,
        "variable": variable_name,
        "status": "pass",
        "errors": [],
        "warnings": [],
        "checks": {},
    }

    try:
        ds = xr.open_dataset(file_path)
    except Exception as exc:
        result["status"] = "fail"
        result["errors"].append(f"Unable to open dataset: {exc}")
        return result

    try:
        time_name = find_coord_key(ds, ["time"])
        lat_name = find_coord_key(ds, ["lat", "latitude"])
        lon_name = find_coord_key(ds, ["lon", "longitude"])
        result["checks"]["time_coord"] = time_name
        result["checks"]["lat_coord"] = lat_name
        result["checks"]["lon_coord"] = lon_name

        if time_name is not None:
            month_strings = to_month_strings(ds[time_name].values)
            result["checks"]["month_count"] = len(month_strings)
            result["checks"]["unique_month_count"] = len(set(month_strings))
            result["checks"]["first_month"] = (
                month_strings[0] if month_strings else None
            )
            result["checks"]["last_month"] = (
                month_strings[-1] if month_strings else None
            )
            result["errors"].extend(
                compute_month_sequence_problems(ds, time_name)
            )

        if lat_name is not None and lon_name is not None:
            lat_values = np.asarray(ds[lat_name].values)
            lon_values = np.asarray(ds[lon_name].values)
            result["checks"]["lat_extent"] = [
                float(np.min(lat_values)),
                float(np.max(lat_values)),
            ]
            result["checks"]["lon_extent"] = [
                float(np.min(lon_values)),
                float(np.max(lon_values)),
            ]
            result["checks"]["native_spatial_axis_order"] = (
                get_spatial_axis_order(ds, variable_name)
                if variable_name in ds.data_vars
                else "unknown"
            )
            result["warnings"].extend(
                check_coordinate_order(ds, variable_name)
            )

        if product_name is not None and variable_name is not None:
            result["errors"].extend(
                check_value_ranges(ds, product_name, variable_name)
            )

        for var_name in ds.data_vars:
            if var_name.lower() in {"time_bnds", "lat_bnds", "lon_bnds"}:
                continue
            arr = np.asarray(ds[var_name].values)
            finite = np.isfinite(arr)
            total = int(arr.size)
            valid = int(finite.sum())
            if total > 0:
                result["checks"].setdefault("variables", {})[var_name] = {
                    "valid_fraction": float(valid / total),
                    "min_value": (
                        float(np.nanmin(arr[finite])) if valid > 0 else None
                    ),
                    "max_value": (
                        float(np.nanmax(arr[finite])) if valid > 0 else None
                    ),
                }

        if result["errors"]:
            result["status"] = "fail"
    finally:
        ds.close()

    return result


def check_missing_expected_files():
    missing = []
    for file_name in EXPECTED_FILES:
        file_path = MEASUREMENT_DIR / file_name
        if not file_path.exists():
            missing.append(str(file_path.relative_to(ROOT)))
    return missing


def run_audit():
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "expected_month_span": [EXPECTED_MONTHS[0], EXPECTED_MONTHS[-1]],
        "expected_total_cubes": 12,
        "files_found": 0,
        "files_checked": 0,
        "missing_files": [],
        "status": "pass",
        "results": [],
    }

    missing = check_missing_expected_files()
    report["missing_files"] = missing
    if missing:
        report["status"] = "fail"

    for file_name in sorted(EXPECTED_FILES):
        file_path = MEASUREMENT_DIR / file_name
        report["files_checked"] += 1
        if not file_path.exists():
            continue
        report["files_found"] += 1
        result = audit_one_cube(file_path)
        report["results"].append(result)
        if result["status"] == "fail":
            report["status"] = "fail"

    with REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print("=== QA Audit: 12 regional cube integrity ===")
    print(f"Files expected: {report['expected_total_cubes']}")
    print(f"Files found: {report['files_found']}")
    print(f"Files checked: {report['files_checked']}")
    print(f"Missing files: {len(report['missing_files'])}")
    if report["missing_files"]:
        for missing_item in report["missing_files"]:
            print(f"  - {missing_item}")
    print(f"Results saved to: {REPORT_PATH}")
    if report["status"] == "pass":
        print("Overall status: PASS")
    else:
        print("Overall status: FAIL")
        for item in report["results"]:
            if item["status"] == "fail":
                print(f"  * {item['file']}")
                for error in item["errors"]:
                    print(f"    - {error}")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    try:
        sys.exit(run_audit())
    except KeyboardInterrupt:
        print("QA audit interrupted.")
        sys.exit(130)
