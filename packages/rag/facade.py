"""Unified Role 04 entrypoint for Role 03/05/06 integration.

`Role04Service` ties the two Role 04 paths together behind one surface:

1. Concept/variable Q&A: Phase 1 provenance/registry + Phase 2 bilingual BM25
   retrieval + Phase 3 Gemini provider behind the strict zero-trust validator,
   with seamless offline `local_retrieval` fallback (never requires the LLM).
2. Statistical conclusions: Phase 4 deterministic bilingual interactive
   conclusion templates with ActiveRequestTracker stale-response protection.

`normalize_result_payload` is the single adapter point for Role 03 result
payloads: documented field-alias differences between IMPLEMENTATION.md and
Role 03's live output are mapped here, in one place, without touching the
template logic in conclusions.py. `live_probe` runs one bounded live Gemini
request only when a server-side key is configured; otherwise it skips cleanly.
"""

import copy
import time

from .conclusions import ActiveRequestTracker, render_conclusions
from .explanation import ExplanationPipeline
from .provider import GeminiClient
from .retriever import Retriever

ALIAS_RULES = {
    "analysis_id": ("analysis_id", "result_id", "job_id"),
    "request_id": ("request_id", "request_hash"),
    "region_id": ("region_id", "region"),
    "variable_id": ("variable_id", "variable"),
    "units": ("units", "unit"),
    "receipt_id": ("receipt_id", "receipt"),
    "result_state": ("result_state", "state"),
    "method_revision": ("method_revision", "method"),
    "data_revision": ("data_revision", "data_revision_id"),
}

ARTIFACT_ALIASES = {
    "regional_chart": ("regional_chart", "chart", "regional_chart_available"),
    "cell_reveal": ("cell_reveal", "cells", "cell_reveal_available", "reveal_cells"),
    "spin_it": ("spin_it", "spin_it_available"),
    "receipt": ("receipt", "receipt_available"),
}

REGIONAL_ALIASES = {
    "mean": ("mean", "regional_mean", "average"),
    "n_months": ("n_months", "months", "sample_size"),
    "sen_slope": ("sen_slope", "slope"),
    "slope_units": ("slope_units", "slope_unit"),
    "p_value": ("p_value", "p"),
    "significance_alpha": ("significance_alpha", "alpha"),
    "confidence_interval": ("confidence_interval", "ci"),
    "inference_reason_code": ("inference_reason_code", "null_reason"),
}

CELLS_ALIASES = {
    "denominator": ("denominator",),
    "ineligible_qa_cells": ("ineligible_qa_cells", "masked_cells", "ineligible_cells"),
    "total_cells": ("total_cells", "total"),
    "eligible_cells": ("eligible_cells", "eligible"),
    "increasing_cells": ("increasing_cells", "increasing"),
    "decreasing_cells": ("decreasing_cells", "decreasing"),
    "non_significant_cells": ("non_significant_cells", "non_significant"),
    "increasing_weighted_fraction": ("increasing_weighted_fraction",),
    "decreasing_weighted_fraction": ("decreasing_weighted_fraction",),
}

COVERAGE_ALIASES = {
    "valid_area_fraction": ("valid_area_fraction", "valid_fraction"),
    "denominator": ("denominator",),
    "ineligible_cells": ("ineligible_cells", "masked_cells"),
}

SENSITIVITY_ALIASES = {
    "matching_windows": ("matching_windows", "agreeing_windows"),
    "total_windows": ("total_windows", "windows"),
}


def _pick(source, names):
    if not isinstance(source, dict):
        return None
    for name in names:
        if source.get(name) is not None:
            return source[name]
    return None


def _map_block(source, aliases):
    out = {}
    for canonical, names in aliases.items():
        value = _pick(source, names)
        if value is not None:
            out[canonical] = value
    return out


