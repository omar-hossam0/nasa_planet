# API Contract — v1 (mock milestone)

Base URL: `http://127.0.0.1:8000` · Prefix: `/v1` · Content type: `application/json`

All responses are Pydantic-validated. Every payload carries `data_mode: "mock"` and a
`disclaimer` where a scientific claim could otherwise be implied.

---

## 1. Conventions

### Dates
`YYYY-MM` only (e.g. `2005-01`). Validated by regex; `start_month <= end_month`.

### AOI
```json
{ "type": "bbox", "coordinates": [west, south, east, north] }
```
WGS84 degrees. Order is enforced: `west < east`, `south < north`,
longitude ∈ [-180, 180], latitude ∈ [-90, 90]. Only `bbox` is approved; polygons are
deferred until the team agrees on GeoJSON constraints.

### Error envelope
Every failure returns this shape — never a stack trace:

```json
{
  "error": {
    "code": "DATA_NOT_AVAILABLE",
    "message": "The requested period is outside the declared coverage 2001-01..2024-12.",
    "details": { "requested": ["1990-01", "1995-12"] },
    "request_id": "req_9f2c1ab34d07"
  }
}
```

`X-Request-ID` is echoed on every response; supply your own header to correlate logs.

### Status codes

| Code | Used for |
|---|---|
| 200 | Successful retrieval; also cached analysis reuse |
| 202 | New analysis / Spin It accepted |
| 404 | Unknown variable, region, job, result, cell, receipt, spin |
| 409 | Data unavailable, incomplete result, incomparable cells |
| 422 | Validation failure, invalid AOI/period/policy/window/language |
| 500 | Unexpected internal error (generic message only) |
| 503 | Capability unavailable (real adapters not delivered) |

### Error codes

| Code | HTTP | Meaning |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Pydantic/schema validation failed; `details.errors[]` lists fields |
| `VARIABLE_NOT_FOUND` | 404 | Unknown `variable_id`; `details.known_variable_ids` |
| `REGION_NOT_FOUND` | 404 | Unknown `region_id`; `details.known_region_ids` |
| `JOB_NOT_FOUND` | 404 | Unknown `job_id` |
| `RESULT_NOT_FOUND` | 404 | Unknown `result_id` |
| `CELL_NOT_FOUND` | 404 | Cell does not exist in that result |
| `RECEIPT_NOT_FOUND` | 404 | Unknown `receipt_id` |
| `SPIN_NOT_FOUND` | 404 | Unknown `spin_id` |
| `INVALID_AOI` | 422 | Bbox malformed, inverted, or outside configured span limits |
| `INVALID_PERIOD` | 422 | Period span outside configured limits, or inverted |
| `DATA_NOT_AVAILABLE` | 409 | Requested combination is not usable |
| `RESULT_NOT_COMPLETE` | 409 | Job not completed, so no result exists |
| `INCOMPATIBLE_COMPARISON` | 409 | Missing-data cell, or unsupported comparison |
| `INVALID_SPIN_WINDOW` | 422 | Window does not fit the base result period |
| `UNSUPPORTED_LANGUAGE` | 422 | Language outside `en` / `ar` |
| `UNSUPPORTED_AGGREGATION_POLICY` | 422 | Policy outside `area_weighted` / `cell_mean` |
| `MOCK_MODE_DISABLED` | 503 | Mock capability requested while mock mode is off |
| `INTERNAL_ERROR` | 500 | Unhandled error |

### Identifier strategy
Deterministic, derived from the canonical request hash:

```text
job_mock_<8 hex>      result_mock_<8 hex>    receipt_mock_<8 hex>
spin_mock_<8 hex>     cmp_mock_<8 hex>       expl_mock_<8 hex>
cell_01 .. cell_09    window_01 .. window_NN
```

Identical requests therefore yield identical identifiers, which makes tests and demos
reproducible.

---

## 2. System

### `GET /health`
```json
{ "status": "ok", "app_name": "Trend Detective Backend", "version": "0.1.0",
  "environment": "development", "mock_mode": true, "message": "Service is running." }
```

### `GET /ready`
```json
{
  "status": "ok", "api_running": true, "mock_services_available": true,
  "mock_mode": true, "environment": "development",
  "integrations": [
    { "name": "database",          "state": "not_integrated", "detail": "..." },
    { "name": "statistics_engine", "state": "mock",           "detail": "..." },
    { "name": "rag_service",       "state": "mock",           "detail": "..." },
    { "name": "nasa_data",         "state": "mock",           "detail": "..." },
    { "name": "job_queue",         "state": "mock",           "detail": "..." },
    { "name": "frontend",          "state": "not_integrated", "detail": "..." }
  ],
  "notes": ["Ready to serve mock-backed requests.", "..."]
}
```
`state` is one of `mock | not_integrated | connected | unavailable`. Nothing is reported
as `connected` in this milestone.

