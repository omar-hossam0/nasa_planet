# Trend Detective backend

FastAPI backend for the React workspace in `frontend/`.

## Current execution modes

- `MOCK_MODE=false`: actual local NASA NetCDF inputs, strict fixed-reference QA,
  area-weighted regional series, annual descriptive Theil-Sen slopes and native
  cell grids from `packages/science`.
- `MOCK_MODE=true`: explicit synthetic fixtures for demos and isolated tests.
- Numerical result explanations in real mode consume stored results through
  Role04, with no LLM calculation. Documentation questions use a separate RAG
  pipeline with optional server-side Gemini generation.
- Inference is not released: p-values and confidence intervals remain null.
  Descriptive availability is not a claim of inferential scientific approval.

The local `backend/.env` selects real mode. Environment variables override files.
Never commit credentials. `backend/.env.example` documents provider settings.

## Run locally

From repository root:

```powershell
python -m pip install -r backend/requirements.txt
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

The Vite development server forwards `/v1` to port 8000. API documentation is at
`http://127.0.0.1:8000/docs`. Restart API and workers after changing source files,
region configuration, preparation policy or provider settings.

Local inline execution is convenient for development. For deployment use the
SQL repositories and separate worker described in
[PRODUCTION_IMPLEMENTATION.md](docs/PRODUCTION_IMPLEMENTATION.md). The deployment
profile is not yet released; authentication, migrations and worker recovery remain
separate work. Do not confuse a working real-science path with completed hosting.

## Main workflow

1. `GET /v1/catalog` and `/v1/catalog/regions` provide variables and region allowlist.
2. `POST /v1/analyses` accepts region, variable(s), bbox and dates. Unsupported
   sources, empty native-grid selections and unsupported aggregation are rejected.
3. Poll `GET /v1/analyses/{job_id}`, then fetch `/v1/results/{result_id}`.
4. `/v1/results/{result_id}/spatial?compact=true` returns compact native arrays.
   Omit `compact` to request individual cell polygons; `/cells/{cell_id}` returns
   the actual QA-masked monthly series and annual cell estimate.
5. `POST /v1/explanations` renders the stored result through Role04. Its references
   document products; input hashes in the evidence receipt identify measurements.
6. `POST /v1/explanations/ask` handles independent documentation questions.
7. `POST /v1/results/{result_id}/spin` recomputes annual sensitivity windows on the
   same fixed QA support; `POST /v1/comparisons` compares cells in one result.
8. `/v1/receipts/{receipt_id}` returns provenance and the matching request/result.

## Verification

```powershell
# From backend/
python -m pytest tests -q
# From repository root
python -m pytest packages/science/tests -q
python tools/audit_application_browser.py --real-science
python tools/acceptance_check.py
```

The current backend tests are under `backend/tests/`; there is no legacy
`tests/test_api.py` file in this checkout. Browser checks require Python
Playwright and an installed Chromium browser. The backend serves the built
React product at `/product/` and redirects `/` there when `dist/product/`
exists.

See [REAL_SCIENCE_INTEGRATION.md](docs/REAL_SCIENCE_INTEGRATION.md) for integration
choices, validation results and scientific/deployment limits.
