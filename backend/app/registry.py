"""Runtime registry: the only source of what the API is allowed to serve.

Reads the versioned JSON files produced by Roles 01 and 02. Nothing here
invents availability: a variable/region pair is servable only when both
measurement_ready and method_ready are true.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from . import config, canonical

SCOPE_PATH = config.REPO_DIR / "docs" / "architecture" / "scope.v2.json"
CATALOG_PATH = config.DATA_DIR / "runtime_catalog.json"
COVERAGE_PATH = config.DATA_DIR / "coverage_report.json"
METHOD_PATH = config.DATA_DIR / "analysis" / "method_config.json"
QA_PATH = config.DATA_DIR / "qa_policy.json"


class Registry:
    def __init__(self) -> None:
        self.scope = json.loads(SCOPE_PATH.read_text(encoding="utf-8"))
        self.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        self.coverage = json.loads(COVERAGE_PATH.read_text(encoding="utf-8"))
        self.method = json.loads(METHOD_PATH.read_text(encoding="utf-8"))
        self.qa = json.loads(QA_PATH.read_text(encoding="utf-8"))
        self.revision = canonical.sha256_bytes(
            b"|".join(p.read_bytes() for p in
                      (SCOPE_PATH, CATALOG_PATH, COVERAGE_PATH,
                       METHOD_PATH, QA_PATH)))
        self.method_revision = (config.METHOD_REVISION_OVERRIDE or
                                self.method["method_revision"])
        self._entries = self._build_entries()

    def _build_entries(self) -> list[dict]:
        scope_entries = {(e["variable_id"], e["region_id"]): e
                         for e in self.scope["entries"]}
        regions = {r["id"]: r for r in self.scope["regions"]}
        out = []
        for item in self.catalog:
            vid = item.get("variable_id")
            rid = item.get("region_id")
            if not vid or not rid:
                continue
            scope = scope_entries.get((vid, rid))
            if not scope:
                continue
            cube = item["path"]
            cov = self.coverage["cubes"].get(f"{item['product_id']}/{rid}", {})
            out.append({
                "variable_id": vid,
                "region_id": rid,
                "product_id": item["product_id"],
                "version": item.get("version"),
                "units": item["units"],
                "label": item.get("label"),
                "bbox": regions[rid]["bbox"],
                "native_grid": item.get("native_grid"),
                "cube_path": cube,
                "cube_sha256": cov.get("sha256"),
                "manifest_path": cube,
                "measurement_ready": bool(scope.get("measurement_ready")),
                "method_ready": bool(scope.get("method_ready")),
                "app_available": bool(scope.get("app_available")),
                "method_revision": scope.get("method_revision",
                                              self.method["method_revision"]),
                "source_kind": item.get("source_kind"),
                "limitations": item.get("limitations", []),
                "evidence_card": scope.get("evidence_card"),
                "spatial_trend": scope.get("spatial_trend"),
            })
        return out

    # ---------------------------------------------------------------- api
    def entries(self) -> list[dict]:
        return list(self._entries)

    def get(self, variable_id: str, region_id: str) -> dict | None:
        for e in self._entries:
            if e["variable_id"] == variable_id and e["region_id"] == region_id:
                return e
        return None

    def servable(self, variable_id: str, region_id: str) -> dict | None:
        e = self.get(variable_id, region_id)
        if not e:
            return None
        if not (e["measurement_ready"] and e["method_ready"]):
            return None
        return e

    def bbox_for(self, region_id: str) -> tuple | None:
        for r in self.scope["regions"]:
            if r["id"] == region_id:
                return tuple(r["bbox"])
        return None

    def cell_deg(self, entry: dict) -> float:
        grid = entry.get("native_grid") or {}
        try:
            return float(str(grid.get("lat")).split()[0])
        except (TypeError, ValueError, AttributeError):
            return 0.5

    def defaults(self) -> dict:
        return {
            "aggregation_policy_id": self.method["aggregation"]["policy_id"],
            "method_revision": self.method_revision,
            "data_revision": self.revision,
        }

    def method_summary(self) -> dict:
        return {
            "method_revision": self.method_revision,
            "alpha": self.method["inference"]["alpha"],
            "basis": self.method["inference"]["basis"],
            "aggregation": self.method["aggregation"],
            "dependence": self.method["dependence"],
            "bootstrap": self.method["bootstrap"],
            "multiplicity": self.method["multiplicity"],
            "minimum_series": self.method["minimum_series"],
            "period_sensitivity": self.method["period_sensitivity"],
        }


@lru_cache(maxsize=1)
def load_registry() -> Registry:
    return Registry()


def reset_registry() -> None:
    load_registry.cache_clear()
