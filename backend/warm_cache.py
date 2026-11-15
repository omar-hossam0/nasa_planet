"""Pre-warm the cache for the demo presets.

Run once before presenting:  python warm_cache.py
Then the same requests on stage return from cache in milliseconds.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app import config, db, registry
from app.main import app

PRESETS = [
    {"region_id": "nile_corridor",
     "variable_ids": ["air_temperature", "soil_moisture"],
     "start_month": "2001-01", "end_month": "2024-12"},
    {"region_id": "sahel_comparison",
     "variable_ids": ["vegetation_greenness", "precipitation"],
     "start_month": "2001-01", "end_month": "2024-12"},
    {"region_id": "morocco_comparison",
     "variable_ids": ["air_temperature"],
     "start_month": "2001-01", "end_month": "2024-12"},
]


def wait(c, job_id, timeout=300):
    t0 = time.time()
    while time.time() - t0 < timeout:
        body = c.get(f"/v1/analyses/{job_id}").json()
        if body["state"] in ("succeeded", "failed"):
            return body
        time.sleep(0.2)
    raise TimeoutError(job_id)


def main() -> int:
    config.ensure_dirs()
    db.init_db()
    reg = registry.load_registry()
    db.sync_catalog(reg.entries(), reg.revision)
    with TestClient(app) as c:
        for preset in PRESETS:
            r = c.post("/v1/analyses", json=preset)
            body = r.json()
            if body.get("cached"):
                print(f"cached   {preset['region_id']} {preset['variable_ids']}")
                continue
            job = wait(c, body["job_id"])
            print(f"{job['state']:9s} {preset['region_id']} "
                  f"{preset['variable_ids']}")
    print("cache warm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
