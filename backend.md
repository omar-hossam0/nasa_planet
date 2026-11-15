# Trend Detective — Backend Engineering Instructions

> **Status: GREENFIELD / API-FIRST / MOCK-FIRST**
>
> This is an implementation guide for the backend workstream, **not a claim that any feature is already implemented**.
> At the time of writing:
> - No database has been selected or provisioned.
> - The AI/RAG team has not delivered an integration-ready output or contract.
> - Real NASA datasets, statistical integration outputs, and the frontend are **not yet available to the backend as verified working integrations**.
> - Assume no existing working backend features until the repository is inspected.
> - Development must use **explicitly labeled mock data** until the actual contracts and datasets arrive.
> - The developer works on Git branch **`backend`**. **Do not commit, merge, or push changes to `main`**. Push backend work only to `backend`, after checking the current branch and remote.
>
> **Architecture proposal:** Python + FastAPI, modular monolith, layered design, REST/JSON, Pydantic, dependency-injected adapters/repositories, mock-first integrations.

## 1. Product objective and scope

Trend Detective is a scientific environmental-trend exploration platform using NASA Earth-observation datasets. It helps users see what regional averages can hide, explore local spatial differences, change time windows ("Spin It"), receive evidence-grounded explanations, and inspect reproducibility metadata ("Evidence Receipt").

Backend responsibility: provide stable APIs, validate requests and dataset availability, orchestrate statistical work, integrate future AI/RAG, manage jobs and result identifiers, serve spatial/chart-ready data, and produce evidence metadata. The backend **does not invent scientific results**, **does not let the LLM calculate statistics**, and **does not assume any upstream component is finished**.

Proposed frontend: React + TypeScript, map and chart visualization. These are integration assumptions, **not implemented dependencies**.

## 2. Non-negotiable working rules

1. **Inspect before editing.** Check the actual repository tree, README, configuration, existing API contracts, and Git status. Do not overwrite existing team work or claim absent components exist.
2. **Branch safety.** Verify `git branch --show-current` equals `backend` before making commits. If not, stop and ask or switch safely only if the branch exists and the working tree permits. Never run destructive Git commands. Never push to `main`; use `git push -u origin backend` only when remote access and authorization are confirmed. Never merge into `main` without explicit instruction.
3. **Mock-first, contract-first.** Define request/response models and tests before integrating real services. All mock responses must include a clear `data_mode: "mock"` or equivalent and must never be presented as observed NASA results.
4. **No database required now.** Use in-memory repositories and fixtures behind interfaces. In-memory state is ephemeral, process-local, non-shared between workers, and resets on restart. Run a single application process for the mock demo; do not advertise durability.
5. **No AI required now.** Use a deterministic `MockRAGAdapter` for recommendation and explanation contracts. Never imply the mock response came from an LLM, retrieved NASA documentation, or verified citations.
6. **No real statistics required now.** A `MockStatisticsAdapter` returns deterministic fixtures only. Keep real integration behind an adapter and require a reviewed statistical output contract.
7. **Do not silently expand scientific coverage.** Distinguish `catalogued`, `data_available`, and `analysis_ready`. The earlier project brief identified MERRA-2 air temperature and GLDAS soil moisture for a limited Egypt area as available, while precipitation, NDVI, and broader coverage were planned; **re-verify actual files/registry before asserting any availability**.
8. **Version the API under `/v1`.** Keep stable public contracts and avoid exposing internal file paths or stack traces.
9. **Use English for code, API fields, identifiers, and developer docs** to avoid right-to-left parsing issues. User-facing explanations may be localized.
10. **No fake success.** Return explicit unavailable/not-implemented states when an integration is missing; distinguish a contract demo from a scientific result.

## 3. Architecture and dependency boundaries

```text
Frontend (not yet integrated)
          |
       REST/JSON
          |
FastAPI Routers + Pydantic Schemas
          |
Application Services (catalog, analysis, results, spatial, spin,
                      recommendations, explanations, receipts)
          |
Adapters / Repositories / Job Manager
  |             |                |                |
Catalog     Statistics        AI / RAG          Storage
Registry    Adapter           Adapter           Interfaces
  |             |                |                |
Mock/real   Mock/real         Mock/real         In-memory/SQL
```

