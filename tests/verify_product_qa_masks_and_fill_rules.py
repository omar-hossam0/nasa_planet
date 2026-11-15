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

        if product_name == "MOD13C2":
            if "NDVI" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("NDVI variable missing.")
            if "pixel_reliability" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("pixel_reliability missing.")
            if "VI_Quality" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("VI_Quality missing.")

            ndvi = np.asarray(ds["NDVI"].values, dtype=float)
            rel = np.asarray(ds["pixel_reliability"].values, dtype=np.uint16)
            vi_quality = np.asarray(ds["VI_Quality"].values, dtype=np.uint16)

            valid_ndvi = np.isfinite(ndvi)
            if np.any((ndvi <= -3000.0) & valid_ndvi):
                result["status"] = "fail"
                result["errors"].append(
                    "NDVI still contains fill values below -3000."
                )

            good_mask = np.isin(rel, [0, 1])
            if good_mask.size and good_mask.mean() < 0.5:
                result["status"] = "fail"
                result["errors"].append(
                    "pixel_reliability mask coverage is too sparse for reliable QA."
                )

            vi_quality_bits = (vi_quality & 0b11)
            vi_quality_mask = vi_quality_bits <= 1
            if vi_quality_mask.size and vi_quality_mask.mean() < 0.5:
                result["status"] = "fail"
                result["errors"].append(
                    "VI_Quality bitmask fails the acceptable quality threshold."
                )

            result["checks"]["ndvi_valid_fraction"] = float(valid_ndvi.mean())
            result["checks"]["pixel_reliability_good_fraction"] = float(
                good_mask.mean()
            )
            result["checks"]["vi_quality_good_fraction"] = float(
                vi_quality_mask.mean()
            )

        if product_name == "GPM_3IMERGM":
            if "precipitation" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("precipitation variable missing.")
            if "precipitationQualityIndex" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("precipitationQualityIndex missing.")
            if "randomError" not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append("randomError missing.")

            precip = np.asarray(ds["precipitation"].values, dtype=float)
            quality = np.asarray(ds["precipitationQualityIndex"].values, dtype=float)
            random_error = np.asarray(ds["randomError"].values, dtype=float)

            if np.any((precip == 0.0) & np.isfinite(precip)):
                result["checks"]["zero_precip_count"] = int(
                    np.sum((precip == 0.0) & np.isfinite(precip))
                )
            if np.any(~np.isfinite(precip)):
                result["checks"]["nan_precip_count"] = int(np.sum(~np.isfinite(precip)))

            if quality.size > 0 and np.all(np.isnan(quality)):
                result["status"] = "fail"
                result["errors"].append("precipitationQualityIndex is entirely NaN.")

            if random_error.size > 0 and np.all(np.isnan(random_error)):
                result["status"] = "fail"
                result["errors"].append("randomError is entirely NaN.")

        if product_name == "GLDAS_NOAH025_M":
            if variable_name not in ds.data_vars:
                result["status"] = "fail"
                result["errors"].append(f"Missing variable: {variable_name}")
            else:
                values = np.asarray(ds[variable_name].values, dtype=float)
                if np.any((values == 0.0) & np.isfinite(values)):
                    zero_cells = int(np.sum((values == 0.0) & np.isfinite(values)))
                    result["checks"]["zero_cells"] = zero_cells
                    if zero_cells > 0:
                        result["status"] = "fail"
                        result["errors"].append(
                            "Sea or missing cells appear to be encoded as zero instead of NaN."
                        )

        if product_name == "M2TMNXSLV":
            values = np.asarray(ds[variable_name].values, dtype=float)
            if np.any((values == 0.0) & np.isfinite(values)):
                zero_cells = int(np.sum((values == 0.0) & np.isfinite(values)))
                result["checks"]["zero_cells"] = zero_cells
                if zero_cells > 0:
                    result["status"] = "fail"
                    result["errors"].append(
                        "Sea or missing cells appear to be encoded as zero instead of NaN."
                    )

        result["checks"]["region"] = region_name
    finally:
        ds.close()

    return result


def main():
    report = {
        "script": "verify_product_qa_masks_and_fill_rules.py",
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
        ROOT / "tests" / "verify_product_qa_masks_and_fill_rules_report.json"
    ).open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")

    print("=== Product QA Mask and Fill Rule Verification ===")
    print(f"Files checked: {len(report['results'])}")
    print(f"Overall status: {report['status'].upper()}")
    for item in report["results"]:
        print(f"- {item['file']}: {item['status'].upper()}")
        for error in item["errors"]:
            print(f"  * {error}")

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
