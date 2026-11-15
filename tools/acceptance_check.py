"""Member 6 release checks.

Runs the acceptance items from docs/architecture/PLAN.md and writes
docs/acceptance_report.json. Every check prints PASS/FAIL with the actual
number it observed.

Run:  python tools/acceptance_check.py
"""
from __future__ import annotations

import csv
import io
import json
import re
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, registry  # noqa: E402
from app.main import app  # noqa: E402

RESULTS: list[dict] = []
PRESET = {"region_id": "nile_corridor", "variable_ids": ["air_temperature"],
          "start_month": "2001-01", "end_month": "2024-12"}


def check(name: str, ok: bool, detail: str, item: str) -> None:
    RESULTS.append({"check": name, "item": item, "passed": bool(ok),
                    "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def wait(client, job_id, timeout=300):
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

    with TestClient(app) as client:
        # ---------------------------------------------------------- readiness
        cat = client.get("/v1/catalog").json()
        ready = [e for e in cat["entries"]
                 if e["measurement_ready"] and e["method_ready"]]
        check("readiness_12_pairs", len(ready) == 12,
              f"{len(ready)}/12 measurement+method ready", "readiness")

        health = client.get("/health").json()
        check("revisions_exposed", bool(health["data_revision"]) and
              health["method_revision"].startswith("m2-"),
              f"data {health['data_revision'][:12]} method "
              f"{health['method_revision']}", "readiness")

        # --------------------------------------------------- analysis + receipt
        r = client.post("/v1/analyses", json=PRESET)
        job = wait(client, r.json()["job_id"])
        check("analysis_succeeds", job["state"] == "succeeded",
              f"job {job['job_id']} -> {job['state']}", "end_to_end")

        result = client.get(f"/v1/analyses/{job['job_id']}/result").json()
        var = result["payload"]["variables"][0]
        check("slope_present", var["trend"]["slope_per_year"] is not None,
              f"slope {var['trend']['slope_per_year']:+.5f} "
              f"{var['units']}/yr", "end_to_end")

        receipt = client.get(f"/v1/receipts/{result['receipt_id']}")
        rp = receipt.json()["payload"]
        required = ("request", "data_revision", "method_revision",
                    "software_revision", "sources", "qa_policy",
                    "spatial_mask", "aggregation_policy", "anomaly_baseline",
                    "trend_method", "dependence", "bootstrap", "multiplicity")
        missing = [k for k in required if k not in rp]
        check("receipt_complete", not missing,
              f"{len(required) - len(missing)}/{len(required)} fields, "
              f"{sum(s['granule_count'] for s in rp['sources'])} granules",
              "receipt")
        check("receipt_has_no_secrets",
              not re.search(r"password|token|secret|api[_-]?key|bearer",
                            json.dumps(receipt.json()).lower()),
              "no credential-like keys", "receipt")

        # --------------------------------------------------------- citations
        exp = client.get(f"/v1/analyses/{job['job_id']}/explanation?language=ar").json()
        cited = exp["explanation"]["cited_chunk_ids"]
        retrieved = {c["chunk_id"] for c in exp["citations"]}
        check("citations_resolve", bool(cited) and set(cited) <= retrieved,
              f"{len(cited)} citations, all in retrieved set", "citations")
        check("explanation_validated", exp["validation"]["ok"],
              f"path {exp['path']}", "citations")
        check("llm_disabled_falls_back",
              exp["path"] in ("deterministic", "deterministic_fallback"),
              "no provider configured, deterministic answer served", "fallback")

        # ------------------------------------------------- numeric consistency
        series = client.get(f"/v1/analyses/{job['job_id']}/series").json()["series"][0]
        same_slope = abs(series["trend"]["slope_per_year"] -
                         var["trend"]["slope_per_year"]) < 1e-12
        check("chart_matches_card", same_slope,
              f"series slope {series['trend']['slope_per_year']:+.6f} == "
              f"card {var['trend']['slope_per_year']:+.6f}", "consistency")

        cmp = client.post("/v1/compare",
                          json={"variable_id": "air_temperature"}).json()
        nile = [x for x in cmp["regions"]
                if x["region_id"] == "nile_corridor"][0]
        check("compare_matches_card",
              abs(nile["slope_per_year"] - var["trend"]["slope_per_year"]) < 1e-12,
              f"compare {nile['slope_per_year']:+.6f} == card "
              f"{var['trend']['slope_per_year']:+.6f}", "consistency")

        # ------------------------------------------------------------- units
        unit_ok = True
        for e in ready:
            if not e["units"]:
                unit_ok = False
        check("units_present_for_all", unit_ok,
              "every ready entry carries units", "units")

        # ------------------------------------------------------ export reopen
        with tempfile.TemporaryDirectory() as td:
            rp_json = Path(td) / "result.json"
            rp_json.write_text(json.dumps(result), encoding="utf-8")
            reopened = json.loads(rp_json.read_text(encoding="utf-8"))
            ok_json = reopened["result_id"] == result["result_id"]

            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["month", "value", "trend_line"])
            for i, m in enumerate(series["months"]):
                w.writerow([m, series["values"][i],
                            series["trend_line"][i]])
            rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
            ok_csv = len(rows) == 288 and rows[0]["month"] == "2001-01"
            check("export_reopens", ok_json and ok_csv,
                  f"JSON reopens, CSV has {len(rows)} rows", "export")

    # --------------------------------------------------------- offline build
    offline_js = ROOT / "dist" / "offline" / "offline_data.js"
    if offline_js.exists():
        text = offline_js.read_text(encoding="utf-8")
        blob = text[len("window.TD_OFFLINE="):].rstrip().rstrip(";")
        data = json.loads(blob)
        n = len(data["analyses"])
        key = "nile_corridor|air_temperature|2001-01|2024-12|none"
        snap = data["analyses"].get(key)
        same = snap is not None and abs(
            snap["result"]["payload"]["variables"][0]["trend"]["slope_per_year"]
            - var["trend"]["slope_per_year"]) < 1e-12
        check("offline_bundle_complete", n >= 12 and len(data["spatial"]) >= 12,
              f"{n} analyses, {len(data['spatial'])} spatial products",
              "offline")
        check("offline_matches_live", same,
              "snapshot slope equals live slope", "offline")
    else:
        check("offline_bundle_complete", False, "dist/offline missing", "offline")

    passed = sum(1 for c in RESULTS if c["passed"])
    report = {
        "generated": "2026-11-14",
        "method_revision": reg.method_revision,
        "data_revision": reg.revision,
        "checks": RESULTS,
        "summary": {"total": len(RESULTS), "passed": passed,
                    "failed": len(RESULTS) - passed},
    }
    out = ROOT / "docs" / "acceptance_report.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"\n{passed}/{len(RESULTS)} release checks passed -> {out.name}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
