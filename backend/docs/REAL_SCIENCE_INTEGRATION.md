# Real descriptive science integration

This implementation supersedes the earlier mock-only audit and the missing-field
blocker recorded in `SCIENCE_RAG_RECHECK.md`. It connects the existing scientific
methods; it does not release inferential statistics or complete production hosting.

## Data flow

```text
React selection: region + variable + dates + optional bbox
  -> FastAPI request/coverage/native-cell validation
  -> inline local executor OR durable SQL worker
  -> registered local NASA NetCDF input + source fingerprint
  -> existing science strict QA and fixed full-reference support
  -> requested monthly regional series + annual aggregates
  -> existing annual Theil-Sen kernel at actual elapsed years
  -> stored result, native annual slope arrays and evidence receipt
  -> React chart/map/evidence and per-cell details
  -> Role04 conclusion renderer, using only the stored numeric result
```

Independent documentation questions still use corpus BM25 retrieval and optional
Gemini generation. Gemini does not calculate slopes, generate source measurements
or decide whether a region's trend is statistically significant.

## Scientific choices preserved

- No estimator, QA threshold or imputation policy was changed.
- The supported API aggregation is `area_weighted`, using the existing spherical
  native-cell solid angles and centre-selected rectangles. `cell_mean` is rejected
  in real mode rather than silently treated as area weighted.
- Strict reference support is computed over the full registered 2001–2024 source
  record, then the requested dates and area are selected. Custom periods do not
  redefine reference support to make data look more complete.
- Annual temperature, soil moisture and NDVI use the existing complete-year,
  calendar-day-weighted aggregation. Annual precipitation sums twelve integrated
  monthly amounts. Source precipitation rates are not mislabeled as accumulations.
- A descriptive annual slope is an estimated change, not a significance verdict.
  `p_value` and confidence intervals remain null; method approval is not asserted.
- Missing cell slopes remain null. Positive, negative, zero and unavailable counts
  use preparation-eligible support; excluded cells are not significance categories.
- `100%` valid monthly values does not imply 100% retained spatial area. The UI
  separately displays QA-retained cell counts and retained native-cell area.

The input contract's `cube_variable` and `cube_units` fields were populated from
the source audit's explicit identities/units. No source measurements were changed.
The runtime science contract is `docs/architecture/scope.v2.json`; the historical
root `scope.v2.json` copy is not consumed by this integration.

## Source integrity and scaling

Source SHA256, preparation policy hash, region revision and input-contract hash
participate in dataset/cache revisions. Source or policy changes after startup
fail closed; restart API and workers after an intentional update. Receipts identify
the same source files and hashes as their stored result.

`GET /v1/results/{id}/spatial?compact=true` returns native axes and slope arrays
without thousands of repeated polygon geometries. The ordinary endpoint still
provides polygons and identifiers for cell detail/comparison consumers. Displayed
cells use native spacing, not an invented 3×3 grid.

Science I/O is bounded by a process-local lock because NetCDF/HDF5 operations may
not be thread-safe. Separate worker processes are the deployment scaling unit.
The API does not promise an unmeasured throughput or latency target.

## Configuration and execution

The ignored local `backend/.env` now contains `MOCK_MODE=false`, alongside the
previously configured provider settings. Tests may explicitly select mock mode.

For a durable worker deployment, use the same environment in API and workers:

```powershell
$env:MOCK_MODE = 'false'
$env:DATABASE_URL = 'postgresql+psycopg://USER:PASSWORD@HOST:5432/trend_detective'
$env:JOB_BACKEND = 'database'
$env:APP_ENV = 'staging'
python init_storage.py
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
# Separate terminal, same environment:
python -m app.workers.durable
```

Local development can execute inline without a configured database. This is
convenient for development, not a claim that durable production jobs are provisioned.
Production startup remains gated on deployment/authentication review.

Adding a region to `backend/config/regions.json` makes it discoverable, but real
mode enables only variable/region pairs with an actual registered input. Register
and validate the input in the scientific contract too; never invent coverage from
the drawn rectangle. Aliases and labels do not grant data access.

## Verification

- Science suite: 118 passing tests, 57 passing subtests after contract repair.
- Active backend suite: 162 passing tests (including 16 real-input integration
  cases). Role04 conclusion/validation regression selection: 67 passing tests.
- Real integration tests cover all twelve source cases, compare annual slopes
  with archived Phase 3 values and independent median-of-pairwise-slopes references,
  check actual native cells, receipt hashes, Role04 result explanations, custom
  area/date selection, empty selections, aggregation rejection and SQL workers.
- Real browser audit clicks all twelve variable/region combinations, compares
  displayed slopes and every plotted monthly coordinate with actual API data,
  downloads a matching receipt, computes 15 sensitivity windows, compares three
  regions, and tests documentation Q&A, mobile layout and Arabic RTL.
- The Nile temperature check returns `0.025330383313493597 K/year` on 102 native
  cells for 2001–2024 under the current default strict preparation.

Commands:

```powershell
# backend/
python -m pytest tests --ignore=tests/test_api.py -q
# repository root
python -m pytest packages/science/tests -q
python tools/audit_application_browser.py --real-science
```

The browser audit deliberately disables provider generation to make its scientific
and source-grounding checks reproducible without paid calls. Gemini connectivity
was checked separately in the earlier provider setup. Browser artifacts live in
ignored `backend/var/real-browser-audit/`.

Remaining deployment work includes identity/ownership, migrations, worker lease
recovery, in-flight deduplication, load validation on PostgreSQL and hosting. The
legacy API test file still targets an incompatible historical API; it is not
silently deleted or reported as passing.
