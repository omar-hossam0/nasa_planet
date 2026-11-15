import json
from pathlib import Path

import numpy as np
import xarray as xr

ROOT = Path(__file__).resolve().parent.parent
MEASUREMENT_DIR = ROOT / "data" / "nasa" / "measurements"

PRODUCTS = {
    "M2TMNXSLV": {"variable": "T2M"},
    "GLDAS_NOAH025_M": {"variable": "SoilMoi0_10cm_inst"},
    "GPM_3IMERGM": {"variable": "precipitation"},
    "MOD13C2": {"variable": "NDVI"},
}


def file_group(product_name, region_name):
    return f"{product_name}_{region_name}_2001_2024.nc"


def check_file(file_name):
    result = {
        "file": file_name,
        "status": "pass",
        "errors": [],
        "checks": {},
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
        variable_name = PRODUCTS[product_name]["variable"]
        region_name = file_name[len(product_name) + 1 : -len("_2001_2024.nc")]

        if product_name == "M2TMNXSLV":
            values = np.asarray(ds[variable_name].values, dtype=float)
            finite = values[np.isfinite(values)]
            if finite.size == 0:
                result["status"] = "fail"
                result["errors"].append("No finite T2M values found.")
            else:
                min_value = float(np.min(finite))
                max_value = float(np.max(finite))
                if min_value < 180.0 or max_value > 350.0:
                    result["status"] = "fail"
                    result["errors"].append(
                        f"T2M range outside expected Kelvin bounds: [{min_value}, {max_value}]"
                    )
                result["checks"]["kelvin_range"] = [min_value, max_value]

        if product_name == "GLDAS_NOAH025_M":
            values = np.asarray(ds[variable_name].values, dtype=float)
            finite = values[np.isfinite(values)]
            if finite.size == 0:
                result["status"] = "fail"
                result["errors"].append("No finite soil moisture values found.")
            else:
                min_value = float(np.min(finite))
                max_value = float(np.max(finite))
                if min_value < 0.0 or max_value > 1000.0:
                    result["status"] = "fail"
                    result["errors"].append(
                        f"Soil moisture range outside kg m-2 bounds: [{min_value}, {max_value}]"
                    )
                result["checks"]["soil_moisture_range"] = [min_value, max_value]

        if product_name == "GPM_3IMERGM":
            values = np.asarray(ds[variable_name].values, dtype=float)
            finite = values[np.isfinite(values)]
            if finite.size == 0:
                result["status"] = "fail"
                result["errors"].append("No finite precipitation values found.")
            else:
                min_value = float(np.min(finite))
                max_value = float(np.max(finite))
                if min_value < 0.0 or max_value > 10.0:
                    result["status"] = "fail"
                    result["errors"].append(
                        f"Precipitation range outside expected hourly rate bounds: [{min_value}, {max_value}]"
                    )
                result["checks"]["precip_rate_range"] = [min_value, max_value]

                month_len = values.shape[0]
                if month_len != 288:
                    result["status"] = "fail"
                    result["errors"].append(
                        f"Expected 288 months but found {month_len}."
                    )

        if product_name == "MOD13C2":
            values = np.asarray(ds[variable_name].values, dtype=float)
            finite = values[np.isfinite(values)]
            if finite.size == 0:
                result["status"] = "fail"
                result["errors"].append("No finite NDVI values found.")
            else:
                min_value = float(np.min(finite))
                max_value = float(np.max(finite))
                if min_value < -0.2 or max_value > 1.0:
                    result["status"] = "fail"
                    result["errors"].append(
                        f"NDVI range outside expected bounds: [{min_value}, {max_value}]"
                    )
                result["checks"]["ndvi_range"] = [min_value, max_value]

        result["checks"]["region"] = region_name
    finally:
        ds.close()

    return result


def main():
    report = {
        "script": "verify_units_and_scale_decoding.py",
        "status": "pass",
        "results": [],
    }

    files = []
    for product_name in PRODUCTS:
        for region_name in ["Nile", "Morocco", "Sahel"]:
            files.append(file_group(product_name, region_name))

    for file_name in sorted(files):
        result = check_file(file_name)
        report["results"].append(result)
        if result["status"] != "pass":
            report["status"] = "fail"

    with (
        ROOT / "tests" / "verify_units_and_scale_decoding_report.json"
    ).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print("=== Unit and Scale Decoding Verification ===")
    print(f"Files checked: {len(report['results'])}")
    print(f"Overall status: {report['status'].upper()}")
    for item in report["results"]:
        print(f"- {item['file']}: {item['status'].upper()}")
        for error in item["errors"]:
            print(f"  * {error}")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