---

## 3. Catalog

### `GET /v1/catalog`
Returns `variables[]`, `count`, `data_mode`, `disclaimer`, `registry_snapshot`, `warnings[]`.

Each variable:
```json
{
  "variable_id": "air_temperature",
  "display_name": "2-metre air temperature",
  "description": "...",
  "unit": "K",
  "units_verified": true,
  "unit_source": "data/nasa/runtime_catalog.json (units field for T2M)",
  "source": { "product_id": "M2TMNXSLV", "version": "5.12.4",
              "source_variable": "T2M", "provider": "NASA GES DISC (MERRA-2)",
              "documentation_url": null, "lineage_note": "..." },
  "availability_state": "measurement_ready",
  "measurement_ready": true, "method_ready": false, "app_available": false,
  "demo_available": true, "demo_only": true, "data_mode": "mock"
}
```

`availability_state` distinguishes `catalogued` < `measurement_ready` < `analysis_ready`.
A catalogued variable is **not** automatically analysis-ready.

### `GET /v1/catalog/variables/{variable_id}`
Adds `aliases[]`, `supported_regions[]`, `coverage_start`, `coverage_end`,
`native_grid`, `limitations[]`, `warnings[]`. Accepts aliases (`T2M`, `ndvi`, ...).

### `GET /v1/catalog/regions`
```json
{ "region_id": "nile_corridor", "display_name": "Nile corridor (Egypt rectangle)",
  "description": "...", "bbox": [29.0, 24.0, 33.0, 32.0],
  "period_start": "2001-01", "period_end": "2024-12",
  "supported_variable_ids": ["air_temperature", "soil_moisture", "precipitation", "vegetation_greenness"],
  "demo_only": true, "data_mode": "mock", "warnings": ["..."] }
```

### `GET /v1/catalog/availability`
Query: `variable_id`, `region_id`, `start_month`, `end_month`, optional `bbox=w,s,e,n`.

```json
{
  "variable_id": "air_temperature", "region_id": "nile_corridor",
  "start_month": "2005-01", "end_month": "2020-12", "aoi": null,
  "measurement_ready": true, "method_ready": false, "app_available": false,
  "demo_available": true, "usable": true,
  "reason_code": "MOCK_DEMO_ONLY",
  "reason_message": "Usable for the mock demonstration only. ...",
  "availability_source": "registry_snapshot + mock_demo_gate",
  "simulated": true,
  "supported_aggregation_policies": ["area_weighted", "cell_mean"],
  "data_mode": "mock", "warnings": ["..."]
}
```

`reason_code`: `DEMO_READY | MOCK_DEMO_ONLY | METHOD_NOT_APPROVED | OUTSIDE_COVERAGE |
UNKNOWN_VARIABLE | UNKNOWN_REGION | INVALID_PERIOD | INVALID_AOI`.

---

## 4. Recommendations

### `POST /v1/recommendations`
```json
{ "question": "I want to study temperature changes.", "language": "en",
  "region_id": "nile_corridor", "start_month": "2005-01", "end_month": "2020-12" }
```

```json
{
  "status": "recommended",
  "question": "I want to study temperature changes.",
  "language": "en",
  "candidates": [
    { "variable_id": "air_temperature", "display_name": "2-metre air temperature",
      "unit": "K", "confidence": 0.85,
      "rationale": "The question mentions temperature or warming.",
      "demo_available": true, "measurement_ready": true }
  ],
  "clarification_question": null,
  "message": "Deterministic keyword match against the demo catalog. No retrieval or model was used.",
  "context": { "region_id": "nile_corridor", "region_known": true,
               "start_month": "2005-01", "end_month": "2020-12" },
  "references": [],
  "provider": "mock_rules",
  "data_mode": "mock",
  "disclaimer": "Synthetic demonstration data. Not a NASA scientific result.",
  "warnings": ["..."]
}
```

`status`: `recommended | clarification_required | unsupported`.
Bare "moisture"/"humidity"/"رطوبة" returns `clarification_required` — the catalog has
soil moisture but no atmospheric humidity. Unknown region → 404. Unknown language → 422.

---

## 5. Analyses and jobs

