"""Read-only Phase 0 inventory; this does not apply QA or compute trends.

Run from the repository root with the pinned NASA xarray/NetCDF dependencies:
    python tools/audit_science_inputs.py --output packages/science/phase_reports/input_audit.json

Exit 1 means the existing registry and files disagree. Preserve those findings
for the data owner rather than guessing a field alias or changing source data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xarray as xr


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def month_range(start: str, end: str) -> list[str]:
    def index(value: str) -> int:
        year, month = map(int, value.split("-"))
        if not 1 <= month <= 12:
            raise ValueError(f"Invalid calendar month: {value}")
        return year * 12 + month - 1

    first, last = index(start), index(end)
    if first > last:
        raise ValueError("Reversed analysis period")
    return [f"{i // 12:04d}-{i % 12 + 1:02d}" for i in range(first, last + 1)]


def inspect_entry(root: Path, entry: dict) -> dict:
    path = (root / entry["cube_file"]).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError("Cube path escapes repository")
    result = {
        key: entry[key]
        for key in ("variable_id", "region_id", "product_id", "version",
                    "source_variable", "cube_file", "period", "bbox")
    }
    result["cube_variable"] = entry.get("cube_variable", entry["source_variable"])
    result.update({"issues": [], "qa_applied_by_audit": False})
    if not path.is_file():
        result["issues"].append("cube_file_missing")
        return result
    result["sha256"] = sha256(path)
    result["bytes"] = path.stat().st_size
    with xr.open_dataset(path) as ds:
        result["dimensions"] = dict(ds.sizes)
        result["attributes"] = {name: str(value) for name, value in ds.attrs.items()}
        result["variables"] = {}
        for name, variable in ds.data_vars.items():
            values = variable.values
            finite = np.isfinite(values)
            result["variables"][name] = {
                "dimensions": list(variable.dims),
                "units": variable.attrs.get("units"),
                "attributes": {k: str(v) for k, v in variable.attrs.items()},
                "encoding": {k: str(variable.encoding[k]) for k in
                             ("_FillValue", "scale_factor", "add_offset")
                             if k in variable.encoding},
                "finite_count_before_product_qa": int(finite.sum()),
                "missing_count_before_product_qa": int((~finite).sum()),
                "source_fill_minus_9999_count": int((values == -9999).sum()),
            }
        cube_variable = result["cube_variable"]
        if cube_variable not in ds.data_vars:
            result["issues"].append("catalog_cube_variable_absent_from_cube")
        elif "cube_units" in entry and ds[cube_variable].attrs.get("units") != entry["cube_units"]:
            result["issues"].append("catalog_cube_units_differ_from_cube")
        if ds.attrs.get("product") != entry["product_id"]:
            result["issues"].append("catalog_product_differs_from_cube_attribute")
        if "time" not in ds.coords:
            result["issues"].append("missing_time_coordinate")
        else:
            months = [str(value)[:7] for value in ds.time.values]
            result["time"] = {
                "first_timestamp": str(ds.time.values[0]) if months else None,
                "last_timestamp": str(ds.time.values[-1]) if months else None,
                "calendar": ds.time.encoding.get("calendar"),
                "count": len(months),
                "unique_months": len(set(months)),
                "matches_catalog_period_in_order": months == month_range(*entry["period"]),
            }
            if not result["time"]["matches_catalog_period_in_order"]:
                result["issues"].append("months_differ_from_catalog_period")
        result["coordinates"] = {}
        west, south, east, north = entry["bbox"]
        for name, lower, upper in (("lat", south, north), ("lon", west, east)):
            if name not in ds.coords:
                result["issues"].append(f"missing_{name}_coordinate")
                continue
            values = ds[name].values
            increasing = bool(np.all(np.diff(values) > 0))
            in_bbox = bool(np.all(np.isfinite(values) & (values >= lower) & (values <= upper)))
            result["coordinates"][name] = {
                "count": int(values.size),
                "first": float(values[0]), "last": float(values[-1]),
                "strictly_increasing": increasing,
                "centres_within_catalog_bbox": in_bbox,
                "units": ds[name].attrs.get("units"),
            }
            if not increasing or not in_bbox:
                result["issues"].append(f"{name}_coordinate_contract_mismatch")
    return result


def audit(root: Path) -> dict:
    scope_path = root / "docs/architecture/scope.v2.json"
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    entries = scope["entries"]
    keys = [(e["variable_id"], e["region_id"]) for e in entries]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate variable-region entries")
    observations = [inspect_entry(root, entry) for entry in entries]
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "scope_sha256": sha256(scope_path),
        "scope_path": "docs/architecture/scope.v2.json",
        "software_versions": {name: importlib.metadata.version(name)
                              for name in ("numpy", "xarray", "netCDF4")},
        "scope_entries": len(entries),
        "entries_without_contract_issues": sum(not e["issues"] for e in observations),
        "issue_count": sum(len(e["issues"]) for e in observations),
        "limitations": [
            "Metadata inventory only: no trend or inferential method was validated.",
            "Product versions are registry claims; file hashes identify the inspected bytes.",
            "Decoded missingness is reported before any product-specific QA selection.",
            "Monthly source subsets and their full lineage were not validated by this audit.",
            "This audit does not promote measurement, method, or application readiness.",
        ],
        "entries": observations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = audit(root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Inspected {result['scope_entries']} cubes; "
          f"{result['issue_count']} catalog/file contract issues. Output: {args.output}")
    return 1 if result["issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
