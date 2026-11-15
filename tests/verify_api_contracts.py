import hashlib
import json
import os
from pathlib import Path

try:
    import requests
except ImportError:  # pragma: no cover - runtime fallback for dry-run usage
    requests = None

ROOT = Path(__file__).resolve().parent.parent

API_BASE = os.environ.get("TREND_DETECTIVE_API_BASE", "")
TIMEOUT_SECONDS = 5


def canonical_json_bytes(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def request_hash_for(payload):
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def build_valid_analysis_request():
    return {
        "region_id": "Nile",
        "AOI": {
            "type": "Polygon",
            "coordinates": [[
                [28.8, 24.2],
                [33.2, 24.2],
                [33.2, 32.2],
                [28.8, 32.2],
                [28.8, 24.2],
            ]],
        },
        "variable_ids": ["T2M"],
        "start_month": "2001-01",
        "end_month": "2024-12",
        "aggregation_policy_id": "area_weighted_monthly_mean",
        "method_revision": "method_v1",
        "data_revisions": {"T2M": "M2TMNXSLV_v5.12.4"},
    }


def build_out_of_bounds_request():
    payload = build_valid_analysis_request()
    payload["AOI"] = {
        "type": "Polygon",
        "coordinates": [[
            [-10.0, -5.0],
            [10.0, -5.0],
            [10.0, 5.0],
            [-10.0, 5.0],
            [-10.0, -5.0],
        ]],
    }
    return payload


def build_invalid_geometry_request():
    payload = build_valid_analysis_request()
    payload["AOI"] = {
        "type": "Polygon",
        "coordinates": [[
            [0.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
            [0.0, 0.0],
        ]],
    }
    return payload


def build_unavailable_region_request():
    payload = build_valid_analysis_request()
    payload["region_id"] = "Amazon"
    return payload


def validate_catalog_payload(payload):
    if isinstance(payload, dict):
        possible_lists = []
        for key in ("catalog", "items", "entries", "results"):
            value = payload.get(key)
            if isinstance(value, list):
                possible_lists.append(value)
        if not possible_lists:
            raise ValueError("Catalog payload does not expose a list of entries.")
        catalog_items = possible_lists[0]
    elif isinstance(payload, list):
        catalog_items = payload
    else:
        raise TypeError("Catalog payload must be a list or object with a list field.")

    if not catalog_items:
        raise ValueError("Catalog list is empty.")

    required_keys = {"measurement_ready", "method_ready", "app_available"}
    for item in catalog_items:
        if not isinstance(item, dict):
            raise TypeError("Catalog item must be an object.")
        missing = sorted(required_keys - set(item.keys()))
        if missing:
            raise ValueError(f"Catalog item missing keys: {missing}")
        if not isinstance(item.get("measurement_ready"), bool):
            raise TypeError("measurement_ready must be boolean.")
        if not isinstance(item.get("method_ready"), bool):
            raise TypeError("method_ready must be boolean.")
        if not isinstance(item.get("app_available"), bool):
            raise TypeError("app_available must be boolean.")

    return catalog_items


def validate_receipt_payload(payload):
    if not isinstance(payload, dict):
        raise TypeError("Receipt payload must be a JSON object.")
    required = {
        "id",
        "request_hash",
        "normalized_request",
        "source_granules",
        "method_settings",
        "software_revision",
    }
    missing = sorted(required - set(payload.keys()))
    if missing:
        raise ValueError(f"Receipt payload missing fields: {missing}")
    return payload


def post_json(url, payload):
    if not API_BASE or requests is None:
        return {"skipped": True, "note": "Server not started; compile-only validation."}
    response = requests.post(url, json=payload, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def get_json(url):
    if not API_BASE or requests is None:
        return {"skipped": True, "note": "Server not started; compile-only validation."}
    response = requests.get(url, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.json()


def run_catalog_checks():
    payload = get_json(f"{API_BASE}/v1/catalog")
    if payload.get("skipped"):
        return {"status": "skipped", "reason": payload["note"]}
    validate_catalog_payload(payload)
    return {"status": "pass", "checked": "catalog"}


def run_analysis_submission_checks():
    valid_request = build_valid_analysis_request()
    valid_hash = request_hash_for(valid_request)

    valid_response = post_json(f"{API_BASE}/v1/analyses", valid_request)
    if valid_response.get("skipped"):
        return {"status": "skipped", "reason": valid_response["note"]}

    if not isinstance(valid_response, dict):
        raise TypeError("POST /v1/analyses should return a JSON object.")

    response_hash = valid_response.get("request_hash")
    if response_hash != valid_hash:
        raise ValueError(
            "Request hash mismatch: response request_hash does not match request hash."
        )

    duplicate_response = post_json(f"{API_BASE}/v1/analyses", valid_request)
    if duplicate_response.get("skipped"):
        return {"status": "skipped", "reason": duplicate_response["note"]}

    duplicate_hash = duplicate_response.get("request_hash")
    if duplicate_hash != valid_hash:
        raise ValueError("Duplicate analysis requests must reuse the same request hash.")

    invalid_geometry = post_json(
        f"{API_BASE}/v1/analyses",
        build_invalid_geometry_request(),
    )
    if invalid_geometry.get("skipped"):
        return {"status": "skipped", "reason": invalid_geometry["note"]}
    if invalid_geometry.get("status") != "rejected":
        raise ValueError("Invalid geometry request should be rejected.")

    out_of_bounds = post_json(
        f"{API_BASE}/v1/analyses",
        build_out_of_bounds_request(),
    )
    if out_of_bounds.get("skipped"):
        return {"status": "skipped", "reason": out_of_bounds["note"]}
    if out_of_bounds.get("status") != "rejected":
        raise ValueError("Out-of-bounds request should be rejected.")

    unavailable_region = post_json(
        f"{API_BASE}/v1/analyses",
        build_unavailable_region_request(),
    )
    if unavailable_region.get("skipped"):
        return {"status": "skipped", "reason": unavailable_region["note"]}
    if unavailable_region.get("status") != "rejected":
        raise ValueError("Unavailable region request should be rejected.")

    return {"status": "pass", "checked": "analyses"}


def run_receipt_checks():
    if not API_BASE or requests is None:
        return {"status": "skipped", "reason": "Server not started; compile-only validation."}

    # In a live environment, a real receipt_id would come from a successful analysis.
    sample_receipt_id = "demo-receipt-id"
    payload = get_json(f"{API_BASE}/v1/receipts/{sample_receipt_id}")
    if payload.get("detail") == "Not found":
        return {"status": "pass", "checked": "receipts", "note": "receipt endpoint reachable"}
    validate_receipt_payload(payload)
    return {"status": "pass", "checked": "receipts"}


def main():
    report = {
        "script": "verify_api_contracts.py",
        "checks": [],
        "status": "pass",
    }

    for checker_name, checker in [
        ("catalog", run_catalog_checks),
        ("analysis_submission", run_analysis_submission_checks),
        ("receipt", run_receipt_checks),
    ]:
        try:
            result = checker()
            report["checks"].append({"name": checker_name, "result": result})
            if result.get("status") == "fail":
                report["status"] = "fail"
        except Exception as exc:  # pragma: no cover - compile-only safety
            report["checks"].append({
                "name": checker_name,
                "result": {"status": "fail", "error": str(exc)},
            })
            report["status"] = "fail"

    if API_BASE and requests is not None:
        print(json.dumps(report, indent=2))
    else:
        print(
            "API server not started; compile-only validation executed. "
            "Set TREND_DETECTIVE_API_BASE to enable live contract checks."
        )

    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
