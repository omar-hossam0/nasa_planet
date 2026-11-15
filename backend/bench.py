"""Performance benchmark for the showcase path.

Run:  python bench.py
Prints wall-clock numbers for: one variable, four variables, an AOI subset and
a cached repeat. These are the numbers the UI promises may be based on.
"""
from __future__ import annotations

import json
import time

from fastapi.testclient import TestClient

from app import config, db, registry
from app.main import app

CASES = {
    "single_variable_full_period": {
        "region_id": "nile_corridor",
        "variable_ids": ["air_temperature"],
        "start_month": "2001-01", "end_month": "2024-12",
    },
    "four_variables_full_period": {
        "region_id": "nile_corridor",
        "variable_ids": ["air_temperature", "soil_moisture",
                         "precipitation", "vegetation_greenness"],
        "start_month": "2001-01", "end_month": "2024-12",
    },
    "single_variable_aoi": {
        "region_id": "nile_corridor",
        "variable_ids": ["air_temperature"],
        "start_month": "2001-01", "end_month": "2024-12",
        "aoi": {"type": "Polygon", "coordinates": [[
            [31.0, 30.0], [32.0, 30.0], [32.0, 31.0], [31.0, 31.0],
            [31.0, 30.0]]]},
    },
}


def wait(c, job_id, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        body = c.get(f"/v1/analyses/{job_id}").json()
        if body["state"] in ("succeeded", "failed"):
            return body, time.time() - t0
        time.sleep(0.1)
    raise TimeoutError(job_id)


def main() -> int:
    config.ensure_dirs()
    db.init_db()
    reg = registry.load_registry()
    db.sync_catalog(reg.entries(), reg.revision)
    results = {}
    with TestClient(app) as c:
        for name, body in CASES.items():
            t0 = time.time()
            r = c.post("/v1/analyses", json=body)
            assert r.status_code in (200, 201), r.text
            job_id = r.json()["job_id"]
            job, _ = wait(c, job_id)
            elapsed = time.time() - t0
            res = c.get(f"/v1/analyses/{job_id}/result")
            size = len(res.content) if res.status_code == 200 else 0
            results[name] = {
                "state": job["state"],
                "seconds": round(elapsed, 2),
                "result_bytes": size,
            }
            print(f"{name:34s} {job['state']:10s} {elapsed:6.2f}s  "
                  f"{size/1024:7.1f} KB", flush=True)

        # cached repeat of the first case
        t0 = time.time()
        r = c.post("/v1/analyses", json=CASES["single_variable_full_period"])
        results["cached_repeat"] = {
            "status": r.status_code,
            "cached": r.json().get("cached"),
            "seconds": round(time.time() - t0, 4),
        }
        print(f"{'cached_repeat':34s} {'hit' if r.json().get('cached') else 'miss':10s} "
              f"{time.time()-t0:6.4f}s")

    out = {"generated": "2026-11-14", "cases": results}
    (config.BASE_DIR / "bench_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote bench_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
