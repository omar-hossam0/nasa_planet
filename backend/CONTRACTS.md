# API contract (published for Members 4, 5 and 6)

Software revision **m3-1.0.0** · data revision from `GET /health` · method
revision **m2-1.0.0**

Start locally:

```bash
cd backend
python run.py                    # http://127.0.0.1:8000
# interactive docs: http://127.0.0.1:8000/docs
```

`openapi.json` in this folder is the generated schema — treat it as the source
of truth for field names. Do not invent endpoints.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | revisions, queue depth, database path |
| GET | `/v1/catalog` | what may be offered to a user, with readiness flags |
| GET | `/v1/methods` | frozen method config snapshot |
| POST | `/v1/analyses` | submit an analysis (idempotent) |
| GET | `/v1/analyses/{job_id}` | poll state and progress |
| GET | `/v1/analyses/{job_id}/result` | result payload |
| GET | `/v1/receipts/{receipt_id}` | immutable receipt |
| GET | `/v1/analyses/{job_id}/explanation?language=ar\|en` | grounded explanation + citations (Member 4) |
| GET | `/v1/spatial/{variable_id}/{region_id}` | per-cell slope + FDR on the native grid (Member 5) |
| GET | `/v1/analyses/{job_id}/series` | monthly series + server trend line (chart) |
| POST | `/v1/compare` | same variable/period across the three windows |
| GET | `/app/` | the map UI (static, no build step) |
| GET | `/product/` | React landing and analysis workspace (built from `frontend/`) |

## Request

```json
{
  "region_id": "nile_corridor",
  "variable_ids": ["air_temperature"],
  "start_month": "2001-01",
  "end_month": "2024-12",
  "aoi": null,
  "aggregation_policy_id": null,
  "method_revision": null,
  "data_revision": null
}
```

`aoi` is an optional GeoJSON Polygon in **lon/lat** order. Rings may start
anywhere and may be clockwise or counter-clockwise: they are normalized before
hashing, so two spellings of the same area return the same job.

`region_id` values: `nile_corridor`, `morocco_comparison`, `sahel_comparison`.
`variable_ids` values: `air_temperature`, `soil_moisture`, `precipitation`,
`vegetation_greenness` (max 4 per request).

## States

| state | meaning | UI treatment |
|---|---|---|
| `queued` / `running` | job accepted | progress bar from `progress` |
| `succeeded` | result exists | show slope, interval, coverage |
| `insufficient_data` | coverage rule rejected the series | its own state, no number |
| `failed` | see `error.code` | error state, no result, **no receipt** |

Result states are per variable inside `payload.variables[]`; the top-level
`payload.state` is `insufficient_data` only when every variable is.

## Error codes (HTTP 400/404/409)

`UNKNOWN_REGION`, `UNSUPPORTED_VARIABLE`, `UNAVAILABLE_SOURCE`,
`INVALID_PERIOD`, `INVALID_GEOMETRY`, `SELF_INTERSECTING`, `OUT_OF_BOUNDS`,
`AREA_TOO_SMALL`, `AREA_TOO_LARGE`, `EXCESSIVE_COMPUTE`, `EMPTY_AOI`,
`METHOD_REVISION_MISMATCH`, `DATA_REVISION_MISMATCH`, `JOB_NOT_FOUND`,
`JOB_FAILED`, `RESULT_NOT_READY`, `RECEIPT_NOT_FOUND`.

All errors use `{"error": {"code": "...", "detail": "..."}}`.

## Result payload (fields Members 4-6 may read)

```
payload.result_id, job_id, request_hash, state, created_at
payload.data_revision, method_revision, software_revision
payload.request                       # the canonical request
payload.variables[]:
    variable_id, product_id, version, units, label
    period{start,end,months}
    aggregation_policy_id, qa_policy_mode
    counts{months,cells,valid_fraction,min_valid_cells_month}
    state
    trend{slope_per_year, slope_units, p_value, p_value_uncorrected,
          ci_low, ci_high, ci_meta, test, dependence_correction,
          significant_at}
    period_sensitivity{full_period, windows[], sign_agreement{}}
    warnings[], artifact{cube, spatial_trend}
payload.receipt_id
```

Rules for Members 4-6:

1. **Copy numbers, never recompute them.** `p_value` is not a probability that
   the trend is real — use the wording in
   `data/nasa/analysis/INTERPRETATION.md` §1.
2. `null` means unavailable or insufficient data. Never render it as zero.
3. The regional slope is not the mean of cell slopes. Say so if you show both.
4. `ci_low`/`ci_high` are an interval for the slope, not for the intercept.
5. Show `counts.valid_fraction` next to every series.

## Series and comparison

`GET /v1/analyses/{job_id}/series` returns `months[]`, `values[]` (nulls kept),
`valid_cells[]`, `trend` and `trend_line[]`. The trend line is computed on the
server; the browser only draws it. Typical call: 0.3 s.

`POST /v1/compare` with `{variable_id, start_month, end_month, with_ci?}`
returns one row per window: `state`, `slope_per_year`, `p_value`, `ci_*`,
`valid_fraction`, `cells`. Same variable, period, method and coverage rule;
native grids differ, so compare slopes, not absolute values. Typical call:
0.7 s without intervals.

## Spatial endpoint

`GET /v1/spatial/{variable_id}/{region_id}` returns the frozen per-cell product:

```
grid.lat[], grid.lon[]        native cell centres
slope[lat][lon]               units/year, null where not eligible
p_value[lat][lon]             seasonal MK p (Hamed-Rao), null if ineligible
significant_fdr[lat][lon]     1/0 after BH at q
n_valid_months[lat][lon]
fdr {q, family, m_tested}
limitations[]
```

Colour by `slope` (clip at a robust percentile), outline `significant_fdr`
cells, and print `fdr.q` and `fdr.m_tested`. Null is not zero.

## Explanation endpoint

`GET /v1/analyses/{job_id}/explanation?language=ar|en` returns:

```
path                "deterministic" | "llm" | "deterministic_fallback"
validation.ok       true when the answer passed every admission rule
validation.warnings rejection reasons when a model answer was replaced
explanation.answer, cited_chunk_ids, numeric_references, limitations, state
citations[]         chunk_id, title, page, source_url, authority
```

Show `explanation.answer` and `limitations[]` verbatim. Render `citations[]`
as the source panel. If `path` is `deterministic_fallback`, say the model
answer was rejected rather than hiding it.

## Receipt fields

`request`, `request_hash`, `data_revision`, `method_revision`,
`software_revision`, `sources[]` (cube sha256 + per-month granule ids),
`qa_policy{mode, policy_version, policy_sha256}`, `method_config_sha256`,
`spatial_mask`, `aggregation_policy`, `anomaly_baseline`, `trend_method`,
`dependence`, `bootstrap`, `multiplicity`, `minimum_series`, `created_at`.

Receipts never contain credentials; keys that look secret are stripped before
hashing.

## Performance (measured, see `bench_results.json`)

| Case | Time |
|---|---|
| 1 variable, full period | 4.5 s |
| 4 variables, full period | 15.9 s |
| 1 variable with AOI | 4.3 s |
| repeat of a completed request (cache) | 0.013 s |

Demo advice: run the preset analyses once before presenting (`python
warm_cache.py`), then the stage clicks are cache hits. Do not promise instant
results for a cold 4-variable request.