Keep the NASA data preparation pipeline **outside request-time API work**. Prepared scientific files will be consumed by the approved statistics adapter when available. Do not download large NASA datasets per user request.

### Layer responsibilities

- **Routers:** HTTP parsing, dependency injection, response status codes; no scientific calculations.
- **Schemas:** Pydantic request/response types, field validation, typed enums, API examples.
- **Services:** business workflows, eligibility checks, cache/job orchestration, output assembly.
- **Adapters:** boundaries to dataset registry, statistics functions, RAG, files.
- **Repositories:** analysis/job/result/receipt persistence abstractions; in-memory now, SQL later.
- **Workers:** bounded compute execution; mock job lifecycle now, persistent external execution later.
- **Core:** settings, logging, error mapping, dependency providers, CORS.

Use FastAPI dependency injection to select implementations from configuration (`MOCK_MODE=true` initially). Never put mock-specific logic directly in routers.

## 4. Proposed endpoint inventory

These are **proposed contracts**; reconcile them with repository documents and frontend/statistics/AI team agreements before freezing. Existing project core paths are `/v1/catalog`, `/v1/analyses`, `/v1/analyses/{job_id}`, `/v1/explanations`, `/v1/receipts/{id}`.

| Priority | Method | Path | Purpose |
|---|---|---|---|
| P0 | GET | `/health` | Liveness |
| P1 | GET | `/ready` | Readiness with explicit mock/dependency state |
| P0 | GET | `/v1/catalog` | Variables, provenance, coverage, availability state |
| P1 | GET | `/v1/catalog/variables/{variable_id}` | Variable details |
| P0 | GET | `/v1/catalog/regions` | Supported/known regions |
| P0 | GET | `/v1/catalog/availability` | Validate variable/region/period (and AOI if supported) |
| P1 | POST | `/v1/recommendations` | Question-to-dataset recommendations (mock RAG initially) |
| P0 | POST | `/v1/analyses` | Create analysis job or reuse compatible cached result |
| P0 | GET | `/v1/analyses/{job_id}` | Job status and result reference |
| P0 | GET | `/v1/results/{result_id}` | Completed summary, series, methods, warnings |
| P0 | GET | `/v1/results/{result_id}/spatial` | Map-ready spatial result |
| P1 | GET | `/v1/results/{result_id}/cells/{cell_id}` | Cell detail and time series |
| P1 | POST | `/v1/comparisons` | Compare compatible cells or regions |
| P1 | POST | `/v1/results/{result_id}/spin` | Start time-window sensitivity analysis |
| P1 | GET | `/v1/spin/{spin_id}` | Sensitivity job/result status |
| P0 | POST | `/v1/explanations` | Evidence-grounded result explanation (mock initially) |
| P0 | GET | `/v1/receipts/{id}` | Reproducibility metadata |
| P1 | GET | `/v1/receipts/{id}/download` | Export artifact only when implemented |

**Do not automatically implement all 18 endpoints at once.** Deliver P0 contract coverage first; P1 can return explicit `501` with documented behavior until implemented, or be omitted from the first release while retaining the specification.

### Key endpoint contract decisions

- `POST /v1/analyses`: use `202 Accepted` and a `job_id` for new asynchronous jobs; cached results may be returned with documented semantics. `GET /v1/analyses/{job_id}` returns `queued | running | completed | failed` and optional `result_id`.
- `GET /v1/results/{result_id}` must not return a success response for incomplete jobs.
- `POST /v1/explanations` takes a **completed `result_id`**, not arbitrary user-provided numerical claims.
- `GET /v1/receipts/{id}` returns metadata only for a known result/receipt. A mock receipt must be marked as such.
- `GET /v1/catalog/availability` should clearly distinguish missing coverage, not-ready data, and unsupported method; do not equate missing with zero.
- For `bbox`, specify coordinate order as `[west, south, east, north]` in WGS84; validate ranges and ordering. For polygon AOI, defer until the team approves GeoJSON and geometry constraints.
- Time period fields: `YYYY-MM` (monthly) for current proposal. Validate `start_month <= end_month`, coverage, and maximum span.
- Spin It may be compute-intensive: keep it as a job separate from the base analysis; a changed time window does not silently mutate the original result.
- For comparisons, validate shared variable, units, period, method and dataset revisions before claiming comparability.
- Spatial responses need cell geometry/coordinates, units, evidence states, missing-value indicators, and data revision. Avoid huge unbounded payloads; add pagination/tiling/limits when needed.

