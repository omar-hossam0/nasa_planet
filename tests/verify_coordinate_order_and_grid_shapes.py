import json
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
MEASUREMENT_DIR = ROOT / "data" / "nasa" / "measurements"

PRODUCTS = {
    "M2TMNXSLV": {
        "lat_step": 0.5,
        "lon_step": 0.625,
        "regions": {
            "Nile": {"lat": (24.0, 32.0), "lon": (29.0, 33.0)},
            "Morocco": {"lat": (30.0, 35.0), "lon": (-10.0, -5.0)},
            "Sahel": {"lat": (12.0, 17.0), "lon": (-5.0, 5.0)},
        },
    },
    "GLDAS_NOAH025_M": {
        "lat_step": 0.25,
        "lon_step": 0.25,
        "regions": {
            "Nile": {"lat": (24.0, 32.0), "lon": (29.0, 33.0)},
            "Morocco": {"lat": (30.0, 35.0), "lon": (-10.0, -5.0)},
            "Sahel": {"lat": (12.0, 17.0), "lon": (-5.0, 5.0)},
        },
    },
    "GPM_3IMERGM": {
        "lat_step": 0.1,
        "lon_step": 0.1,
        "regions": {
            "Nile": {"lat": (24.0, 32.0), "lon": (29.0, 33.0)},
            "Morocco": {"lat": (30.0, 35.0), "lon": (-10.0, -5.0)},
            "Sahel": {"lat": (12.0, 17.0), "lon": (-5.0, 5.0)},
        },
    },
    "MOD13C2": {
        "lat_step": 0.05,
        "lon_step": 0.05,
        "regions": {
            "Nile": {"lat": (24.0, 32.0), "lon": (29.0, 33.0)},
            "Morocco": {"lat": (30.0, 35.0), "lon": (-10.0, -5.0)},
            "Sahel": {"lat": (12.0, 17.0), "lon": (-5.0, 5.0)},
        },
    },
}


def file_group(product_name, region_name):
    return f"{product_name}_{region_name}_2001_2024.nc"


def monotonic_increasing(values):
    return np.all(np.diff(values) > 0)


def monotonic_decreasing(values):
    return np.all(np.diff(values) < 0)


def approx_equal(value, target, tolerance=1e-6):
    return abs(float(value) - float(target)) <= tolerance


def check_file(file_name):
    result = {
        "file": file_name,
        "status": "pass",
        "errors": [],
    }

    path = MEASUREMENT_DIR / file_name
    if not path.exists():
        result["status"] = "fail"
        result["errors"].append("Missing file.")
        return result

    try:
        ds = xr.open_dataset(path)
    except Exception as exc:
        result["status"] = "fail"
        result["errors"].append(f"Could not open NetCDF: {exc}")
        return result

    try:
        product_name = next(
            name for name in PRODUCTS if file_name.startswith(f"{name}_")
        )
        region_name = file_name[len(product_name) + 1 : -len("_2001_2024.nc")]
        config = PRODUCTS[product_name]
        expected_lat_step = config["lat_step"]
        expected_lon_step = config["lon_step"]
        region_bounds = config["regions"][region_name]

        lat_name = next((key for key in ds.coords if "lat" in key.lower()), None)
        lon_name = next((key for key in ds.coords if "lon" in key.lower()), None)
        if lat_name is None or lon_name is None:
            result["status"] = "fail"
            result["errors"].append("Latitude or longitude coordinate missing.")
            return result

        lat_values = np.asarray(ds[lat_name].values, dtype=float)
        lon_values = np.asarray(ds[lon_name].values, dtype=float)

        if lat_values.size < 2 or lon_values.size < 2:
            result["status"] = "fail"
            result["errors"].append("Coordinate axis too short for grid validation.")
            return result

        if not monotonic_increasing(lat_values):
            result["status"] = "fail"
            result["errors"].append("Latitude values are not increasing in the native grid.")

        if not monotonic_increasing(lon_values):
            result["status"] = "fail"
            result["errors"].append("Longitude values are not increasing in the native grid.")

        lat_step = float(np.median(np.diff(lat_values)))
        lon_step = float(np.median(np.diff(lon_values)))
        if not np.isclose(lat_step, expected_lat_step, rtol=0.0, atol=1e-6):
            result["status"] = "fail"
            result["errors"].append(
                f"Latitude step mismatch: expected {expected_lat_step}, found {lat_step}."
            )

        if not np.isclose(lon_step, expected_lon_step, rtol=0.0, atol=1e-6):
            result["status"] = "fail"
            result["errors"].append(
                f"Longitude step mismatch: expected {expected_lon_step}, found {lon_step}."
            )

        expected_lat_min, expected_lat_max = region_bounds["lat"]
        expected_lon_min, expected_lon_max = region_bounds["lon"]
        if lat_values[0] < expected_lat_min - 1e-6 or lat_values[-1] > expected_lat_max + 1e-6:
            result["status"] = "fail"
            result["errors"].append(
                f"Latitude bounds out of expected region window: {lat_values[0]}..{lat_values[-1]} "
                f"not within {expected_lat_min}..{expected_lat_max}."
            )

        if lon_values[0] < expected_lon_min - 1e-6 or lon_values[-1] > expected_lon_max + 1e-6:
            result["status"] = "fail"
            result["errors"].append(
                f"Longitude bounds out of expected region window: {lon_values[0]}..{lon_values[-1]} "
                f"not within {expected_lon_min}..{expected_lon_max}."
            )

        if ds[lat_name].ndim > 1:
            result["status"] = "fail"
            result["errors"].append("Latitude coordinate is not a 1D axis as expected.")

        if ds[lon_name].ndim > 1:
            result["status"] = "fail"
            result["errors"].append("Longitude coordinate is not a 1D axis as expected.")

        result["details"] = {
            "lat_step": lat_step,
            "lon_step": lon_step,
            "lat_extent": [float(lat_values.min()), float(lat_values.max())],
            "lon_extent": [float(lon_values.min()), float(lon_values.max())],
        }
    finally:
        ds.close()

    return result


def main():
    report = {
        "script": "verify_coordinate_order_and_grid_shapes.py",
        "status": "pass",
        "results": [],
    }

    files = []
    for product_name in PRODUCTS:
        for region_name in PRODUCTS[product_name]["regions"]:
            files.append(file_group(product_name, region_name))

    for file_name in sorted(files):
        result = check_file(file_name)
        report["results"].append(result)
        if result["status"] != "pass":
            report["status"] = "fail"

    with (ROOT / "tests" / "verify_coordinate_order_and_grid_shapes_report.json").open(
        "w", encoding="utf-8"
    ) as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print("=== Coordinate and Grid Shape Verification ===")
    print(f"Files checked: {len(report['results'])}")
    print(f"Overall status: {report['status'].upper()}")
    for item in report["results"]:
        print(f"- {item['file']}: {item['status'].upper()}")
        for error in item["errors"]:
            print(f"  * {error}")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
