# Trend Detective — Backend (mock-first milestone)

FastAPI backend for **Trend Detective — What the Average Hides**.

This milestone delivers the **complete API surface (18 endpoints)** on deterministic,
clearly-labelled **synthetic data**. There is no database, no AI/RAG provider, no
frontend and no live NASA connection — by design. Every integration sits behind an
interface so it can be replaced without changing the HTTP contract.

---

## 1. Status at a glance

| Area | State |
|---|---|
| API surface | 18 / 18 endpoints implemented |
| Data | Deterministic mock fixtures, `data_mode: "mock"` on every payload |
| Persistence | In-process dictionaries only (lost on restart) |
| Statistics | `MockStatisticsAdapter` — descriptive slopes, **no p-values** |
| AI / RAG | `MockRAGAdapter` — keyword rules + templates, **no citations** |
| NASA data | `MockNASADataAdapter` — repository registry snapshot, no NetCDF reads |
| Tests | 121 passing (`pytest`) |
| Database | Not provisioned (intentional) |

---

## 2. Architecture

Modular monolith, layered:

```text
HTTP request
   -> FastAPI router            app/api/v1/*
   -> Pydantic validation       app/schemas/*
   -> Application service       app/services/*
   -> Adapter / Repository      app/adapters/*, app/repositories/*
   -> Pydantic response         -> HTTP response
```

| Layer | Responsibility |
|---|---|
| `app/api/v1/` | Routes, status codes, OpenAPI docs. No science, no business logic. |
| `app/schemas/` | Request/response models, enums, validation, error envelope. |
| `app/services/` | Workflows: validation, availability, caching, job orchestration, assembly. |
| `app/adapters/` | Interfaces to NASA data, statistics and RAG. Mock implementations today. |
| `app/repositories/` | Job/result/receipt/spin/cache persistence. In-memory today. |
| `app/workers/` | Deterministic mock job manager (no Celery, no Redis, no threads). |
| `app/mocks/` | Deterministic fixtures and generators (catalog, series, grid, AI rules). |
| `app/core/` | Settings, DI container, exceptions, logging, month utilities. |

Dependency injection: `app/core/dependencies.py` builds a `Container` per application
instance and stores it on `app.state.container`. Tests get full isolation by creating a
new app.

---

## 3. Install and run (Windows-friendly)

From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

python -m pip install -r backend/requirements.txt
```

Start the server:

```bash
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Then open:

- Swagger UI — <http://127.0.0.1:8000/docs>
- ReDoc — <http://127.0.0.1:8000/redoc>
- OpenAPI JSON — <http://127.0.0.1:8000/openapi.json>

Health check:

```bash
curl http://127.0.0.1:8000/health
```

### Configuration

Copy `.env.example` to `.env` if you want to override defaults. Nothing in it is
required and no credential is needed.

| Variable | Default | Meaning |
|---|---|---|
| `APP_ENV` | `development` | Reported by `/health` and `/ready` |
| `MOCK_MODE` | `true` | Only supported mode in this milestone |
| `API_PREFIX` | `/v1` | Prefix for versioned routers |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated frontend origins |
| `MOCK_AUTO_COMPLETE_JOBS` | `true` | `false` leaves jobs `queued` until advanced |
| `MAX_VARIABLES_PER_ANALYSIS` | `4` | Guardrail |
| `MIN_PERIOD_MONTHS` / `MAX_PERIOD_MONTHS` | `12` / `600` | Period guardrails |
| `MIN_AOI_SPAN_DEGREES` / `MAX_AOI_SPAN_DEGREES` | `0.25` / `40` | AOI guardrails |
| `MAX_SPIN_WINDOWS` | `60` | Spin It guardrail |

---

## 4. Tests

```bash
cd backend
..\.venv\Scripts\python.exe -m pytest
```

- 121 tests, no network, no database, no external service.
- Every endpoint has at least one happy-path test plus its error cases.
- Repository isolation and cross-instance determinism are covered explicitly.

Useful variants:

```bash
python -m pytest -q                     # quiet
python -m pytest tests/test_analyses.py # one module
python -m pytest -k spin                # by keyword
```

---

## 5. Endpoints

