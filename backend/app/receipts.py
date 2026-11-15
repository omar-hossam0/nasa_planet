"""Receipt construction.

A receipt is only ever written for a succeeded analysis, and it never carries
credentials. Keys that look secret are stripped before hashing and storage.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from . import canonical, config, db, registry

SECRET_PATTERN = re.compile(
    r"(token|secret|password|passwd|api[_-]?key|authorization|bearer|"
    r"credential|netrc|cookie)", re.IGNORECASE)


def redact(obj):
    """Remove any key that looks like a credential, recursively."""
    if isinstance(obj, dict):
        return {k: redact(v) for k, v in obj.items()
                if not SECRET_PATTERN.search(str(k))}
    if isinstance(obj, list):
        return [redact(v) for v in obj]
    return obj


def build(job: dict, request: dict, per_variable: list[dict],
          spatial_mask: dict) -> dict:
    reg = registry.load_registry()
    qa_sha = canonical.sha256_file(registry.QA_PATH)
    method_sha = canonical.sha256_file(registry.METHOD_PATH)
    sources = []
    for v in per_variable:
        entry = reg.get(v["variable_id"], request["region_id"]) or {}
        granules = v.pop("_granules", [])
        sources.append({
            "variable_id": v["variable_id"],
            "product_id": v.get("product_id"),
            "version": v.get("version"),
            "cube_path": entry.get("cube_path"),
            "cube_sha256": entry.get("cube_sha256"),
            "granules": granules,
            "granule_count": len(granules),
        })
    payload = {
        "request": request,
        "request_hash": job["request_hash"],
        "data_revision": job["data_revision"],
        "method_revision": job["method_revision"],
        "software_revision": config.SOFTWARE_REVISION,
        "sources": sources,
        "qa_policy": {
            "mode": reg.method["qa"]["mode"],
            "policy_version": reg.qa["policy_version"],
            "policy_sha256": qa_sha,
        },
        "method_config_sha256": method_sha,
        "spatial_mask": spatial_mask,
        "aggregation_policy": reg.method["aggregation"],
        "anomaly_baseline": reg.method["seasonal_adjustment"],
        "trend_method": {
            "test": "seasonal_mann_kendall",
            "season_period": reg.method["inference"]["season_period"],
            "alpha": reg.method["inference"]["alpha"],
            "two_sided": reg.method["inference"]["two_sided"],
            "slope": "theil_sen on seasonal anomalies",
        },
        "dependence": reg.method["dependence"],
        "bootstrap": reg.method["bootstrap"],
        "multiplicity": reg.method["multiplicity"],
        "minimum_series": reg.method["minimum_series"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    return redact(payload)
