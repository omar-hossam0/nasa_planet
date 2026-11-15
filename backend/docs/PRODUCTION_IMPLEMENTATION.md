# Backend implementation checkpoint

Current science integration: [REAL_SCIENCE_INTEGRATION.md](REAL_SCIENCE_INTEGRATION.md).
`MOCK_MODE=false` now uses actual NASA inputs and Role04 result conclusions.

The active entrypoint is `app.main:app`. Legacy `app/db.py`, `app/worker.py`
and `app/analysis_runner.py` belong to a different contract and must not be mixed
with the active API. No production science release is claimed by this checkpoint.

## Implemented

- SQLAlchemy repositories for jobs, results, receipts, spin results and completed-request cache.
- PostgreSQL driver support; SQLite is available for local integration tests.
- Atomic job plus queue insertion, and atomic result/receipt/cache/job completion.
- Separate durable worker with PostgreSQL `FOR UPDATE SKIP LOCKED` claims.
- Database queue avoids an additional Redis dependency during the first stage.
- Full UUID task identities in queue mode; cache keys preserve AOI precision.
- Real corpus retrieval at `POST /v1/explanations/ask` when `RAG_ENABLED=true`.
- Retrieval pipeline is reused per process, without sharing mutable RAG session trackers.
- Real source/statistics/spatial adapters and Role04 stored-result conclusions.
- Production startup remains blocked pending deployment and authorization review.

## Run the persistent integration environment

Install `backend/requirements.txt`. From `backend/`, set these environment variables
in both the API and worker shells:

```powershell
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@HOST:5432/trend_detective'
$env:JOB_BACKEND = 'database'
$env:RAG_ENABLED = 'true'
$env:APP_ENV = 'staging'
$env:MOCK_MODE = 'false'
python init_storage.py
```

`init_storage.py` is initial provisioning, not a schema migration framework.
Run provisioning once before the API and workers, not on every process startup.

API:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Worker, in a separate shell with the same settings:

```powershell
python -m app.workers.durable
```

Real analysis endpoints return descriptive science data. Explicit mock mode remains
available for fixture tests. The question endpoint
uses the real corpus and optionally Gemini via server-side `GEMINI_API_KEY`.
Questions currently have a separate input contract, without analysis-result context.

## Remaining before production

1. Preserve the descriptive-only boundary during deployment; passing integration
   tests does not approve scientific inference.
2. Retain request-local Role04 trackers and result provenance while adding new
   data/regions; positive/negative cell slopes are never significance categories.
3. Add identity/ownership checks for results, rate limits, admission limits,
   gateway TLS, secret management and deployment origin restrictions.
4. Introduce versioned schema migrations and normalized indexed tables before
   growth. This checkpoint stores schema-validated records in a generic JSON table.
5. Add worker heartbeats, bounded retries, job lease recovery and reconciliation.
   Interrupted claimed tasks currently remain running for operator review. Do not
   reset them while their original workers may still be running.
6. Concurrent identical in-flight requests may create separate tasks; completed
   results are cached. Add a transactional unique active-request reservation.
7. Use object storage for large native-grid artifacts, signed download URLs and
   immutable source revisions. Add metrics, traces, backups and restore drills.
8. Exercise PostgreSQL concurrency and load tests on actual deployment hardware.
   SQLite tests do not establish PostgreSQL throughput or production performance.

## Verification

`python -m pytest tests --ignore=tests/test_api.py -q` runs the active backend suite.
`tests/test_api.py` targets the legacy API contract and fails on the original HEAD
as well; it is retained, not deleted or silently skipped by configuration.
Root RAG tests also have existing registry/phase-state failures unrelated to this
checkpoint. Resolve contract ownership before merging all suites into one gate.