## 5. Canonical example schemas (illustrative, not verified project contracts)

### Analysis request

```json
{
  "variable_ids": ["air_temperature"],
  "region_id": "egypt",
  "aoi": {
    "type": "bbox",
    "coordinates": [29.0, 25.0, 33.0, 31.0]
  },
  "start_month": "2005-01",
  "end_month": "2020-12",
  "aggregation_policy": "area_weighted"
}
```

`aggregation_policy` must be supported by the statistics team; until then, allow only agreed enum values. Do not imply the sample geographic area is covered by actual data.

### Accepted job

```json
{
  "job_id": "job_mock_001",
  "status": "queued",
  "result_id": null,
  "data_mode": "mock"
}
```

### Completed job

```json
{
  "job_id": "job_mock_001",
  "status": "completed",
  "result_id": "result_mock_001",
  "data_mode": "mock"
}
```

### Error envelope

```json
{
  "error": {
    "code": "DATA_NOT_AVAILABLE",
    "message": "The requested dataset is not ready for analysis.",
    "details": {
      "variable_id": "precipitation"
    },
    "request_id": "req_example"
  }
}
```

Define explicit response models for result summaries, time-series points, spatial cells, evidence/uncertainty state, warnings, source references, and receipt metadata. **Do not invent units, p-values, significance, coverage, citations, or dataset revision identifiers in real-mode responses.**

## 6. Mock fixtures and behavior

Keep fixtures under `app/mocks/` and use deterministic, reproducible IDs/values for tests. A small, deliberately synthetic grid and time series can demonstrate visualization and flow; label them **synthetic demo data** in every relevant API response and documentation. Avoid realistic-looking fake citations to NASA products.

- Catalog fixtures: known variable IDs, display names, units if verified, and explicit `demo_only`/availability fields.
- Analysis fixtures: sample request maps to deterministic job and result; mock job state progression can be immediate or controlled by a test fixture. Do not use unreliable sleeps or unbounded background tasks.
- Spatial fixtures: a handful of synthetic cells with stable IDs and geometries.
- Spin fixtures: a few synthetic windows, explicitly not scientific findings.
- AI fixtures: canned recommendation/explanation messages with `provider: "mock"` and no fabricated references.
- Receipt fixtures: only mock provenance, with `data_mode: "mock"` and clear disclaimers.
- Missing resources: return `404`; unavailable capability: return a consistent explicit error; malformed requests: `422`; incompatible state: `409`; service unavailable: `503` where appropriate.

**Single-process limitation:** in-memory repository state disappears on restart and is not shared across processes. Tests should isolate/reset fixtures.

## 7. Job lifecycle and cache rules

States: `queued`, `running`, `completed`, `failed`. Optionally `cancelled` only if cancellation is implemented.

For mock mode, implement a predictable in-process job manager and state transitions, or immediately completed deterministic fixtures with the contract preserved. Never claim the in-memory job system is durable.

For real mode, plan a bounded worker and durable job storage; do not run heavy numerical calculations in HTTP handlers or rely solely on FastAPI `BackgroundTasks`. No need to introduce Celery/Redis now unless actual requirements justify it.

Cache keys must include normalized AOI, variable(s), period, aggregation/method settings, **dataset revision**, **method version**, and any relevant computation configuration. Never reuse cached outputs across incompatible versions.

## 8. Scientific integrity and provenance