### `POST /v1/analyses`
```json
{
  "variable_ids": ["air_temperature"],
  "region_id": "nile_corridor",
  "aoi": { "type": "bbox", "coordinates": [29.0, 24.0, 33.0, 32.0] },
  "start_month": "2005-01",
  "end_month": "2020-12",
  "aggregation_policy": "area_weighted"
}
```

`aoi` is optional (defaults to the region bbox). Extra fields are rejected
(`extra="forbid"`).

**202 Accepted** for new work, **200 OK** when an equivalent analysis already exists:

```json
{
  "job_id": "job_mock_661b1c73", "status": "completed",
  "result_id": "result_mock_661b1c73", "cached": false,
  "data_mode": "mock",
  "disclaimer": "Synthetic demonstration data. Not a NASA scientific result.",
  "links": { "job": "/v1/analyses/job_mock_661b1c73",
             "result": "/v1/results/result_mock_661b1c73" },
  "message": "Analysis accepted and completed synchronously by the mock job manager."
}
```

Cache key covers: sorted variable ids, region, canonical AOI (4 dp), period,
aggregation policy, dataset revision, method version, data mode. Two requests share a
result **only** when all of these match.

Validation order: variables exist → region exists → AOI span → period span →
policy supported → availability gate.

### `GET /v1/analyses/{job_id}`
```json
{
  "job_id": "job_mock_661b1c73", "status": "completed",
  "result_id": "result_mock_661b1c73", "progress_percent": 100,
  "request": { "...": "echo of the accepted body" },
  "resolved_variable_ids": ["air_temperature"],
  "data_mode": "mock", "disclaimer": "...", "warnings": ["..."],
  "state_history": [
    { "status": "queued",    "at": "2026-11-14T21:48:44Z", "message": "Job accepted." },
    { "status": "running",   "at": "2026-11-14T21:48:44Z", "message": "Mock computation started." },
    { "status": "completed", "at": "2026-11-14T21:48:44Z", "message": "Mock result stored." }
  ],
  "error": null,
  "created_at": "...", "updated_at": "...",
  "links": { "job": "...", "result": "..." }
}
```

---

## 6. Results

### `GET /v1/results/{result_id}`
```json
{
  "result_id": "result_mock_661b1c73",
  "job_id": "job_mock_661b1c73",
  "data_mode": "mock",
  "disclaimer": "Synthetic demonstration data. Not a NASA scientific result.",
  "evidence_state": "synthetic_demo",
  "analysis": {
    "variable_ids": ["air_temperature"], "region_id": "nile_corridor",
    "region_display_name": "Nile corridor (Egypt rectangle)",
    "aoi": { "type": "bbox", "coordinates": [29.0, 24.0, 33.0, 32.0] },
    "start_month": "2005-01", "end_month": "2020-12",
    "period_months": 192, "aggregation_policy": "area_weighted"
  },
  "datasets": [
    { "variable_id": "air_temperature", "product_id": "M2TMNXSLV", "version": "5.12.4",
      "source_variable": "T2M",
      "revision": "M2TMNXSLV:5.12.4:nile_corridor:mock",
      "source": "mock_registry_snapshot" }
  ],
  "method": {
    "method_id": "mock_seasonal_linear_v0", "method_version": "0.1.0-mock",
    "aggregation_policy": "area_weighted", "status": "mock_synthetic",
    "approved": false,
    "note": "Mock statistics adapter. Method has not been scientifically reviewed."
  },
  "variables": [
    {
      "variable_id": "air_temperature", "display_name": "2-metre air temperature",
      "unit": "K", "units_verified": true,
      "series": [ { "month": "2005-01", "value": 294.1, "missing": false } ],
      "trend": {
        "method_id": "mock_seasonal_linear_v0", "method_version": "0.1.0-mock",
        "direction": "increasing", "slope_per_year": 0.0252, "slope_unit": "K year-1",
        "intercept": 295.7, "n_months": 192, "n_years": 16,
        "p_value": null, "r_squared": 0.62,
        "inference_status": "not_computed", "evidence_state": "synthetic_demo",
        "notes": ["..."]
      }
    }
  ],
  "warnings": [ { "code": "MOCK_DATA_MODE", "message": "...", "severity": "warning" } ],
  "spatial": { "spatial_url": "/v1/results/result_mock_661b1c73/spatial",
               "cell_count": 9, "missing_cell_count": 1, "grid": "3x3_regular_lonlat" },
  "receipt_id": "receipt_mock_661b1c73",
  "links": { "self_url": "...", "spatial": "...", "receipt": "...", "receipt_download": "..." },
  "created_at": "..."
}
```

