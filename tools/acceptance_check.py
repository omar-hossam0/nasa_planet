"""Release checks for the current FastAPI/React contract.

Run from the repository root with ``python tools/acceptance_check.py``.
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

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

RESULTS: list[dict] = []
PRESET = {
    "region_id": "nile_corridor",
    "variable_ids": ["air_temperature"],
    "start_month": "2001-01",
    "end_month": "2024-12",
}


def check(name: str, ok: bool, detail: str, item: str) -> None:
    RESULTS.append({"check": name, "item": item, "passed": bool(ok), "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def wait(client: TestClient, job_id: str, timeout: int = 300) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/v1/analyses/{job_id}").json()
        if body["status"] in ("completed", "failed"):
            return body
        time.sleep(0.2)
    raise TimeoutError(job_id)


def main() -> int:
    with TestClient(app) as client:
        catalog = client.get("/v1/catalog").json()
        regions = client.get("/v1/catalog/regions").json()["regions"]
        supported = {
            (region["region_id"], variable)
            for region in regions
            for variable in region["supported_variable_ids"]
        }
        available = {
            (region["region_id"], variable["variable_id"])
            for region in regions
            for variable in catalog["variables"]
            if variable["app_available"]
        }
        ready = supported & available
        check("readiness_12_pairs", len(ready) == 12, f"{len(ready)}/12 available pairs", "readiness")
        check("revisions_exposed", bool(catalog["registry_snapshot"]), "catalog revision exposed", "readiness")

        root = client.get("/", follow_redirects=False)
        product = client.get("/product/")
        check("product_routes", root.status_code == 307 and root.headers["location"] == "/product/"
              and product.status_code == 200, "root redirects and product HTML is served", "runtime")

        accepted = client.post("/v1/analyses", json=PRESET)
        job = wait(client, accepted.json()["job_id"])
        check("analysis_succeeds", job["status"] == "completed", f"{job['job_id']} -> {job['status']}", "end_to_end")
        result = client.get(f"/v1/results/{job['result_id']}").json()
        variable = result["variables"][0]
        check("slope_present", variable["trend"]["slope_per_year"] is not None,
              f"slope {variable['trend']['slope_per_year']:+.5f}", "end_to_end")
        receipt = client.get(f"/v1/receipts/{result['receipt_id']}").json()
        receipt_text = json.dumps(receipt).lower()
        check("receipt_has_no_secrets",
              not re.search(r"password|token|secret|api[_-]?key|bearer", receipt_text),
              "no credential-like keys", "receipt")

        explanation = client.post("/v1/explanations", json={"result_id": result["result_id"]}).json()
        check("explanation_validated", bool(explanation["references"]), "references attached", "citations")
        check("inference_honest", variable["trend"]["p_value"] is None
              and variable["trend"]["inference_status"] == "not_computed",
              "p-value withheld until inference review", "science")

        series = variable["series"]
        check("chart_series_complete", len(series) == 288, f"{len(series)} monthly points", "consistency")
        spatial = client.get(f"/v1/results/{result['result_id']}/spatial?compact=true").json()
        check("spatial_shape", len(spatial["slope"]) == len(spatial["lat"])
              and all(len(row) == len(spatial["lon"]) for row in spatial["slope"]),
              f"{len(spatial['lat'])}x{len(spatial['lon'])} native grid", "spatial")

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text(json.dumps(result), encoding="utf-8")
            reopened = json.loads(output.read_text(encoding="utf-8"))
            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["month", "value"])
            writer.writerows((point["month"], point["value"]) for point in series)
            rows = list(csv.DictReader(io.StringIO(csv_buffer.getvalue())))
        check("export_reopens", reopened["result_id"] == result["result_id"] and len(rows) == 288,
              f"JSON reopens, CSV has {len(rows)} rows", "export")

    offline = ROOT / "dist" / "offline" / "offline_data.js"
    check("offline_bundle_complete", offline.exists(), "offline bundle present", "offline")
    passed = sum(item["passed"] for item in RESULTS)
    report = {
        "generated": time.strftime("%Y-%m-%d"),
        "checks": RESULTS,
        "summary": {"total": len(RESULTS), "passed": passed, "failed": len(RESULTS) - passed},
    }
    output = ROOT / "docs" / "acceptance_report.json"
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n{passed}/{len(RESULTS)} release checks passed -> {output}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