| # | Method | Path | Purpose |
|---|---|---|---|
| 1 | GET | `/health` | Liveness |
| 2 | GET | `/ready` | Readiness with honest integration state |
| 3 | GET | `/v1/catalog` | Variables + provenance + readiness flags |
| 4 | GET | `/v1/catalog/variables/{variable_id}` | Variable detail |
| 5 | GET | `/v1/catalog/regions` | Study regions |
| 6 | GET | `/v1/catalog/availability` | Is this variable/region/period/AOI usable? |
| 7 | POST | `/v1/recommendations` | Keyword-based variable suggestions |
| 8 | POST | `/v1/analyses` | Create analysis (202 new, 200 cached) |
| 9 | GET | `/v1/analyses/{job_id}` | Job status |
| 10 | GET | `/v1/results/{result_id}` | Completed result |
| 11 | GET | `/v1/results/{result_id}/spatial` | Map-ready 3x3 grid |
| 12 | GET | `/v1/results/{result_id}/cells/{cell_id}` | Cell detail |
| 13 | POST | `/v1/comparisons` | Cell-to-cell comparison |
| 14 | POST | `/v1/results/{result_id}/spin` | Spin It window sweep |
| 15 | GET | `/v1/spin/{spin_id}` | Spin It results |
| 16 | POST | `/v1/explanations` | Template explanation (EN/AR) |
| 17 | GET | `/v1/receipts/{receipt_id}` | Evidence receipt |
| 18 | GET | `/v1/receipts/{receipt_id}/download` | Receipt as JSON attachment |

Full request/response contracts: [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md).

---

## 6. Quick workflow

```bash
# 1. Create an analysis
curl -X POST http://127.0.0.1:8000/v1/analyses \
  -H "Content-Type: application/json" \
  -d '{"variable_ids":["air_temperature"],"region_id":"nile_corridor",
       "start_month":"2001-01","end_month":"2024-12"}'

# 2. Poll the job (replace JOB_ID)
curl http://127.0.0.1:8000/v1/analyses/JOB_ID

# 3. Read the result, spatial grid, comparison, spin, explanation, receipt
curl http://127.0.0.1:8000/v1/results/RESULT_ID
curl http://127.0.0.1:8000/v1/results/RESULT_ID/spatial
curl -X POST http://127.0.0.1:8000/v1/comparisons \
  -H "Content-Type: application/json" \
  -d '{"comparison_type":"cells","result_id":"RESULT_ID","cell_ids":["cell_01","cell_04"]}'
curl -X POST http://127.0.0.1:8000/v1/results/RESULT_ID/spin \
  -H "Content-Type: application/json" \
  -d '{"minimum_window_years":10,"start_year_min":2001,"end_year_max":2024}'
curl -X POST http://127.0.0.1:8000/v1/explanations \
  -H "Content-Type: application/json" -d '{"result_id":"RESULT_ID","language":"en"}'
```

---

## 7. Mock mode: what it means

- Every response carries `data_mode: "mock"` and a disclaimer.
- Trend payloads carry `p_value: null` and `inference_status: "not_computed"`. No
  significance test is run, so no significance may be claimed.
- Recommendations carry `provider: "mock_rules"` and `references: []` — nothing was
  retrieved, so nothing is cited.
- Explanations carry `mode: "mock_template"` and `references: []`.
- Catalog `measurement_ready` / `method_ready` / `app_available` are copied from the
  verified registry snapshot. Because `method_ready` and `app_available` are `false`
  everywhere, analyses are allowed only through an explicit **demo gate**
  (`demo_available`), and `/catalog/availability` reports
  `availability_source: "registry_snapshot + mock_demo_gate"` and `simulated: true`.

Details and formulas: [`docs/MOCK_DATA.md`](docs/MOCK_DATA.md).

---

## 8. Known limitations

1. **No durability.** All state lives in process memory; restarting the server erases
   every job, result and receipt. Multiple uvicorn workers do not share state.
2. **No real science.** Slopes are computed from synthetic series. They are descriptive
   of the demo series only.
3. **No database.** Repository protocols exist; only in-memory implementations do.
4. **No AI/RAG.** Keyword rules and templates. No embeddings, no retrieval, no citations.
5. **No NASA I/O.** The catalog is a snapshot of `docs/architecture/scope.v2.json` and
   `data/nasa/runtime_catalog.json`. No NetCDF file is opened at request time.
6. **Single variable for spatial.** For multi-variable results the spatial grid and
   Spin It operate on the first requested variable.
7. **Regional comparison not implemented.** `comparison_type` only accepts `cells`.
8. **No authentication.** Out of scope for this milestone.

---

## 9. Future integration points

| When we receive | Replace | Keep |
|---|---|---|
| Real NASA datasets / runtime registry | `MockNASADataAdapter` (`app/adapters/mock_nasa_data.py`) + refresh `app/mocks/catalog.py` | `NASADataAdapter` protocol, all services |
| Statistics engine + reviewed method | `MockStatisticsAdapter` (`app/adapters/mock_statistics.py`) | `StatisticsAdapter` protocol, `ComputedAnalysis`/`ComputedSpin` |
| RAG + model outputs | `MockRAGAdapter` (`app/adapters/mock_rag.py`) | `RAGAdapter` protocol, recommendation/explanation schemas |
| Database + durable jobs | `InMemory*Repository` (`app/repositories/memory.py`), `MockJobManager` | Repository protocols, `Container` wiring |
| Frontend | Nothing server-side except `CORS_ORIGINS` | All contracts |

No router or schema change should be required for any of these.

---

## 10. Git

Development happens on the **`backend`** branch. `main` is untouched. Nothing is pushed
automatically.