`p_value` is always `null` and `inference_status` is always `not_computed` in this
milestone. A non-significant result would not be proof of no change, so no verdict is
offered at all.

---

## 7. Spatial

### `GET /v1/results/{result_id}/spatial`
```json
{
  "result_id": "result_mock_661b1c73", "variable_id": "air_temperature",
  "unit": "K", "trend_unit": "K year-1", "grid": "3x3_regular_lonlat",
  "cell_count": 9, "missing_cell_count": 1,
  "bounds": [29.0, 24.0, 33.0, 32.0],
  "cells": [
    {
      "cell_id": "cell_01", "result_id": "result_mock_661b1c73",
      "variable_id": "air_temperature",
      "bbox": [29.0, 24.0, 30.3333, 26.6667],
      "centroid": [29.6667, 25.3333],
      "geometry": { "type": "Polygon",
                    "coordinates": [[[29.0,24.0],[30.3333,24.0],[30.3333,26.6667],
                                     [29.0,26.6667],[29.0,24.0]]] },
      "trend_value": 0.0281, "trend_unit": "K year-1",
      "direction": "increasing", "evidence_state": "synthetic_demo",
      "missing_data": false, "data_mode": "mock"
    }
  ],
  "data_mode": "mock", "disclaimer": "...", "warnings": []
}
```

`cell_09` is deliberately missing: `trend_value: null`, `missing_data: true`,
`direction: "insufficient_data"`. Clients must render it as missing, never as zero.

### `GET /v1/results/{result_id}/cells/{cell_id}`
Adds `display_name`, `unit`, `trend` (full `TrendSummary`), `series[]`, `warnings[]`.

---

## 8. Comparisons

### `POST /v1/comparisons`
```json
{ "comparison_type": "cells", "result_id": "result_mock_661b1c73",
  "cell_ids": ["cell_01", "cell_04"] }
```
2–4 distinct cell ids. Missing-data cells → 409. Unknown cell → 404.

```json
{
  "comparison_id": "cmp_mock_87ea1893",
  "comparison_type": "cells",
  "result_id": "result_mock_661b1c73",
  "variable_id": "air_temperature", "display_name": "2-metre air temperature",
  "unit": "K", "trend_unit": "K year-1",
  "start_month": "2005-01", "end_month": "2020-12",
  "compatibility": {
    "variable_match": true, "unit_match": true, "period_match": true,
    "method_version_match": true, "dataset_revision_match": true,
    "compatible": true, "notes": ["..."]
  },
  "cells": [ { "cell_id": "cell_01", "label": "cell_01 (29.67, 25.33)",
               "bbox": ["..."], "trend_value": 0.0281, "trend_unit": "K year-1",
               "direction": "increasing", "evidence_state": "synthetic_demo",
               "missing_data": false } ],
  "series": [ { "month": "2005-01", "values": { "cell_01": 294.1, "cell_04": 292.8 } } ],
  "deltas": [ { "cell_id": "cell_01", "difference_from_first": 0.0, "percent_difference": 0.0 } ],
  "summary": "Synthetic slopes for the selected cells - ...",
  "chart_hint": "multi_line",
  "data_mode": "mock", "disclaimer": "...", "warnings": ["..."]
}
```

`comparison_type` is currently restricted to `cells`; `regions` is reserved. The schema
is additive-safe: adding regional comparisons will not break existing clients.

---

## 9. Spin It

### `POST /v1/results/{result_id}/spin` → **202**
```json
{ "minimum_window_years": 10, "start_year_min": 2001, "end_year_max": 2024 }
```
Years must lie inside the base result's covered period, otherwise 422
`INVALID_SPIN_WINDOW` with `details.coverage`.

```json
{ "spin_id": "spin_mock_5240e1cc", "result_id": "result_mock_4503b00a",
  "status": "completed",
  "message": "Spin It computed 14 deterministic mock window(s). The parent result was not modified.",
  "links": { "self_url": "/v1/spin/spin_mock_5240e1cc",
             "result": "/v1/results/result_mock_4503b00a" },
  "data_mode": "mock", "disclaimer": "..." }
```