def normalize_result_payload(raw):
    if not isinstance(raw, dict):
        raise ValueError("result payload must be an object")
    payload = {}
    for canonical, aliases in ALIAS_RULES.items():
        value = _pick(raw, aliases)
        if value is not None:
            payload[canonical] = value

    period = raw.get("period")
    start = _pick(raw, ("start_month", "start", "period_start"))
    end = _pick(raw, ("end_month", "end", "period_end"))
    if isinstance(period, dict):
        payload["period"] = {
            "start_month": period.get("start_month") or period.get("start") or start,
            "end_month": period.get("end_month") or period.get("end") or end,
        }
    elif period is not None:
        payload["period"] = period
    elif start is not None and end is not None:
        payload["period"] = {"start_month": start, "end_month": end}

    product_block = raw.get("product") if isinstance(raw.get("product"), dict) else None
    if product_block is None and isinstance(raw.get("source"), dict):
        product_block = raw["source"]
    if product_block is None and (raw.get("product_id") or raw.get("product_version")):
        product_block = {"product_id": raw.get("product_id"), "product_version": raw.get("product_version")}
    if product_block is not None:
        payload["product"] = {
            "product_id": _pick(product_block, ("product_id", "id")),
            "product_version": _pick(product_block, ("product_version", "version")),
            "source_type": product_block.get("source_type"),
        }

    regional = raw.get("regional") if isinstance(raw.get("regional"), dict) else {}
    mapped_regional = _map_block(regional, REGIONAL_ALIASES)
    for canonical, names in REGIONAL_ALIASES.items():
        if canonical not in mapped_regional:
            value = _pick(raw, names)
            if value is not None:
                mapped_regional[canonical] = value
    if mapped_regional:
        payload["regional"] = mapped_regional

    cells_block = raw.get("cells") if isinstance(raw.get("cells"), dict) else None
    if cells_block is None and isinstance(raw.get("cell_distribution"), dict):
        cells_block = raw["cell_distribution"]
    if cells_block is not None:
        payload["cells"] = _map_block(cells_block, CELLS_ALIASES)

    coverage_block = raw.get("coverage") if isinstance(raw.get("coverage"), dict) else None
    if coverage_block is None and isinstance(raw.get("qa_coverage"), dict):
        coverage_block = raw["qa_coverage"]
    if coverage_block is not None:
        payload["coverage"] = _map_block(coverage_block, COVERAGE_ALIASES)

    sensitivity_block = raw.get("sensitivity") if isinstance(raw.get("sensitivity"), dict) else None
    if sensitivity_block is None and isinstance(raw.get("spin_it_summary"), dict):
        sensitivity_block = raw["spin_it_summary"]
    if sensitivity_block is not None:
        payload["sensitivity"] = _map_block(sensitivity_block, SENSITIVITY_ALIASES)

    artifacts_block = raw.get("artifacts") if isinstance(raw.get("artifacts"), dict) else None
    if artifacts_block is None and isinstance(raw.get("availability_flags"), dict):
        artifacts_block = raw["availability_flags"]
    if artifacts_block is not None:
        mapped_artifacts = _map_block(artifacts_block, ARTIFACT_ALIASES)
        if mapped_artifacts:
            payload["artifacts"] = mapped_artifacts

    if isinstance(raw.get("comparison"), dict):
        payload["comparison"] = raw["comparison"]

    return payload


class Role04Service:
    """Single Role 04 integration surface.

    answer_question(): concept/variable Q&A path (deterministic retrieval;
    LLM explanation only when configured, always validated, offline fallback).
    register_analysis()/render_result(): statistical conclusion path with
    stale-response protection; payloads may arrive in any documented alias
    form and are normalized before rendering.
    """

    def __init__(self, provider=None, retriever=None):
        self.retriever = retriever or Retriever()
        self.provider = provider or GeminiClient()
        self.pipeline = ExplanationPipeline(provider=self.provider, retriever=self.retriever)
        self.tracker = ActiveRequestTracker()

    def answer_question(self, query, region_id=None, period=None, data_revision=None):
        return self.pipeline.explain(query, region_id=region_id, period=period, data_revision=data_revision)

    def register_analysis(self, raw_payload, variable_ids=None):
        payload = normalize_result_payload(raw_payload)
        registered_variables = list(variable_ids) if variable_ids else (
            [payload["variable_id"]] if payload.get("variable_id") else []
        )
        return self.tracker.register(
            payload.get("analysis_id"),
            payload.get("request_id"),
            payload.get("region_id"),
            registered_variables,
            payload.get("period"),
        )

    def reset_session(self):
        self.tracker = ActiveRequestTracker()

    def render_result(self, raw_payload, language="en", normalize=True):
        payload = normalize_result_payload(raw_payload) if normalize else copy.deepcopy(raw_payload)
        tracker = self.tracker if self.tracker.current is not None else None
        return render_conclusions(payload, language=language, tracker=tracker)

    def render_assessment(self, assessment, language="en"):
        """Current typed result path: assessed facts -> shared bilingual templates."""
        from .result_templates import render_assessment
        return render_assessment(assessment, language)

    def live_probe(self, question, region_id=None, period=None):
        if not self.provider.is_configured():
            return {
                "status": "skipped",
                "mode": "skipped",
                "reason": "GEMINI_API_KEY is not configured; live probe skipped cleanly",
            }
        started = time.perf_counter()
        result = self.pipeline.explain(question, region_id=region_id, period=period)
        result["probe_elapsed_seconds"] = round(time.perf_counter() - started, 2)
        return result
