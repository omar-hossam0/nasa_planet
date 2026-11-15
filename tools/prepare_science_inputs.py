"""Generate Stage 2 prepared NetCDF files and an explicit coverage manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages/science"))
from src.preparation import prepare_registered
from src.preprocessing import load_policy, policy_hash


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data/derived/science/phase_2")
    parser.add_argument("--coverage-report", type=Path, default=ROOT / "packages/science/phase_reports/PHASE_2_COVERAGE.json")
    parser.add_argument("--variable-id", help="Optional exact semantic ID; default prepares all twelve pairs")
    parser.add_argument("--modis-mode", choices=("strict", "standard"), help="Explicit QA sensitivity variant")
    args = parser.parse_args()
    folder = args.output_dir.resolve()
    folder.mkdir(parents=True, exist_ok=True)
    policy = load_policy()
    if args.modis_mode is not None:
        policy["qa"]["modis_mode"] = args.modis_mode
    source_validation = []
    for source in policy["sources"]:
        actual_hash = file_hash(ROOT / source["path"])
        if actual_hash != source["sha256"]:
            raise ValueError(f"Source documentation hash mismatch: {source['path']}")
        source_validation.append({**source, "hash_verified": True})
    entries = json.loads((ROOT / "docs/architecture/scope.v2.json").read_text(encoding="utf-8"))["entries"]
    if args.variable_id is not None:
        entries = [entry for entry in entries if entry["variable_id"] == args.variable_id]
        if not entries:
            parser.error("Variable ID is not registered")
    records = []
    for entry in entries:
        prepared, metadata = prepare_registered(entry["variable_id"], entry["region_id"], policy=policy)
        name = f"{entry['variable_id']}__{entry['region_id']}.nc"
        target = folder / name
        encoding = {key: {"zlib": True, "complevel": 4} for key in prepared.data_vars}
        temporary = target.with_suffix(".partial.nc")
        prepared.to_netcdf(temporary, encoding=encoding)
        temporary.replace(target)
        metadata.update({"source_cube_file": entry["cube_file"],
                         "source_cube_sha256": file_hash(ROOT / entry["cube_file"]),
                         "artifact": target.relative_to(ROOT).as_posix() if target.is_relative_to(ROOT) else target.as_posix(),
                         "artifact_sha256": file_hash(target)})
        records.append(metadata)
        print(f"{entry['variable_id']} / {entry['region_id']}: "
              f"{metadata['eligible_fixed_support_cells']}/{metadata['selected_cell_count']} fixed cells, "
              f"area fraction {metadata['fixed_support_area_fraction_of_selected_native_cells']:.4f}", flush=True)
    manifest = {"policy_revision": policy["policy_revision"], "policy_sha256": policy_hash(policy),
                "policy_review_status": policy["status"], "inference_status": "not_computed",
                "entries": records, "documentation": source_validation}
    args.coverage_report.parent.mkdir(parents=True, exist_ok=True)
    args.coverage_report.write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} prepared cubes and coverage report: {args.coverage_report}")


if __name__ == "__main__":
    main()
