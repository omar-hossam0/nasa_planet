"""Build a self-contained offline snapshot of the app.

Produces `dist/offline/` with index.html, app.js, style.css and
`offline_data.js` (window.TD_OFFLINE). The page then runs from the filesystem
with no server, no network and no model, using results precomputed by the same
frozen method.

Run:  python tools/export_offline.py
"""
from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, registry  # noqa: E402
from app.main import app  # noqa: E402

REGIONS = ["nile_corridor", "morocco_comparison", "sahel_comparison"]
VARIABLES = ["air_temperature", "soil_moisture", "precipitation",
             "vegetation_greenness"]
START, END = "2001-01", "2024-12"


def key(region: str, variable: str) -> str:
    return f"{region}|{variable}|{START}|{END}|none"


def wait(client, job_id: str, timeout: float = 300) -> dict:
    t0 = time.time()
    while time.time() - t0 < timeout:
        body = client.get(f"/v1/analyses/{job_id}").json()
        if body["state"] in ("succeeded", "failed"):
            return body
        time.sleep(0.2)
    raise TimeoutError(job_id)


def main() -> int:
    config.ensure_dirs()
    db.init_db()
    reg = registry.load_registry()
    db.sync_catalog(reg.entries(), reg.revision)

    out_dir = ROOT / "dist" / "offline"
    out_dir.mkdir(parents=True, exist_ok=True)

    offline = {"catalog": None, "spatial": {}, "analyses": {},
               "explanations": {}, "series": {}, "meta": {}}

    with TestClient(app) as client:
        offline["catalog"] = client.get("/v1/catalog").json()
        for region in REGIONS:
            for variable in VARIABLES:
                body = {"region_id": region, "variable_ids": [variable],
                        "start_month": START, "end_month": END}
                r = client.post("/v1/analyses", json=body)
                if r.status_code not in (200, 201):
                    print(f"skip {region}/{variable}: {r.status_code} {r.text[:120]}")
                    continue
                job = wait(client, r.json()["job_id"])
                if job["state"] != "succeeded":
                    print(f"skip {region}/{variable}: {job['state']}")
                    continue
                result = client.get(
                    f"/v1/analyses/{job['job_id']}/result").json()
                series = client.get(
                    f"/v1/analyses/{job['job_id']}/series").json()
                spatial = client.get(
                    f"/v1/spatial/{variable}/{region}").json()
                expl = {}
                for lang in ("ar", "en"):
                    e = client.get(
                        f"/v1/analyses/{job['job_id']}/explanation"
                        f"?language={lang}").json()
                    expl[lang] = e
                    offline["explanations"][f"{job['job_id']}:{lang}"] = e
                offline["analyses"][key(region, variable)] = {
                    "job": job, "result": result, "series": series,
                    "explanation": expl["ar"], "spatial": spatial,
                }
                offline["series"][job["job_id"]] = series
                offline["spatial"][f"{variable}:{region}"] = spatial
                print(f"snapshot {region:20s} {variable:22s} "
                      f"{len(spatial['slope'])}x{len(spatial['slope'][0])} cells",
                      flush=True)

    offline["meta"] = {
        "generated": "2026-11-14",
        "method_revision": reg.method_revision,
        "data_revision": reg.revision,
        "note": "precomputed with the frozen method; no network, no model",
        "requests": len(offline["analyses"]),
    }

    # write the data bundle
    blob = json.dumps(offline, ensure_ascii=False, separators=(",", ":"))
    (out_dir / "offline_data.js").write_text(
        "window.TD_OFFLINE=" + blob + ";\n", encoding="utf-8")

    # copy the app and inject the bundle before app.js
    shutil.copy(ROOT / "web" / "app.js", out_dir / "app.js")
    shutil.copy(ROOT / "web" / "style.css", out_dir / "style.css")
    for name in ("landing.html", "landing.css", "landing.js"):
        shutil.copy(ROOT / "web" / name, out_dir / name)
    shutil.copytree(ROOT / "web" / "assets", out_dir / "assets", dirs_exist_ok=True)
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    html = html.replace('<script src="app.js"></script>',
                        '<script src="offline_data.js"></script>\n'
                        '<script src="app.js"></script>')
    (out_dir / "index.html").write_text(html, encoding="utf-8")

    size = (out_dir / "offline_data.js").stat().st_size
    print(f"\nwrote {out_dir}  (offline_data.js {size/1e6:.2f} MB, "
          f"{len(offline['analyses'])} analyses)")
    (out_dir / "README.md").write_text(
        "# Offline snapshot\n\n"
        "Open `landing.html` for the introduction, or `index.html` for the "
        "explorer — no server, no network, no model.\n"
        f"Generated from data revision `{reg.revision[:12]}` and method "
        f"`{reg.method_revision}`.\n"
        f"{len(offline['analyses'])} precomputed analyses, "
        f"{len(offline['spatial'])} spatial products.\n\n"
        "The app detects the bundle and serves catalog, results, series, "
        "explanations and maps from it. A banner states that the result is a "
        "precomputed snapshot.\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
