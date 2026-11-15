# Role 03 — Backend contracts and service

Status: **DELIVERED** (14 November 2026, 20:15 Egypt time)
Software revision: **m3-1.0.0** · method revision consumed: **m2-1.0.0**

Mission from `docs/architecture/PLAN.md`: own FastAPI, runtime registry, job
queue, caching, SQLite metadata, receipts and deployment. Keep ingestion
separate from user requests. Publish API models and sample contracts.

## Deliverables

| Deliverable | Path | Status | Evidence |
|---|---|---|---|
| Catalog endpoint | `backend/app/main.py` `GET /v1/catalog` | DONE | 12 entries, readiness flags from `scope.v2.json` |
| Analysis submission + polling | `POST /v1/analyses`, `GET /v1/analyses/{id}` | DONE | idempotent, canonical hash, 201/200 semantics |
| Result endpoint | `GET /v1/analyses/{id}/result` | DONE | contract fields, per-variable states |
| Receipt endpoint | `GET /v1/receipts/{id}` | DONE | all 17 contract fields, sha256, no secrets |
| Health check | `GET /health` | DONE | revisions + queue depth |
| Explicit error codes | `backend/app/main.py` | DONE | 17 codes, `{"error":{"code","detail"}}` |
| Job queue + persistence | `backend/app/db.py`, `worker.py` | DONE | SQLite WAL, transactional claim, crash recovery |
| Caching | `db.find_cached_result` | DONE | keyed by request_hash + data_revision + method_revision |
| Published contract | `backend/openapi.json`, `backend/CONTRACTS.md` | DONE | generated from the app |
| Local start command | `backend/run.py`, `backend/README.md` | DONE | `python run.py` |
| Tests | `backend/tests/test_api.py` | DONE | **14/14 pass** |
| Benchmark | `backend/bench.py` + `bench_results.json` | DONE | see table below |

## Acceptance checks (the five required by PLAN.md)

| Check | How it is enforced | Test |
|---|---|---|
| Duplicate requests | unique `request_hash`; second POST returns the same job | `test_duplicate_request_returns_same_job` |
| Unavailable source rejection | `registry.servable()` requires measurement_ready **and** method_ready | `test_reject_unknown_region_and_variable` |
| Interrupted worker recovery | startup marks `running` jobs as `failed/INTERRUPTED` | `test_interrupted_worker_recovery` |
| Stale-cache invalidation | cache key includes both revisions | `test_stale_cache_not_reused_across_method_revision`, `test_reject_method_revision_mismatch` |
| Secret exclusion | no credentials read; receipt keys matching secret patterns stripped | `test_no_secrets_in_result_or_receipt` |

Additional contract tests: canonical geometry (rotated ring → same hash), AOI
out-of-bounds, self-intersecting polygon, invalid period, insufficient-data
state, failed job exposes no result or receipt.

## Measured performance (`bench_results.json`)

| Case | Time | Notes |
|---|---|---|
| 1 variable, full period | 4.52 s | 4.2 KB result |
| 4 variables, full period | 15.85 s | 13.7 KB result |
| 1 variable with AOI | 4.31 s | AOI subset is not slower |
| repeat of a completed request | 0.013 s | cache hit |

**UI promise:** one or two variables are fine live (~5 s each). For four
variables, pre-warm with `python warm_cache.py` before presenting; do not
promise instant cold results.

## Contract decisions published to Members 4-6

- `region_id` ∈ {nile_corridor, morocco_comparison, sahel_comparison};
  `variable_ids` ∈ {air_temperature, soil_moisture, precipitation,
  vegetation_greenness}; max 4 per request.
- Rings may start anywhere and be either orientation — normalized before
  hashing, so the browser must not build cache keys itself.
- `null` means unavailable/insufficient, never zero.
- `app_available` stays `false` until Member 6 signs the end-to-end path; the
  catalog reports it so the UI can hide or label the app state honestly.
- A failed job never exposes a result and never has a receipt; result and
  receipt rows are written in one transaction.

## Verified end-to-end over real HTTP

Server started with uvicorn, then:

```
GET  /health                    -> 200, method m2-1.0.0
GET  /v1/catalog                -> 12 entries
POST /v1/analyses               -> job_74fdae89949143d4 (queued)
GET  /v1/analyses/{id}          -> succeeded
GET  .../result                 -> NDVI Sahel +0.000682/yr p=0.00394,
                                   precipitation +0.000035 mm/hr/yr p=0.892
GET  /v1/receipts/rcpt_...      -> 17 fields, 288 granules per source
POST /v1/analyses (NO2)         -> 400 UNSUPPORTED_VARIABLE
```

The live API numbers match the precomputed evidence cards exactly, which is
the intended proof that the service cannot drift from the frozen pipeline.

## Open items

1. **No auth layer.** This is a local/competition deployment; any user can
   submit jobs. State it in the README rather than implying security.
2. **Single worker thread.** A 4-variable request blocks the queue for ~16 s.
   Acceptable for a demo; not a production queue.
3. **`app_available` remains false** by design until Member 6 verifies the
   end-to-end user path.
4. **Artifact files are referenced, not served.** `/v1/analyses/{id}/result`
   returns paths into the repository; serving map tiles/npz over HTTP is
   Member 5's integration step.