- Keep statistics in a reviewed statistics adapter; AI does not produce scientific numbers.
- Distinguish `increasing`, `decreasing`, `inconclusive`, `insufficient_data`, and `not_computed` as approved by the statistics team. A non-significant result is **not** proof of no change.
- Preserve units, confidence intervals/p-values when supplied, valid sample counts, coverage/quality flags, and method versions.
- Never infer causation from trend or correlation.
- Receipt should eventually capture request parameters, AOI, period, source product, dataset revision, preprocessing revision, method/version, result identifier, generated artifacts, warnings, and timestamps.
- Missing metadata should be represented as missing/unavailable, not fabricated.

## 9. Planned project structure

```text
backend/
├── app/
│   ├── main.py
│   ├── api/v1/
│   │   ├── system.py
│   │   ├── catalog.py
│   │   ├── recommendations.py
│   │   ├── analyses.py
│   │   ├── results.py
│   │   ├── spatial.py
│   │   ├── comparisons.py
│   │   ├── spin.py
│   │   ├── explanations.py
│   │   └── receipts.py
│   ├── schemas/
│   ├── services/
│   ├── adapters/
│   ├── repositories/
│   │   ├── interfaces.py
│   │   └── memory.py
│   ├── workers/
│   ├── mocks/
│   └── core/
│       ├── config.py
│       ├── dependencies.py
│       ├── errors.py
│       └── logging.py
├── tests/
├── .env.example
├── .gitignore
├── requirements.txt
├── Dockerfile
└── README.md
```

Use small modules, typing, consistent naming, no circular imports, and dependency injection. Prefer async only for I/O-bound operations; CPU-bound computation belongs in worker processes.

## 10. Database migration plan (NOT now)

Do **not** add a database dependency as a prerequisite for the first API implementation.

Define repository protocols/interfaces for:
- `CatalogRepository` / runtime registry reader
- `AnalysisRepository`
- `JobRepository`
- `ResultRepository`
- `ReceiptRepository`

Initial implementations are in-memory or file-backed demo fixtures. Future implementations can use SQLAlchemy with SQLite (single-instance MVP) or PostgreSQL (more concurrent/durable deployment), plus Alembic migrations. NASA scientific arrays should remain in appropriate file/object storage rather than being forced into relational tables. Keep database selection open until deployment and workload requirements are known.

## 11. Future integration contracts to request from teammates

### Data team
- Verified runtime catalog, canonical variable IDs and aliases
- Data availability by AOI/time, source products, revisions
- File formats/paths, grid CRS/resolution, units, missing-value conventions
- Data loading interface and preprocessing/quality metadata

### Statistics team
- Callable function/API interface and exact typed input/output schemas
- Supported methods, aggregation policies, temporal windows
- Spatial cell IDs/geometry, time-series shapes, units
- Evidence/uncertainty fields, missing-data rules, warnings, method versions
- Performance and memory expectations

### AI/RAG team
- Recommendation request/response schema
- Supported language handling, citations with resolvable IDs
- Explanation input contract tied to completed result IDs
- Action identifiers for UI, safety/validation, provider failure fallback
- Explicit distinction between retrieved facts and generated text

### Frontend team
- Confirm endpoints, AOI shape, chart series format, spatial geometry format
- Polling behavior and job/result identifiers
- Error display conventions, interactive explanation action names
- API base URL, CORS origins, mock-mode labeling

**Do not pretend any of these contracts have been delivered.** Track unresolved decisions in `docs/OPEN_QUESTIONS.md`.

## 12. Configuration, safety, and deployment

- `.env.example`: `APP_ENV=development`, `MOCK_MODE=true`, `API_PREFIX=/v1`, `CORS_ORIGINS=http://localhost:5173`, `LOG_LEVEL=INFO`, and optional future settings (e.g., `DATABASE_URL`) commented out.
- Do not commit `.env`, API keys, secrets, local datasets, or large generated artifacts.
- Validate request size, AOI bounds, date ranges, query lengths, and maximum concurrency.
- Configure CORS explicitly for local frontend origins; do not use wildcard origins with credentials.
- Use structured logs and request IDs; avoid leaking sensitive request contents, secrets, filesystem paths, or stack traces in responses.
- Add `/health` and `/ready`; readiness should honestly report unavailable dependencies without breaking mock-only development.
- Prepare Docker support and a local run path. Deployment provider and durable storage remain undecided.
- Never claim a public deployment, working NASA integration, or AI integration until tested.