### `GET /v1/spin/{spin_id}`
```json
{
  "spin_id": "spin_mock_5240e1cc", "result_id": "result_mock_4503b00a",
  "status": "completed",
  "request": { "minimum_window_years": 10, "start_year_min": 2001, "end_year_max": 2024 },
  "variable_id": "air_temperature", "display_name": "2-metre air temperature",
  "unit": "K", "trend_unit": "K year-1",
  "windows": [ { "window_id": "window_01", "start_month": "2001-01",
                 "end_month": "2010-12", "years": 10.0,
                 "trend_value": 0.0494, "direction": "increasing",
                 "evidence_state": "synthetic_demo" } ],
  "summary": { "window_count": 14, "min_trend": 0.0204, "max_trend": 0.0494,
               "mean_trend": 0.0407, "sign_agreement_share": 1.0,
               "note": "Descriptive sensitivity across synthetic windows. Not a statistical test." },
  "data_mode": "mock", "disclaimer": "...", "warnings": ["..."]
}
```

`sign_agreement_share` is descriptive sensitivity, **not** a probability that the trend
is real.

---

## 10. Explanations

### `POST /v1/explanations`
```json
{ "result_id": "result_mock_661b1c73", "language": "en" }
```

```json
{
  "explanation_id": "expl_mock_1a2b3c4d",
  "result_id": "result_mock_661b1c73",
  "language": "en",
  "mode": "mock_template",
  "sections": [
    { "section_id": "summary", "title": "Summary", "body": "For Nile corridor ... " },
    { "section_id": "interpretation", "title": "Interpretation", "body": "..." },
    { "section_id": "spatial_insight", "title": "Spatial insight", "body": "..." },
    { "section_id": "time_window_insight", "title": "Time-window insight", "body": "..." }
  ],
  "actions": [
    { "action_id": "FOCUS_REGION", "label": "Focus region", "enabled": true,
      "payload": { "result_id": "...", "region_id": "nile_corridor" } },
    { "action_id": "FOCUS_REGIONAL_CHART", "label": "Show regional chart", "enabled": true, "payload": {} },
    { "action_id": "REVEAL_CELLS", "label": "Reveal cells", "enabled": true,
      "payload": { "result_id": "...", "spatial_url": "..." } },
    { "action_id": "OPEN_SPIN_IT", "label": "Spin it", "enabled": true,
      "payload": { "result_id": "...", "spin_endpoint": "..." } },
    { "action_id": "OPEN_RECEIPT", "label": "Open receipt", "enabled": true,
      "payload": { "receipt_id": "..." } }
  ],
  "references": [],
  "limitations": ["Synthetic demonstration data, not a NASA scientific result.", "..."],
  "data_mode": "mock",
  "disclaimer": "...",
  "generated_at": "2026-11-14T21:52:32.563Z"
}
```

Numbers in `body` are taken from the stored result. No new number is introduced, and
`references` is empty because nothing was retrieved. Action identifiers are **proposals**
pending confirmation from the frontend owners.

---

## 11. Receipts

### `GET /v1/receipts/{receipt_id}`
```json
{
  "receipt_id": "receipt_mock_661b1c73",
  "receipt_version": "1.0",
  "result_id": "result_mock_661b1c73",
  "job_id": "job_mock_661b1c73",
  "data_mode": "mock",
  "disclaimer": "...",
  "analysis": { "...": "same echo as the result" },
  "variable_ids": ["air_temperature"],
  "region_id": "nile_corridor",
  "aoi": [29.0, 24.0, 33.0, 32.0],
  "start_month": "2005-01", "end_month": "2020-12", "period_months": 192,
  "dataset_revisions": [ { "product_id": "M2TMNXSLV", "version": "5.12.4", "revision": "..." } ],
  "method": { "method_id": "...", "approved": false },
  "provenance": {
    "mode": "mock", "generator": "trend-detective-backend",
    "note": "Mock provenance only. No NASA product revision, granule list or official citation is asserted by this receipt.",
    "registry_snapshot": "scope.v2.json@2026-11-14 + runtime_catalog.json@2026-11-14",
    "statistics_adapter": "MockStatisticsAdapter"
  },
  "warnings": [ "..." ],
  "generated_at": "...",
  "content_hash": "<sha256 of the canonical receipt body>",
  "links": { "self_url": "...", "download": "...", "result": "..." }
}
```

`content_hash` is sha256 over the canonical JSON body excluding `content_hash` and
`links`. It is stable across repeated reads.

### `GET /v1/receipts/{receipt_id}/download`
Returns the identical document as a JSON attachment:

```text
Content-Type: application/json
Content-Disposition: attachment; filename="receipt_mock_661b1c73.json"
X-Receipt-Content-Hash: <sha256>
```

No PDF generation.
