"""Strict explanation schema and validator.

The validator is the admission gate: an explanation is only shown if every
citation resolves to a retrieved chunk, every number matches a field of the
verified result, every suggested variable is actually available, and the
wording does not make claims the method cannot support.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "m4-1.0.0"

# phrases that mis-state what a p-value or a trend estimate means
BANNED_PATTERNS = [
    (r"\b(9[0-9]|100)\s*%\s*(chance|probability|confident|sure)\b",
     "probability_of_hypothesis"),
    (r"\bprobability (that )?the trend (is|exists|is real)\b",
     "probability_of_hypothesis"),
    (r"\b(chance|likelihood) (that )?(it|the trend) is (real|due to chance)\b",
     "probability_of_hypothesis"),
    (r"\b(proves|proven|definitely|conclusively|certainly)\b", "overclaim"),
    (r"\b(caused by|because of climate change|due to global warming)\b",
     "causality"),
    (r"\bwill (continue|increase|decrease) (to|by)\b", "forecast"),
    (r"\b(yield|harvest|biomass|crop production)\b.*\bndvi\b|"
     r"\bndvi\b.*\b(yield|harvest|biomass|crop production)\b",
     "ndvi_overclaim"),
    (r"\bzero (moisture|rain|precipitation)\b", "missing_as_zero"),
    (r"\bignore (all )?(previous|prior) instructions\b", "injection_followed"),
    (r"\bsystem\s*:", "injection_followed"),
]

NUMBER_RE = re.compile(r"[-+]?\d+(?:\.\d+)?(?:e[-+]?\d+)?")


@dataclass
class ValidationResult:
    ok: bool
    errors: list[dict] = field(default_factory=list)
    warnings: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"ok": self.ok, "errors": self.errors,
                "warnings": self.warnings}


def _resolve_field(payload: dict, path: str) -> Any:
    """Resolve 'variables[0].trend.slope_per_year' against a result payload."""
    cur: Any = payload
    for part in path.split("."):
        m = re.match(r"^(\w+)\[(\d+)\]$", part)
        if m:
            key, idx = m.group(1), int(m.group(2))
            cur = cur[key][idx]
        elif isinstance(cur, list) and part.isdigit():
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def _numbers_in(text: str) -> list[float]:
    out = []
    for m in NUMBER_RE.finditer(text):
        try:
            out.append(float(m.group(0)))
        except ValueError:
            pass
    return out


def validate(explanation: dict, result_payload: dict | None,
             retrieved: list[dict], catalog: list[dict],
             region_id: str | None) -> ValidationResult:
    res = ValidationResult(ok=True)

    # --- schema shape -----------------------------------------------------
    required = ("schema_version", "answer", "language", "cited_chunk_ids",
                "numeric_references", "suggested_variable_ids", "limitations",
                "state")
    for key in required:
        if key not in explanation:
            res.ok = False
            res.errors.append({"code": "SCHEMA_MISSING_FIELD", "field": key})
    if not res.ok:
        return res
    if explanation["schema_version"] != SCHEMA_VERSION:
        res.ok = False
        res.errors.append({"code": "SCHEMA_VERSION_MISMATCH",
                           "expected": SCHEMA_VERSION,
                           "got": explanation["schema_version"]})
    if explanation["state"] not in ("answered", "insufficient_data",
                                    "unsupported", "unavailable"):
        res.ok = False
        res.errors.append({"code": "INVALID_STATE",
                           "state": explanation["state"]})
    if explanation["language"] not in ("ar", "en"):
        res.ok = False
        res.errors.append({"code": "INVALID_LANGUAGE"})

    # --- citations must resolve to retrieved chunks ------------------------
    retrieved_ids = {r["chunk_id"] for r in retrieved}
    for cid in explanation["cited_chunk_ids"]:
        if cid not in retrieved_ids:
            res.ok = False
            res.errors.append({"code": "CITATION_NOT_RETRIEVED",
                               "chunk_id": cid})

    # --- numbers must come from the verified result -----------------------
    covered = []
    for ref in explanation["numeric_references"]:
        try:
            actual = _resolve_field(result_payload or {}, ref["field"])
        except (KeyError, IndexError, TypeError):
            res.ok = False
            res.errors.append({"code": "NUMERIC_FIELD_NOT_FOUND",
                               "field": ref.get("field")})
            continue
        if actual is None:
            res.ok = False
            res.errors.append({"code": "NUMERIC_FIELD_IS_NULL",
                               "field": ref.get("field")})
            continue
        try:
            if abs(float(actual) - float(ref["value"])) > 1e-9 * max(
                    1.0, abs(float(actual))):
                res.ok = False
                res.errors.append({
                    "code": "NUMERIC_VALUE_MISMATCH",
                    "field": ref["field"], "expected": actual,
                    "got": ref["value"]})
                continue
        except (TypeError, ValueError):
            res.ok = False
            res.errors.append({"code": "NUMERIC_VALUE_NOT_A_NUMBER",
                               "field": ref.get("field")})
            continue
        covered.append(float(actual))

    # any other number in the prose must be a year/percentage from the result
    # a number in prose is acceptable if it is a rounded rendering of a
    # referenced field value; method constants from the frozen config are
    # also acceptable because they are not result numbers
    allowed = {0.05, 95.0, 5.0, 12.0, 60.0, 48.0, 80.0, 0.8}
    for v in covered:
        for d in range(1, 11):
            allowed.add(round(abs(v), d))
        allowed.add(abs(v))
    if result_payload:
        for var in result_payload.get("variables", []):
            allowed.add(float(var["period"]["start"][:4]))
            allowed.add(float(var["period"]["end"][:4]))
            allowed.add(float(var["counts"]["months"]))
            pct = float(var["counts"]["valid_fraction"]) * 100
            for d in range(1, 8):
                allowed.add(round(pct, d))
            allowed.add(float(var["counts"]["cells"]))
    for num in _numbers_in(explanation["answer"]):
        if round(abs(num), 12) in allowed:
            continue
        if abs(num) in (0.05, 95.0, 5.0, 12.0):   # alpha, CI level, %, block
            continue
        res.ok = False
        res.errors.append({"code": "UNREFERENCED_NUMBER", "number": num})

    # --- suggestions must be available ------------------------------------
    available = {(c["variable_id"], c["region_id"]) for c in catalog
                 if c["measurement_ready"] and c["method_ready"]}
    for vid in explanation["suggested_variable_ids"]:
        if region_id is None:
            break
        if (vid, region_id) not in available:
            res.ok = False
            res.errors.append({"code": "SUGGESTION_UNAVAILABLE",
                               "variable_id": vid, "region_id": region_id})

    # --- wording -----------------------------------------------------------
    text = explanation["answer"]
    for pattern, code in BANNED_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            res.ok = False
            res.errors.append({"code": "BANNED_PHRASING", "rule": code,
                               "pattern": pattern})

    # --- state consistency -------------------------------------------------
    if explanation["state"] == "insufficient_data":
        if explanation["numeric_references"]:
            res.ok = False
            res.errors.append({"code": "NUMBERS_WITH_INSUFFICIENT_DATA"})
        if not explanation["limitations"]:
            res.warnings.append({"code": "MISSING_LIMITATIONS"})
    if explanation["state"] == "answered" and not explanation["limitations"]:
        res.warnings.append({"code": "MISSING_LIMITATIONS"})

    return res


def load_catalog() -> list[dict]:
    root = Path(__file__).resolve().parent.parent
    scope = json.loads((root / "docs" / "architecture" / "scope.v2.json")
                       .read_text(encoding="utf-8"))
    return [{"variable_id": e["variable_id"], "region_id": e["region_id"],
             "measurement_ready": e["measurement_ready"],
             "method_ready": e["method_ready"]}
            for e in scope["entries"]]