## 13. Tests and acceptance criteria

Use `pytest` + FastAPI `TestClient`/`httpx` as appropriate. Test at minimum:
- Health and OpenAPI schema generation
- Catalog variable listing and unavailable data states
- Valid/invalid AOI, date ranges, variable IDs
- Create job -> poll job -> fetch completed mock result
- Missing/failed job, incomplete result, unknown cell
- Spatial fixture and unit/evidence metadata
- Spin window validation and comparison compatibility
- Mock recommendations/explanations clearly marked as mock
- Receipts linked to results, not invented
- Consistent error envelope and status codes
- Dependency injection replacing mock adapters in tests
- In-memory repository isolation between test cases

Use deterministic fixtures, no external NASA/AI/network calls in unit tests. Provide example curl requests and sample responses in README. Make sure `/docs` is usable.

## 14. Implementation order

**Phase 0 — Repository reconnaissance:** inspect existing files and branch, identify conventions and conflicts; write a brief plan. No destructive changes.

**Phase 1 — Foundation (P0):** FastAPI app, config, CORS, error handler, health, schemas, in-memory repositories, mock adapters, `/v1/catalog`, regions/availability, analysis creation and status, results retrieval, tests and Swagger.

**Phase 2 — Full mock user journey:** spatial reveal, cell detail, comparisons, Spin It, recommendations, explanations, receipts, optional export. Ensure each is demo-labeled and contract-tested.

**Phase 3 — Real integrations:** plug in verified NASA runtime registry, statistics engine, AI/RAG output, durable jobs, and selected database/storage. Add integration tests and verify scientific provenance.

**Phase 4 — Delivery:** Docker, CI/test commands, documentation, deployment smoke tests, and a fallback demo. Do not mark as complete until actually verified.

## 15. Git and collaboration workflow

1. `git status`
2. `git branch --show-current` (must be `backend` before commit/push)
3. Inspect `git remote -v` and repository guidance
4. Make scoped backend changes only; avoid modifying unrelated frontend/AI/data files
5. Run tests and review `git diff`
6. Commit descriptive, focused changes **on `backend`**
7. Push only to `origin backend` when explicitly intended and remote access is configured
8. **Never push to `main`, never force-push, never merge to `main`** without explicit approval

If working tree has uncommitted team changes, preserve them and ask before altering conflicting files.

## 16. Definition of done for the first milestone

- FastAPI boots locally and `/docs` renders.
- P0 endpoints return validated, documented, deterministic mock responses.
- All mock responses are clearly labeled; no real-science claims.
- Endpoints follow the layered architecture and can swap mock adapters/repositories for real ones.
- Tests pass without a database, frontend, AI provider, or NASA network access.
- README explains setup, mock limitations, API examples, pending integrations, and branch workflow.
- Changes are prepared/committed only on branch `backend`; **`main` remains untouched**.

## 17. Explicit non-goals for the first milestone

- No real NASA data ingestion or scientific validation claims.
- No real AI/LLM provider or fabricated citations.
- No database provisioning, SQL migrations, or production persistence.
- No user authentication unless an agreed requirement emerges.
- No Kubernetes, microservices, Redis/Celery, or complex infrastructure by default.
- No changes to the frontend or other teams' modules.
- No unapproved merge or push to `main`.

---

**Implementation instruction to the coding assistant:** Start by inspecting the repository and confirming the `backend` branch. Present a short plan, implement the P0 mock-first FastAPI foundation, run tests, and report exactly what was created, what was tested, and what remains blocked by external teams. Treat this document as design guidance, not evidence of completed work.
